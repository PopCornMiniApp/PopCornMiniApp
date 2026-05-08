"""
Smart Sync Module — Fast incremental sync for PopCorn
═══════════════════════════════════════════════════════

This module provides smart polling that checks only recent messages
instead of scanning the entire group history.

Strategy:
- Runs every 5 minutes
- Scans only messages since last sync
- Much faster than full scan
- Catches new content quickly
"""
import asyncio
import logging
from datetime import datetime, timedelta

from app.config import PRIVATE_GROUP_ID
from app import database as db
from app.database import push_db_to_hf, update_sync_status, get_sync_status
from app.scanner import (
    _parse_topic, _ensure_registered, _process_file_message,
    _get_input_channel, _get_messages_batch, _MsgProxy, _build_file_proxy
)
from app.cache import cache_clear_all

logger = logging.getLogger(__name__)


async def run_smart_sync(pyro_client, lookback_minutes: int = 10, use_user_bot: bool = True) -> dict:
    """
    Smart sync: scan only recent messages (last N minutes).
    
    Args:
        pyro_client: Pyrogram client instance (preferably user bot, not bot)
        lookback_minutes: How many minutes back to scan (default: 10)
        use_user_bot: If True, uses user bot methods (default: True)
    
    Returns:
        dict with sync results
    
    Note:
        This function works best with user bots (s1, s2) as they have full API access.
        Regular bots have limited access to message history.
    """
    results = {
        "messages_scanned": 0,
        "topics_found": 0,
        "registered": 0,
        "files_attached": 0,
        "errors": 0,
        "sync_type": "smart"
    }
    
    changed = False
    
    # Get sync status
    sync_status = get_sync_status()
    last_message_id = sync_status.get("last_message_id", 0)
    
    logger.info(f"[smart_sync] Starting smart sync from message_id={last_message_id}")
    
    # Get channel info
    channel_id, access_hash = await _get_input_channel(pyro_client)
    if not channel_id:
        logger.error("[smart_sync] Cannot resolve private group peer")
        results["errors"] += 1
        return results
    
    # Get current max message ID
    # Strategy: Use raw API to get channel info (works with user bots)
    try:
        from pyrogram.raw.functions.channels.get_full_channel import GetFullChannel
        from pyrogram.raw.types.input_channel import InputChannel
        
        # Get full channel info which includes message count
        full_channel = await pyro_client.invoke(
            GetFullChannel(
                channel=InputChannel(
                    channel_id=channel_id,
                    access_hash=access_hash
                )
            )
        )
        
        # Extract current message count from full_chat
        full_chat = getattr(full_channel, "full_chat", None)
        if full_chat:
            # Try to get the read_inbox_max_id or pts as indicator
            current_max_id = getattr(full_chat, "read_inbox_max_id", 0)
            if current_max_id == 0:
                # Fallback: try pts (message counter)
                current_max_id = getattr(full_chat, "pts", 0)
            
            if current_max_id == 0:
                logger.warning("[smart_sync] Could not determine current max message ID from channel info")
                # Last resort: scan recent messages to find max ID
                try:
                    msgs = await _get_messages_batch(pyro_client, channel_id, access_hash, list(range(1, 101)))
                    real_msgs = [m for m in msgs if type(m).__name__ != "MessageEmpty" and getattr(m, "id", 0) > 0]
                    if real_msgs:
                        current_max_id = max(getattr(m, "id", 0) for m in real_msgs)
                        logger.info(f"[smart_sync] Found max ID from recent scan: {current_max_id}")
                    else:
                        logger.error("[smart_sync] No messages found in recent scan")
                        return results
                except Exception as scan_err:
                    logger.error(f"[smart_sync] Failed to scan for max ID: {scan_err}")
                    return results
        else:
            logger.error("[smart_sync] Could not get full_chat from GetFullChannel")
            results["errors"] += 1
            return results
            
        logger.info(f"[smart_sync] Current max message ID: {current_max_id}")
        
    except Exception as e:
        logger.error(f"[smart_sync] GetFullChannel failed: {e}")
        # Fallback: try to scan recent messages
        try:
            logger.info("[smart_sync] Attempting fallback: scanning recent messages...")
            msgs = await _get_messages_batch(pyro_client, channel_id, access_hash, list(range(1, 101)))
            real_msgs = [m for m in msgs if type(m).__name__ != "MessageEmpty" and getattr(m, "id", 0) > 0]
            if real_msgs:
                current_max_id = max(getattr(m, "id", 0) for m in real_msgs)
                logger.info(f"[smart_sync] Fallback successful - max ID: {current_max_id}")
            else:
                logger.error("[smart_sync] Fallback failed - no messages found")
                results["errors"] += 1
                return results
        except Exception as fallback_err:
            logger.error(f"[smart_sync] Fallback also failed: {fallback_err}")
            results["errors"] += 1
            return results
    
    # If this is first sync, scan last 100 messages only
    if last_message_id == 0:
        last_message_id = max(0, current_max_id - 100)
        logger.info(f"[smart_sync] First sync, starting from {last_message_id}")
    
    # Calculate message range to scan
    start_id = last_message_id + 1
    end_id = current_max_id
    
    if start_id > end_id:
        logger.info("[smart_sync] No new messages since last sync")
        return results
    
    logger.info(f"[smart_sync] Scanning messages {start_id} to {end_id} ({end_id - start_id + 1} messages)")
    
    # Scan messages in batches
    batch_size = 100
    topic_map: dict[int, dict] = {}
    
    for batch_start in range(start_id, end_id + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end_id)
        ids = list(range(batch_start, batch_end + 1))
        
        try:
            msgs = await _get_messages_batch(pyro_client, channel_id, access_hash, ids)
            
            # Filter real messages with content
            real_msgs = [
                m for m in msgs
                if type(m).__name__ != "MessageEmpty"
                and getattr(m, "id", 0) > 0
            ]
            
            results["messages_scanned"] += len(real_msgs)
            
            for raw_msg in real_msgs:
                try:
                    # Get topic info
                    reply_to = getattr(raw_msg, "reply_to", None)
                    topic_id = None
                    if reply_to:
                        topic_id = (
                            getattr(reply_to, "reply_to_top_id", None)
                            or getattr(reply_to, "reply_to_msg_id", None)
                        )
                    
                    if not topic_id:
                        continue
                    
                    caption = getattr(raw_msg, "message", "") or ""
                    msg_id = getattr(raw_msg, "id", 0)
                    media = getattr(raw_msg, "media", None)
                    
                    # Check if this is a topic creation message
                    if hasattr(raw_msg, "action"):
                        action = raw_msg.action
                        action_type = type(action).__name__
                        
                        if "ForumTopicCreated" in action_type or "ForumTopicEdited" in action_type:
                            topic_title = getattr(action, "title", "")
                            if topic_title:
                                parsed = _parse_topic(topic_title)
                                if parsed and topic_id not in topic_map:
                                    topic_map[topic_id] = parsed
                                    results["topics_found"] += 1
                                    try:
                                        added = await _ensure_registered(parsed, topic_id)
                                        if added:
                                            results["registered"] += 1
                                            changed = True
                                            logger.info(f"[smart_sync] Registered: {topic_title}")
                                    except Exception as e:
                                        logger.warning(f"[smart_sync] Register error: {e}")
                                        results["errors"] += 1
                    
                    # Check if this is a file message
                    if media and caption.strip():
                        media_type = type(media).__name__
                        file_obj = None
                        
                        if "Document" in media_type:
                            doc = getattr(media, "document", None)
                            if doc:
                                file_obj = _build_file_proxy(doc)
                        elif "Video" in media_type:
                            vid = getattr(media, "video", None)
                            if vid:
                                file_obj = _build_file_proxy(vid)
                        
                        if file_obj and topic_id:
                            # Try to infer topic type from caption if not in map
                            if topic_id not in topic_map:
                                parsed = _parse_topic(caption)
                                if parsed:
                                    topic_map[topic_id] = parsed
                                    try:
                                        added = await _ensure_registered(parsed, topic_id)
                                        if added:
                                            results["registered"] += 1
                                            changed = True
                                    except Exception as e:
                                        logger.warning(f"[smart_sync] Register from caption: {e}")
                            
                            # Process file
                            proxy = _MsgProxy(
                                id=msg_id,
                                caption=caption,
                                video=file_obj if "Video" in media_type else None,
                                document=file_obj if "Document" in media_type else None
                            )
                            
                            try:
                                saved = await _process_file_message(proxy, topic_id)
                                if saved:
                                    results["files_attached"] += 1
                                    changed = True
                                    logger.info(f"[smart_sync] File attached: msg_id={msg_id}")
                            except Exception as e:
                                logger.warning(f"[smart_sync] Process file error: {e}")
                                results["errors"] += 1
                
                except Exception as e:
                    logger.warning(f"[smart_sync] Message processing error: {e}")
                    results["errors"] += 1
                    continue
        
        except Exception as e:
            logger.error(f"[smart_sync] Batch {batch_start}-{batch_end} failed: {e}")
            results["errors"] += 1
            continue
        
        # Small delay between batches
        await asyncio.sleep(0.1)
    
    # Update sync status
    if end_id > last_message_id:
        update_sync_status(end_id, "smart")
    
    # Push changes if any
    if changed:
        push_db_to_hf()
        cache_clear_all()
        logger.info(f"[smart_sync] Changes pushed to HF and cache cleared")
    
    logger.info(
        f"[smart_sync] Complete: scanned={results['messages_scanned']} "
        f"topics={results['topics_found']} registered={results['registered']} "
        f"files={results['files_attached']} errors={results['errors']}"
    )
    
    return results


async def run_catch_up_sync(pyro_client) -> dict:
    """
    Catch-up sync: run on startup to catch any missed messages.
    Scans messages from last sync to current.
    """
    logger.info("[catch_up] Starting catch-up sync...")
    
    # Run smart sync with longer lookback
    results = await run_smart_sync(pyro_client, lookback_minutes=60)
    results["sync_type"] = "catch_up"
    
    logger.info(f"[catch_up] Complete: {results}")
    return results

# Made with Bob
