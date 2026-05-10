"""
Mirror Management System
========================

This module manages the mirror system for content distribution and protection:
1. Distributes content across multiple mirror groups (3x redundancy)
2. Tracks file locations in all groups
3. Automatic recovery from failed mirrors
4. Verification and repair of mirror integrity
5. Load balancing across groups
"""

import asyncio
import logging
import time
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from pyrogram.client import Client
from pyrogram.errors import FloodWait

from app.multi_source_config import MIRROR_GROUPS
from app.database import get_connection

logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class FileMirror:
    """Represents a file mirror in a group"""
    file_id: str
    content_type: str  # 'movie' or 'episode'
    content_id: str
    group_id: int
    message_id: int
    file_unique_id: str
    file_size: int
    upload_date: float
    is_verified: bool = True
    last_check: float = 0

    def needs_verification(self, interval: int = 3600) -> bool:
        """Check if mirror needs verification (default: every hour)"""
        return time.time() - self.last_check > interval


@dataclass
class MirrorStats:
    """Statistics for mirror operations"""
    total_files: int = 0
    mirrored_files: int = 0
    failed_mirrors: int = 0
    recovered_files: int = 0
    verified_files: int = 0
    repair_operations: int = 0


# ============================================================================
# MIRROR MANAGER
# ============================================================================

class MirrorManager:
    """
    Manages content mirroring across multiple groups
    """

    def __init__(self, target_redundancy: int = 3):
        """
        Initialize mirror manager

        Args:
            target_redundancy: Number of copies for each file (default: 3)
        """
        self.target_redundancy = target_redundancy
        self.file_mirrors: Dict[str, List[FileMirror]] = defaultdict(list)
        self.group_file_count: Dict[int, int] = defaultdict(int)
        self.stats = MirrorStats()
        self._user_client: Optional[Client] = None
        self._initialized = False
        self._mirror_lock = asyncio.Lock()

    async def initialize(self, user_client: Client):
        """
        Initialize the mirror manager

        Args:
            user_client: Pyrogram user client for operations
        """
        if self._initialized:
            logger.info("MirrorManager already initialized")
            return

        self._user_client = user_client

        # Load existing mirrors from database
        await self._load_mirrors_from_db()

        self._initialized = True
        logger.info(
            f"✅ MirrorManager initialized with {len(self.file_mirrors)} files tracked")

    async def _load_mirrors_from_db(self):
        """Load existing mirror information from database"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT file_id, content_type, content_id, group_id, message_id,
                       file_unique_id, file_size, upload_date, is_verified, last_check
                FROM file_mirrors
                ORDER BY upload_date DESC
            """)

            for row in cursor.fetchall():
                mirror = FileMirror(
                    file_id=row[0],
                    content_type=row[1],
                    content_id=row[2],
                    group_id=row[3],
                    message_id=row[4],
                    file_unique_id=row[5],
                    file_size=row[6],
                    upload_date=row[7],
                    is_verified=bool(row[8]),
                    last_check=row[9] or 0
                )

                self.file_mirrors[row[0]].append(mirror)
                self.group_file_count[row[3]] += 1

            self.stats.total_files = len(self.file_mirrors)
            logger.info(
                f"📊 Loaded {self.stats.total_files} files from database")

        except Exception as e:
            logger.error(f"Error loading mirrors from database: {e}")

    async def mirror_content(
        self,
        file_id: str,
        content_type: str,
        content_id: str,
        source_group_id: int,
        source_message_id: int,
        file_size: int,
        file_unique_id: str
    ) -> Dict:
        """
        Mirror content to target groups

        Args:
            file_id: Telegram file ID
            content_type: 'movie' or 'episode'
            content_id: Content identifier
            source_group_id: Source group ID
            source_message_id: Source message ID
            file_size: File size in bytes
            file_unique_id: Unique file identifier

        Returns:
            Dict with mirror results
        """
        if not self._user_client:
            raise ValueError("MirrorManager not initialized")

        async with self._mirror_lock:
            # Check existing mirrors
            existing_mirrors = self.file_mirrors.get(file_id, [])
            existing_groups = {m.group_id for m in existing_mirrors}

            # Calculate how many more mirrors needed
            needed_mirrors = self.target_redundancy - len(existing_mirrors)

            if needed_mirrors <= 0:
                logger.info(
                    f"✅ File {file_id} already has sufficient mirrors ({len(existing_mirrors)})")
                return {
                    "success": True,
                    "existing_mirrors": len(existing_mirrors),
                    "new_mirrors": 0,
                    "groups": list(existing_groups)
                }

            logger.info(
                f"🔄 Mirroring {file_id} to {needed_mirrors} additional groups...")

            # Select target groups (exclude source and existing)
            target_groups = self._select_mirror_groups(
                needed_mirrors,
                exclude_groups=existing_groups | {source_group_id}
            )

            if not target_groups:
                logger.warning(f"No available groups for mirroring {file_id}")
                return {
                    "success": False,
                    "error": "No available mirror groups",
                    "existing_mirrors": len(existing_mirrors)
                }

            # Mirror to selected groups
            new_mirrors = 0
            failed_mirrors = 0

            for group_name, group_config in target_groups:
                try:
                    # Forward message to mirror group
                    forwarded = await self._user_client.forward_messages(
                        chat_id=group_config.group_id,
                        from_chat_id=source_group_id,
                        message_ids=source_message_id
                    )

                    if forwarded:
                        # Handle both single message and list
                        msg = forwarded[0] if isinstance(
                            forwarded, list) else forwarded

                        # Create mirror record
                        mirror = FileMirror(
                            file_id=file_id,
                            content_type=content_type,
                            content_id=content_id,
                            group_id=group_config.group_id,
                            message_id=msg.id,
                            file_unique_id=file_unique_id,
                            file_size=file_size,
                            upload_date=time.time(),
                            is_verified=True,
                            last_check=time.time()
                        )

                        # Save to database
                        await self._save_mirror_to_db(mirror)

                        # Update in-memory tracking
                        self.file_mirrors[file_id].append(mirror)
                        self.group_file_count[group_config.group_id] += 1

                        new_mirrors += 1
                        self.stats.mirrored_files += 1

                        logger.info(
                            f"✅ Mirrored to {group_name} "
                            f"(msg_id={msg.id}, group={group_config.group_id})"
                        )

                except FloodWait as e:
                    logger.warning(f"FloodWait {e.value}s for {group_name}")
                    await asyncio.sleep(e.value)
                    failed_mirrors += 1

                except Exception as e:
                    logger.error(f"Error mirroring to {group_name}: {e}")
                    failed_mirrors += 1

            self.stats.failed_mirrors += failed_mirrors

            return {
                "success": new_mirrors > 0,
                "existing_mirrors": len(existing_mirrors),
                "new_mirrors": new_mirrors,
                "failed_mirrors": failed_mirrors,
                "total_mirrors": len(existing_mirrors) + new_mirrors,
                "groups": list(existing_groups | {g[1].group_id for g in target_groups[:new_mirrors]})
            }

    def _select_mirror_groups(
        self,
        count: int,
        exclude_groups: Set[int]
    ) -> List[Tuple[str, any]]:
        """
        Select mirror groups based on load balancing

        Args:
            count: Number of groups to select
            exclude_groups: Groups to exclude

        Returns:
            List of (group_name, group_config) tuples
        """
        # Get available groups (exclude main and specified groups)
        available = [
            (name, group) for name, group in MIRROR_GROUPS.items()
            if name != "main"
            and group.is_healthy()
            and group.group_id not in exclude_groups
        ]

        if not available:
            return []

        # Sort by file count (prefer less loaded groups)
        available.sort(
            key=lambda x: self.group_file_count.get(
                x[1].group_id, 0))

        return available[:count]

    async def _save_mirror_to_db(self, mirror: FileMirror):
        """Save mirror record to database"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO file_mirrors
                (file_id, content_type, content_id, group_id, message_id,
                 file_unique_id, file_size, upload_date, is_verified, last_check)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mirror.file_id,
                mirror.content_type,
                mirror.content_id,
                mirror.group_id,
                mirror.message_id,
                mirror.file_unique_id,
                mirror.file_size,
                mirror.upload_date,
                1 if mirror.is_verified else 0,
                mirror.last_check
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Error saving mirror to database: {e}")

    async def verify_mirrors(self, file_id: str) -> Dict:
        """
        Verify all mirrors for a file

        Args:
            file_id: File ID to verify

        Returns:
            Verification results
        """
        if not self._user_client:
            raise ValueError("MirrorManager not initialized")

        mirrors = self.file_mirrors.get(file_id, [])

        if not mirrors:
            return {"success": False, "error": "No mirrors found"}

        verified = 0
        failed = 0

        for mirror in mirrors:
            try:
                # Try to get the message
                msg = await self._user_client.get_messages(
                    mirror.group_id,
                    mirror.message_id
                )

                # Handle both single message and list
                message = msg[0] if isinstance(msg, list) else msg

                if message and hasattr(message, 'media') and message.media:
                    mirror.is_verified = True
                    mirror.last_check = time.time()
                    verified += 1
                else:
                    mirror.is_verified = False
                    failed += 1

                # Update database
                await self._update_mirror_verification(mirror)

            except Exception as e:
                logger.error(
                    f"Error verifying mirror in group {mirror.group_id}: {e}")
                mirror.is_verified = False
                failed += 1

        self.stats.verified_files += 1

        return {
            "success": True,
            "total_mirrors": len(mirrors),
            "verified": verified,
            "failed": failed
        }

    async def _update_mirror_verification(self, mirror: FileMirror):
        """Update mirror verification status in database"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE file_mirrors
                SET is_verified = ?, last_check = ?
                WHERE file_id = ? AND group_id = ?
            """, (
                1 if mirror.is_verified else 0,
                mirror.last_check,
                mirror.file_id,
                mirror.group_id
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Error updating mirror verification: {e}")

    async def repair_mirrors(self, file_id: str) -> Dict:
        """
        Repair failed mirrors by creating new ones

        Args:
            file_id: File ID to repair

        Returns:
            Repair results
        """
        mirrors = self.file_mirrors.get(file_id, [])

        if not mirrors:
            return {"success": False, "error": "No mirrors found"}

        # Find a working mirror as source
        working_mirror = None
        for mirror in mirrors:
            if mirror.is_verified:
                working_mirror = mirror
                break

        if not working_mirror:
            logger.error(f"No working mirror found for {file_id}")
            return {"success": False, "error": "No working mirror available"}

        # Count failed mirrors
        failed_count = sum(1 for m in mirrors if not m.is_verified)

        if failed_count == 0:
            return {
                "success": True,
                "repaired": 0,
                "message": "No repairs needed"}

        logger.info(
            f"🔧 Repairing {failed_count} failed mirrors for {file_id}...")

        # Create new mirrors to replace failed ones
        result = await self.mirror_content(
            file_id=file_id,
            content_type=working_mirror.content_type,
            content_id=working_mirror.content_id,
            source_group_id=working_mirror.group_id,
            source_message_id=working_mirror.message_id,
            file_size=working_mirror.file_size,
            file_unique_id=working_mirror.file_unique_id
        )

        self.stats.repair_operations += 1

        return {
            "success": result["success"],
            "repaired": result.get("new_mirrors", 0),
            "failed_count": failed_count
        }

    async def get_best_mirror(self, file_id: str) -> Optional[FileMirror]:
        """
        Get the best available mirror for a file

        Args:
            file_id: File ID

        Returns:
            Best mirror or None
        """
        mirrors = self.file_mirrors.get(file_id, [])

        if not mirrors:
            return None

        # Filter verified mirrors
        verified_mirrors = [m for m in mirrors if m.is_verified]

        if not verified_mirrors:
            # Try to find any mirror
            return mirrors[0] if mirrors else None

        # Sort by group load (prefer less loaded groups)
        verified_mirrors.sort(
            key=lambda m: MIRROR_GROUPS.get(
                next(
                    (name for name, g in MIRROR_GROUPS.items() if g.group_id == m.group_id), ""), type(
                    'obj', (object,), {
                        'current_load': 999})()).current_load)

        return verified_mirrors[0]

    def get_stats(self) -> Dict:
        """Get mirror system statistics"""
        return {
            "total_files": len(self.file_mirrors),
            "total_mirrors": sum(len(mirrors) for mirrors in self.file_mirrors.values()),
            "mirrored_files": self.stats.mirrored_files,
            "failed_mirrors": self.stats.failed_mirrors,
            "recovered_files": self.stats.recovered_files,
            "verified_files": self.stats.verified_files,
            "repair_operations": self.stats.repair_operations,
            "average_redundancy": (
                sum(len(mirrors) for mirrors in self.file_mirrors.values()) / len(self.file_mirrors)
                if self.file_mirrors else 0
            ),
            "group_distribution": dict(self.group_file_count)
        }

    async def run_maintenance(self):
        """Run maintenance tasks (verification and repair)"""
        logger.info("🔧 Running mirror maintenance...")

        verified_count = 0
        repaired_count = 0

        for file_id, mirrors in list(self.file_mirrors.items()):
            # Check if any mirror needs verification
            needs_check = any(m.needs_verification() for m in mirrors)

            if needs_check:
                # Verify mirrors
                verify_result = await self.verify_mirrors(file_id)
                verified_count += 1

                # Repair if needed
                if verify_result.get("failed", 0) > 0:
                    repair_result = await self.repair_mirrors(file_id)
                    if repair_result.get("success"):
                        repaired_count += 1

            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.1)

        logger.info(
            f"✅ Maintenance complete: verified={verified_count}, repaired={repaired_count}"
        )

        return {
            "verified": verified_count,
            "repaired": repaired_count
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global mirror manager instance
mirror_manager = MirrorManager(target_redundancy=3)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def initialize_mirror_system(user_client: Client):
    """Initialize the mirror management system"""
    await mirror_manager.initialize(user_client)
    logger.info("✅ Mirror management system initialized")


async def mirror_file(
    file_id: str,
    content_type: str,
    content_id: str,
    source_group_id: int,
    source_message_id: int,
    file_size: int,
    file_unique_id: str
) -> Dict:
    """Mirror a file to target groups"""
    return await mirror_manager.mirror_content(
        file_id, content_type, content_id,
        source_group_id, source_message_id,
        file_size, file_unique_id
    )


async def verify_file_mirrors(file_id: str) -> Dict:
    """Verify all mirrors for a file"""
    return await mirror_manager.verify_mirrors(file_id)


async def repair_file_mirrors(file_id: str) -> Dict:
    """Repair failed mirrors for a file"""
    return await mirror_manager.repair_mirrors(file_id)


async def get_best_file_mirror(file_id: str) -> Optional[FileMirror]:
    """Get the best available mirror for a file"""
    return await mirror_manager.get_best_mirror(file_id)


def get_mirror_stats() -> Dict:
    """Get mirror system statistics"""
    return mirror_manager.get_stats()


async def run_mirror_maintenance():
    """Run mirror maintenance tasks"""
    return await mirror_manager.run_maintenance()


# Made with Bob
