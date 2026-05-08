"""
Multi-Group Synchronization System
===================================

This module implements intelligent synchronization across multiple mirror groups:
1. Scans main group for new content
2. Distributes content across 8 mirror groups
3. Ignores specific topics (e.g., "General" for archiving)
4. Implements fast incremental sync (every 1 minute)
5. Ensures redundancy (each file in 2-3 groups)
6. Handles conflict resolution
7. Uses user bot for full API access
"""

import asyncio
import logging
import time
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from pyrogram.client import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChannelPrivate, ChatAdminRequired

from app.multi_source_config import (
    MIRROR_GROUPS,
    IGNORED_TOPICS,
    SYNC_INTERVALS,
    MAX_CONCURRENT_SYNCS,
    should_ignore_topic,
)

logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ContentItem:
    """Represents a content item (movie/episode) to sync"""
    message_id: int
    file_id: str
    file_size: int
    file_name: str
    topic_id: int | None = None
    topic_name: str | None = None
    caption: str | None = None
    mime_type: str | None = None
    synced_to_groups: Set[int] = field(default_factory=set)
    last_sync: float = 0
    
    def needs_sync(self, target_redundancy: int = 2) -> bool:
        """Check if item needs to be synced to more groups"""
        return len(self.synced_to_groups) < target_redundancy


@dataclass
class SyncStats:
    """Statistics for sync operations"""
    total_scanned: int = 0
    new_items: int = 0
    synced_items: int = 0
    failed_items: int = 0
    ignored_topics: int = 0
    sync_duration: float = 0
    last_sync_time: float = 0


# ============================================================================
# MULTI-GROUP SYNC MANAGER
# ============================================================================

class MultiGroupSyncManager:
    """
    Manages synchronization across multiple mirror groups
    """
    
    def __init__(self):
        self.content_registry: Dict[str, ContentItem] = {}  # file_id -> ContentItem
        self.group_content: Dict[int, Set[str]] = defaultdict(set)  # group_id -> set of file_ids
        self.sync_stats = SyncStats()
        self.sync_lock = asyncio.Lock()
        self._user_client: Client | None = None
        self._initialized = False
    
    async def initialize(self, user_client: Client):
        """
        Initialize the sync manager with a user bot client
        
        Args:
            user_client: Pyrogram user bot client (s1 or s2) with full API access
        """
        if self._initialized:
            logger.info("MultiGroupSyncManager already initialized")
            return
        
        self._user_client = user_client
        
        if not self._user_client:
            raise ValueError("User client is required for multi-group sync")
        
        # Verify we can access the main group
        main_group = MIRROR_GROUPS.get("main")
        if not main_group:
            raise ValueError("Main group not configured")
        
        try:
            chat = await self._user_client.get_chat(main_group.group_id)
            logger.info(f"✅ Connected to main group: {chat.title}")
        except Exception as e:
            logger.error(f"Failed to access main group: {e}")
            raise
        
        self._initialized = True
        logger.info("✅ MultiGroupSyncManager initialized")
    
    async def scan_main_group(
        self,
        limit: int = 100,
        offset_id: int = 0
    ) -> Tuple[List[ContentItem], int]:
        """
        Scan main group for content items
        
        Args:
            limit: Maximum number of messages to scan
            offset_id: Start scanning from this message ID
        
        Returns:
            Tuple of (list of ContentItems, last_message_id)
        """
        if not self._user_client:
            raise ValueError("User client not initialized")
        
        main_group = MIRROR_GROUPS["main"]
        content_items: List[ContentItem] = []
        last_msg_id = offset_id
        
        try:
            logger.info(f"📡 Scanning main group from message {offset_id}...")
            
            # Get chat to check if it's a forum
            chat = await self._user_client.get_chat(main_group.group_id)
            is_forum = getattr(chat, 'is_forum', False)
            
            if is_forum:
                # Scan forum topics
                content_items, last_msg_id = await self._scan_forum_topics(
                    main_group.group_id, limit, offset_id
                )
            else:
                # Scan regular group
                content_items, last_msg_id = await self._scan_regular_group(
                    main_group.group_id, limit, offset_id
                )
            
            logger.info(
                f"✅ Scan complete: found {len(content_items)} items, "
                f"last_msg_id={last_msg_id}"
            )
            
            return content_items, last_msg_id
        
        except FloodWait as e:
            logger.warning(f"FloodWait during scan: {e.value}s")
            raise
        
        except Exception as e:
            logger.error(f"Error scanning main group: {e}")
            raise
    
    async def _scan_forum_topics(
        self,
        group_id: int,
        limit: int,
        offset_id: int
    ) -> Tuple[List[ContentItem], int]:
        """Scan forum topics for content"""
        content_items: List[ContentItem] = []
        last_msg_id = offset_id
        
        try:
            # Get forum topics
            async for topic in self._user_client.get_forum_topics(group_id):  # type: ignore
                topic_id = topic.id
                topic_name = topic.title
                
                # Check if topic should be ignored
                if should_ignore_topic(topic_name):
                    logger.info(f"⏭️ Ignoring topic: {topic_name}")
                    self.sync_stats.ignored_topics += 1
                    continue
                
                logger.info(f"📂 Scanning topic: {topic_name} (ID: {topic_id})")
                
                # Scan messages in this topic
                async for message in self._user_client.get_chat_history(  # type: ignore
                    group_id,
                    limit=limit,
                    offset_id=offset_id
                ):
                    if not message:
                        continue
                    
                    last_msg_id = max(last_msg_id, message.id)
                    
                    # Check if message has media
                    if not message.media:
                        continue
                    
                    # Extract content item
                    item = await self._extract_content_item(
                        message, topic_id, topic_name
                    )
                    
                    if item:
                        content_items.append(item)
                        self.sync_stats.total_scanned += 1
        
        except Exception as e:
            logger.error(f"Error scanning forum topics: {e}")
        
        return content_items, last_msg_id
    
    async def _scan_regular_group(
        self,
        group_id: int,
        limit: int,
        offset_id: int
    ) -> Tuple[List[ContentItem], int]:
        """Scan regular group for content"""
        content_items: List[ContentItem] = []
        last_msg_id = offset_id
        
        try:
            async for message in self._user_client.get_chat_history(  # type: ignore
                group_id,
                limit=limit,
                offset_id=offset_id
            ):
                if not message:
                    continue
                
                last_msg_id = max(last_msg_id, message.id)
                
                # Check if message has media
                if not message.media:
                    continue
                
                # Extract content item
                item = await self._extract_content_item(message)
                
                if item:
                    content_items.append(item)
                    self.sync_stats.total_scanned += 1
        
        except Exception as e:
            logger.error(f"Error scanning regular group: {e}")
        
        return content_items, last_msg_id
    
    async def _extract_content_item(
        self,
        message: Message,
        topic_id: int | None = None,
        topic_name: str | None = None
    ) -> ContentItem | None:
        """Extract content item from message"""
        try:
            # Get file info based on media type
            file_id = None
            file_size = 0
            file_name = "unknown"
            mime_type = None
            
            if message.video:
                file_id = message.video.file_id
                file_size = message.video.file_size or 0
                file_name = message.video.file_name or f"video_{message.id}.mp4"
                mime_type = message.video.mime_type
            
            elif message.document:
                file_id = message.document.file_id
                file_size = message.document.file_size or 0
                file_name = message.document.file_name or f"document_{message.id}"
                mime_type = message.document.mime_type
            
            elif message.audio:
                file_id = message.audio.file_id
                file_size = message.audio.file_size or 0
                file_name = message.audio.file_name or f"audio_{message.id}.mp3"
                mime_type = message.audio.mime_type
            
            if not file_id:
                return None
            
            # Create content item
            item = ContentItem(
                message_id=message.id,
                file_id=file_id,
                file_size=file_size,
                file_name=file_name,
                topic_id=topic_id,
                topic_name=topic_name,
                caption=message.caption,
                mime_type=mime_type,
            )
            
            return item
        
        except Exception as e:
            logger.error(f"Error extracting content from message {message.id}: {e}")
            return None
    
    async def sync_to_mirrors(
        self,
        content_items: List[ContentItem],
        target_redundancy: int = 2
    ) -> Dict:
        """
        Sync content items to mirror groups
        
        Args:
            content_items: List of content items to sync
            target_redundancy: Number of mirror groups each item should be in
        
        Returns:
            Dict with sync statistics
        """
        if not self._user_client:
            raise ValueError("User client not initialized")
        
        async with self.sync_lock:
            start_time = time.time()
            synced_count = 0
            failed_count = 0
            
            # Get available mirror groups (exclude main)
            available_mirrors = [
                (name, group) for name, group in MIRROR_GROUPS.items()
                if name != "main" and group.is_healthy()
            ]
            
            if not available_mirrors:
                logger.error("No available mirror groups for sync")
                return {"synced": 0, "failed": 0, "duration": 0}
            
            logger.info(
                f"🔄 Starting sync: {len(content_items)} items to "
                f"{len(available_mirrors)} mirrors (redundancy={target_redundancy})"
            )
            
            # Process items in batches to avoid overwhelming the system
            batch_size = 5
            for i in range(0, len(content_items), batch_size):
                batch = content_items[i:i + batch_size]
                
                # Sync batch concurrently
                tasks = [
                    self._sync_item_to_mirrors(
                        item, available_mirrors, target_redundancy
                    )
                    for item in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        failed_count += 1
                        logger.error(f"Sync task failed: {result}")
                    elif result:
                        synced_count += 1
            
            duration = time.time() - start_time
            
            self.sync_stats.synced_items += synced_count
            self.sync_stats.failed_items += failed_count
            self.sync_stats.sync_duration = duration
            self.sync_stats.last_sync_time = time.time()
            
            logger.info(
                f"✅ Sync complete: synced={synced_count}, failed={failed_count}, "
                f"duration={duration:.2f}s"
            )
            
            return {
                "synced": synced_count,
                "failed": failed_count,
                "duration": duration,
                "total_items": len(content_items),
            }
    
    async def _sync_item_to_mirrors(
        self,
        item: ContentItem,
        available_mirrors: List,
        target_redundancy: int
    ) -> bool:
        """Sync a single item to mirror groups"""
        try:
            # Check if item already has enough redundancy
            if len(item.synced_to_groups) >= target_redundancy:
                return True
            
            # Select target mirrors (prefer least loaded)
            target_mirrors = self._select_target_mirrors(
                available_mirrors,
                target_redundancy - len(item.synced_to_groups)
            )
            
            if not target_mirrors:
                logger.warning(f"No target mirrors available for item {item.file_id}")
                return False
            
            # Get the original message from main group
            main_group = MIRROR_GROUPS["main"]
            
            try:
                original_msg = await self._user_client.get_messages(  # type: ignore
                    main_group.group_id,
                    item.message_id
                )
                
                # Handle both single message and list
                msg = original_msg[0] if isinstance(original_msg, list) else original_msg
                
                if not msg or not hasattr(msg, 'media') or not msg.media:
                    logger.warning(f"Could not get original message {item.message_id}")
                    return False
            
            except Exception as e:
                logger.error(f"Error getting original message: {e}")
                return False
            
            # Forward/copy to target mirrors
            success = False
            for mirror_name, mirror_group in target_mirrors:
                try:
                    # Forward message to mirror group
                    forwarded = await self._user_client.forward_messages(  # type: ignore
                        chat_id=mirror_group.group_id,
                        from_chat_id=main_group.group_id,
                        message_ids=item.message_id
                    )
                    
                    if forwarded:
                        item.synced_to_groups.add(mirror_group.group_id)
                        self.group_content[mirror_group.group_id].add(item.file_id)
                        mirror_group.file_count += 1
                        success = True
                        
                        logger.info(
                            f"✅ Synced {item.file_name} to {mirror_name} "
                            f"(group {mirror_group.group_id})"
                        )
                
                except FloodWait as e:
                    logger.warning(f"FloodWait {e.value}s for {mirror_name}")
                    await asyncio.sleep(e.value)
                
                except Exception as e:
                    logger.error(f"Error syncing to {mirror_name}: {e}")
            
            # Update registry
            self.content_registry[item.file_id] = item
            item.last_sync = time.time()
            
            return success
        
        except Exception as e:
            logger.error(f"Error syncing item {item.file_id}: {e}")
            return False
    
    def _select_target_mirrors(
        self,
        available_mirrors: List[Tuple[str, any]],
        count: int
    ) -> List[Tuple[str, any]]:
        """Select target mirror groups based on load"""
        # Sort by current load (prefer less loaded groups)
        sorted_mirrors = sorted(
            available_mirrors,
            key=lambda x: (x[1].current_load, x[1].file_count)
        )
        
        return sorted_mirrors[:count]
    
    def get_stats(self) -> Dict:
        """Get sync statistics"""
        return {
            "total_items": len(self.content_registry),
            "total_scanned": self.sync_stats.total_scanned,
            "new_items": self.sync_stats.new_items,
            "synced_items": self.sync_stats.synced_items,
            "failed_items": self.sync_stats.failed_items,
            "ignored_topics": self.sync_stats.ignored_topics,
            "last_sync": self.sync_stats.last_sync_time,
            "sync_duration": self.sync_stats.sync_duration,
            "groups": {
                name: {
                    "file_count": group.file_count,
                    "current_load": group.current_load,
                    "active": group.active,
                }
                for name, group in MIRROR_GROUPS.items()
            }
        }
    
    async def run_incremental_sync(
        self,
        last_message_id: int = 0,
        limit: int = 100
    ) -> Dict:
        """
        Run incremental sync (scan new messages only)
        
        Args:
            last_message_id: Last synced message ID
            limit: Maximum messages to scan
        
        Returns:
            Sync statistics
        """
        logger.info(f"🔄 Running incremental sync from message {last_message_id}...")
        
        # Scan for new content
        content_items, new_last_id = await self.scan_main_group(
            limit=limit,
            offset_id=last_message_id
        )
        
        if not content_items:
            logger.info("No new content found")
            return {
                "new_items": 0,
                "synced": 0,
                "last_message_id": new_last_id
            }
        
        # Sync to mirrors
        sync_result = await self.sync_to_mirrors(content_items)
        
        return {
            "new_items": len(content_items),
            "synced": sync_result["synced"],
            "failed": sync_result["failed"],
            "duration": sync_result["duration"],
            "last_message_id": new_last_id,
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global sync manager instance
sync_manager = MultiGroupSyncManager()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def initialize_sync_system(user_client: Client):
    """
    Initialize the multi-group sync system
    
    Args:
        user_client: Pyrogram user bot client (s1 or s2)
    """
    await sync_manager.initialize(user_client)
    logger.info("✅ Multi-group sync system initialized")


async def run_full_sync(limit: int = 1000) -> Dict:
    """
    Run full sync (scan all messages)
    
    Args:
        limit: Maximum messages to scan
    
    Returns:
        Sync statistics
    """
    content_items, last_id = await sync_manager.scan_main_group(limit=limit)
    sync_result = await sync_manager.sync_to_mirrors(content_items)
    
    return {
        "total_items": len(content_items),
        "synced": sync_result["synced"],
        "failed": sync_result["failed"],
        "duration": sync_result["duration"],
        "last_message_id": last_id,
    }


async def run_incremental_sync(last_message_id: int = 0) -> Dict:
    """
    Run incremental sync (new messages only)
    
    Args:
        last_message_id: Last synced message ID
    
    Returns:
        Sync statistics
    """
    return await sync_manager.run_incremental_sync(last_message_id)


def get_sync_stats() -> Dict:
    """Get current sync statistics"""
    return sync_manager.get_stats()

# Made with Bob
