"""
Room Synchronization System - Real-time Video Playback Sync
Handles play, pause, seek, and speed changes with latency compensation
"""

import time
import threading
from typing import Dict, List, Any, Optional
from app.database import get_connection

# Thread-safe locks for room synchronization
_room_locks: Dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_room_lock(room_id: str) -> threading.Lock:
    """Get or create a lock for a specific room"""
    with _locks_lock:
        if room_id not in _room_locks:
            _room_locks[room_id] = threading.Lock()
        return _room_locks[room_id]


# ══════════════════════════════════════════════════════════════════════════════
# Sync State Management
# ══════════════════════════════════════════════════════════════════════════════

def get_sync_state(room_id: str) -> Dict[str, Any]:
    """Get current synchronization state of a room"""
    conn = get_connection()
    try:
        room = conn.execute("""
            SELECT status, current_timestamp, playback_speed, sync_mode
            FROM watch_rooms
            WHERE room_id = ?
        """, (room_id,)).fetchone()

        if not room:
            raise ValueError("Room not found")

        status, current_timestamp, playback_speed, sync_mode = room

        # Get last sync event
        last_event = conn.execute("""
            SELECT event_type, timestamp, playback_speed, created_at
            FROM room_sync_events
            WHERE room_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (room_id,)).fetchone()

        sync_state = {
            "room_id": room_id,
            "status": status,
            "current_timestamp": current_timestamp,
            "playback_speed": playback_speed,
            "sync_mode": sync_mode,
            "server_time": time.time()
        }

        if last_event:
            sync_state["last_event"] = {
                "type": last_event[0],
                "timestamp": last_event[1],
                "speed": last_event[2],
                "time": last_event[3]
            }

        return sync_state
    finally:
        conn.close()


def sync_playback(
    room_id: str,
    user_id: int,
    action: str,
    timestamp: float,
    playback_speed: float = 1.0
) -> Dict[str, Any]:
    """
    Synchronize playback action across all participants with thread-safe locking
    Actions: play, pause, seek, speed_change
    """
    # Acquire room-specific lock to prevent race conditions
    room_lock = _get_room_lock(room_id)

    with room_lock:
        conn = get_connection()
        try:
            # Begin transaction for atomic operations
            conn.execute("BEGIN IMMEDIATE")

            # Check if user has permission to control playback
            room = conn.execute("""
                SELECT r.sync_mode, r.host_user_id, p.role
                FROM watch_rooms r
                JOIN room_participants p ON r.room_id = p.room_id
                WHERE r.room_id = ? AND p.user_id = ? AND p.left_at IS NULL
            """, (room_id, user_id)).fetchone()

            if not room:
                conn.rollback()
                raise ValueError("User not in room")

            sync_mode, host_user_id, role = room

            # Check permissions based on sync mode
            can_control = False

            if sync_mode == "host_control":
                # Only host can control
                can_control = (role == "host")
            elif sync_mode == "watch_party":
                # Host and moderators can control
                can_control = (role in ("host", "moderator"))
            elif sync_mode == "voting":
                # Anyone can suggest, but needs votes (simplified for now)
                can_control = True
            elif sync_mode == "free_watch":
                # Everyone controls their own playback (no sync)
                can_control = True

            if not can_control:
                conn.rollback()
                raise ValueError(
                    "Insufficient permissions to control playback")

            # Update room state
            new_status = None
            if action == "play":
                new_status = "playing"
            elif action == "pause":
                new_status = "paused"

            update_query = "UPDATE watch_rooms SET current_timestamp = ?, playback_speed = ?"
            params: List[Any] = [timestamp, playback_speed]

            if new_status:
                update_query += ", status = ?"
                params.append(new_status)

            if action == "play" and new_status == "playing":
                update_query += ", started_at = COALESCE(started_at, datetime('now'))"

            update_query += " WHERE room_id = ?"
            params.append(room_id)

            conn.execute(update_query, params)

            # Log sync event
            conn.execute("""
                INSERT INTO room_sync_events (room_id, user_id, event_type, timestamp, playback_speed)
                VALUES (?, ?, ?, ?, ?)
            """, (room_id, user_id, action, timestamp, playback_speed))

            # Add system message for major events
            if action in ("play", "pause"):
                action_text = "started playback" if action == "play" else "paused playback"
                conn.execute("""
                    INSERT INTO room_chat_messages (room_id, user_id, content, message_type)
                    VALUES (?, ?, ?, 'system')
                """, (room_id, user_id, f"User {user_id} {action_text}"))

            # Commit transaction
            conn.commit()

            return get_sync_state(room_id)

        except Exception:
            # Rollback on any error
            conn.rollback()
            raise
        finally:
            conn.close()


def calculate_adjusted_timestamp(
    base_timestamp: float,
    event_time: str,
    playback_speed: float,
    is_playing: bool
) -> float:
    """
    Calculate current timestamp with latency compensation
    Accounts for time elapsed since last sync event
    """
    if not is_playing:
        return base_timestamp

    # Parse event time (ISO format)
    from datetime import datetime
    event_dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
    event_timestamp = event_dt.timestamp()

    # Calculate elapsed time
    current_time = time.time()
    elapsed = current_time - event_timestamp

    # Adjust for playback speed
    adjusted_timestamp = base_timestamp + (elapsed * playback_speed)

    return adjusted_timestamp


def broadcast_sync_event(room_id: str, event: Dict[str, Any]) -> List[int]:
    """
    Get list of user IDs to broadcast sync event to
    Returns list of active participant user IDs
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT user_id FROM room_participants
            WHERE room_id = ? AND left_at IS NULL AND is_video_synced = 1
        """, (room_id,)).fetchall()

        return [row[0] for row in rows]
    finally:
        conn.close()


def auto_sync_participants(room_id: str) -> Dict[str, Any]:
    """
    Perform automatic synchronization for all participants
    Called periodically (every 5 seconds) to keep everyone in sync
    """
    conn = get_connection()
    try:
        room = conn.execute("""
            SELECT status, current_timestamp, playback_speed, started_at
            FROM watch_rooms
            WHERE room_id = ?
        """, (room_id,)).fetchone()

        if not room:
            raise ValueError("Room not found")

        status, current_timestamp, playback_speed, started_at = room

        # Calculate actual current timestamp if playing
        if status == "playing" and started_at:
            # Get last sync event time
            last_event = conn.execute("""
                SELECT created_at FROM room_sync_events
                WHERE room_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (room_id,)).fetchone()

            if last_event:
                adjusted_timestamp = calculate_adjusted_timestamp(
                    current_timestamp,
                    last_event[0],
                    playback_speed,
                    True
                )

                # Update room timestamp
                conn.execute("""
                    UPDATE watch_rooms SET current_timestamp = ?
                    WHERE room_id = ?
                """, (adjusted_timestamp, room_id))

                conn.commit()

                current_timestamp = adjusted_timestamp

        return {
            "room_id": room_id,
            "status": status,
            "current_timestamp": current_timestamp,
            "playback_speed": playback_speed,
            "sync_time": time.time()
        }
    finally:
        conn.close()


def resync_participant(room_id: str, user_id: int) -> Dict[str, Any]:
    """
    Resynchronize a specific participant (e.g., when they rejoin or fall behind)
    """
    conn = get_connection()
    try:
        # Check if user is in room
        participant = conn.execute("""
            SELECT 1 FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not participant:
            raise ValueError("User not in room")

        # Get current sync state
        sync_state = get_sync_state(room_id)

        # If playing, calculate adjusted timestamp
        if sync_state["status"] == "playing" and "last_event" in sync_state:
            adjusted_timestamp = calculate_adjusted_timestamp(
                sync_state["current_timestamp"],
                sync_state["last_event"]["time"],
                sync_state["playback_speed"],
                True
            )
            sync_state["current_timestamp"] = adjusted_timestamp

        # Log resync event
        conn.execute("""
            INSERT INTO room_sync_events (room_id, user_id, event_type, timestamp, playback_speed)
            VALUES (?, ?, 'sync', ?, ?)
        """, (room_id, user_id, sync_state["current_timestamp"], sync_state["playback_speed"]))

        conn.commit()

        return sync_state
    finally:
        conn.close()


def toggle_participant_sync(room_id: str, user_id: int, enabled: bool) -> bool:
    """
    Enable or disable video sync for a specific participant
    Useful for free_watch mode or when user wants to watch at their own pace
    """
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE room_participants
            SET is_video_synced = ?
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (1 if enabled else 0, room_id, user_id))

        conn.commit()
        return True
    finally:
        conn.close()


def get_sync_history(room_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get synchronization event history for a room"""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM room_sync_events
            WHERE room_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (room_id, limit)).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_participant_sync_status(room_id: str) -> List[Dict[str, Any]]:
    """
    Get sync status for all participants
    Useful for debugging sync issues
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT
                user_id,
                role,
                is_video_synced,
                last_ping,
                julianday('now') - julianday(last_ping) as ping_age_days
            FROM room_participants
            WHERE room_id = ? AND left_at IS NULL
            ORDER BY role, joined_at
        """, (room_id,)).fetchall()

        participants = []
        for row in rows:
            participant = dict(row)
            # Convert ping age from days to seconds
            participant['ping_age_seconds'] = participant['ping_age_days'] * 86400
            # 30 seconds threshold
            participant['is_online'] = participant['ping_age_seconds'] < 30
            del participant['ping_age_days']
            participants.append(participant)

        return participants
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Latency Compensation
# ══════════════════════════════════════════════════════════════════════════════

def estimate_network_latency(
        client_timestamp: float,
        server_timestamp: float) -> float:
    """
    Estimate network latency between client and server
    Returns latency in seconds
    """
    # Simple round-trip time estimation
    latency = abs(server_timestamp - client_timestamp) / 2
    return latency


def compensate_for_latency(
    timestamp: float,
    latency: float,
    playback_speed: float,
    is_playing: bool
) -> float:
    """
    Adjust timestamp to compensate for network latency
    """
    if not is_playing:
        return timestamp

    # Add latency compensation
    compensated_timestamp = timestamp + (latency * playback_speed)

    return compensated_timestamp


def get_sync_quality_metrics(room_id: str) -> Dict[str, Any]:
    """
    Calculate sync quality metrics for monitoring
    """
    conn = get_connection()
    try:
        # Get recent sync events
        recent_events = conn.execute("""
            SELECT
                COUNT(*) as event_count,
                COUNT(DISTINCT user_id) as active_users,
                AVG(CASE WHEN event_type = 'sync' THEN 1 ELSE 0 END) as resync_rate
            FROM room_sync_events
            WHERE room_id = ?
            AND datetime(created_at) > datetime('now', '-5 minutes')
        """, (room_id,)).fetchone()

        # Get participant ping status
        participants = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN julianday('now') - julianday(last_ping) < 0.0003472 THEN 1 ELSE 0 END) as online
            FROM room_participants
            WHERE room_id = ? AND left_at IS NULL
        """, (room_id,)).fetchone()

        metrics = {
            "room_id": room_id,
            "recent_events": recent_events[0] if recent_events else 0,
            "active_users": recent_events[1] if recent_events else 0,
            "resync_rate": recent_events[2] if recent_events else 0,
            "total_participants": participants[0] if participants else 0,
            "online_participants": participants[1] if participants else 0,
            "sync_health": "good" if (
                participants[1] or 0) >= (
                participants[0] or 1) * 0.8 else "degraded"}

        return metrics
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Voting System for Sync Actions
# ══════════════════════════════════════════════════════════════════════════════

def create_sync_vote(
    room_id: str,
    user_id: int,
    action: str,
    timestamp: float
) -> Dict[str, Any]:
    """
    Create a vote for a sync action (for voting mode)
    """
    conn = get_connection()
    try:
        # Check if room is in voting mode
        sync_mode = conn.execute("""
            SELECT sync_mode FROM watch_rooms WHERE room_id = ?
        """, (room_id,)).fetchone()

        if not sync_mode or sync_mode[0] != "voting":
            raise ValueError("Room is not in voting mode")

        # Create poll for the action
        from app.watch_rooms import create_poll

        question = f"Should we {action}?"
        if action == "seek":
            question = f"Should we skip to {timestamp:.0f}s?"

        poll = create_poll(
            room_id=room_id,
            user_id=user_id,
            question=question,
            options=["Yes", "No"]
        )

        return poll
    finally:
        conn.close()


def check_sync_vote_result(poll_id: int) -> Optional[Dict[str, Any]]:
    """
    Check if a sync vote has passed
    Returns sync action if vote passed, None otherwise
    """
    conn = get_connection()
    try:
        import json

        poll = conn.execute("""
            SELECT room_id, question, options, votes, status
            FROM room_polls
            WHERE poll_id = ?
        """, (poll_id,)).fetchone()

        if not poll:
            return None

        room_id, question, options_json, votes_json, status = poll

        if status != "closed":
            return None

        votes = json.loads(votes_json)

        # Count votes
        yes_votes = sum(1 for v in votes.values() if v == 0)  # 0 = Yes
        no_votes = sum(1 for v in votes.values() if v == 1)   # 1 = No

        # Simple majority
        if yes_votes > no_votes:
            # Parse action from question
            action = None
            timestamp = 0.0

            if "pause" in question.lower():
                action = "pause"
            elif "play" in question.lower() or "start" in question.lower():
                action = "play"
            elif "skip" in question.lower():
                action = "seek"
                # Extract timestamp from question
                import re
                match = re.search(r'(\d+)s', question)
                if match:
                    timestamp = float(match.group(1))

            if action:
                return {
                    "action": action,
                    "timestamp": timestamp,
                    "votes": {"yes": yes_votes, "no": no_votes}
                }

        return None
    finally:
        conn.close()

# Made with Bob
