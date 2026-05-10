"""
Watch Rooms System - Advanced Group Watching with Real-time Sync
Supports voice chat, text chat, and synchronized video playback
"""

import uuid
import json
import hashlib
from typing import Optional, Dict, List, Any
from app.database import get_connection


# ══════════════════════════════════════════════════════════════════════════════
# Room Management Functions
# ══════════════════════════════════════════════════════════════════════════════

def create_room(
    host_user_id: int,
    content_type: str,
    content_id: str,
    name: str,
    description: str = "",
    episode_id: Optional[int] = None,
    is_public: bool = True,
    password: Optional[str] = None,
    max_participants: int = 50,
    sync_mode: str = "host_control",
    voice_chat_enabled: bool = False
) -> Dict[str, Any]:
    """Create a new watch room"""
    conn = get_connection()
    try:
        room_id = str(uuid.uuid4())

        # Hash password if provided
        hashed_password = None
        if password:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn.execute(
            """
            INSERT INTO watch_rooms (
                room_id, name, description, host_user_id, content_type, content_id,
                episode_id, is_public, password, max_participants, sync_mode, voice_chat_enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (room_id,
             name,
             description,
             host_user_id,
             content_type,
             content_id,
             episode_id,
             1 if is_public else 0,
             hashed_password,
             max_participants,
             sync_mode,
             1 if voice_chat_enabled else 0))

        # Add host as first participant
        conn.execute("""
            INSERT INTO room_participants (room_id, user_id, role)
            VALUES (?, ?, 'host')
        """, (room_id, host_user_id))

        # Log system message
        conn.execute("""
            INSERT INTO room_chat_messages (room_id, user_id, content, message_type)
            VALUES (?, ?, ?, 'system')
        """, (room_id, host_user_id, f"Room created by user {host_user_id}"))

        conn.commit()

        return get_room_details(room_id)
    finally:
        conn.close()


def join_room(room_id: str, user_id: int,
              password: Optional[str] = None) -> Dict[str, Any]:
    """Join an existing room"""
    conn = get_connection()
    try:
        # Get room details
        room = conn.execute("""
            SELECT is_public, password, max_participants, status
            FROM watch_rooms WHERE room_id = ?
        """, (room_id,)).fetchone()

        if not room:
            raise ValueError("Room not found")

        is_public, room_password, max_participants, status = room

        # Check if room has ended
        if status == 'ended':
            raise ValueError("Room has ended")

        # Check password for private rooms
        if not is_public and room_password:
            if not password:
                raise ValueError("Password required")
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if hashed_password != room_password:
                raise ValueError("Invalid password")

        # Check if already a participant
        existing = conn.execute("""
            SELECT 1 FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if existing:
            raise ValueError("Already in room")

        # Check participant limit
        current_count = conn.execute("""
            SELECT COUNT(*) FROM room_participants
            WHERE room_id = ? AND left_at IS NULL
        """, (room_id,)).fetchone()[0]

        if current_count >= max_participants:
            raise ValueError("Room is full")

        # Add participant
        conn.execute("""
            INSERT INTO room_participants (room_id, user_id, role)
            VALUES (?, ?, 'participant')
        """, (room_id, user_id))

        # Log system message
        conn.execute("""
            INSERT INTO room_chat_messages (room_id, user_id, content, message_type)
            VALUES (?, ?, ?, 'system')
        """, (room_id, user_id, f"User {user_id} joined the room"))

        conn.commit()

        return get_room_details(room_id)
    finally:
        conn.close()


def leave_room(room_id: str, user_id: int) -> bool:
    """Leave a room"""
    conn = get_connection()
    try:
        # Update participant record
        conn.execute("""
            UPDATE room_participants
            SET left_at = datetime('now')
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id))

        # Log system message
        conn.execute("""
            INSERT INTO room_chat_messages (room_id, user_id, content, message_type)
            VALUES (?, ?, ?, 'system')
        """, (room_id, user_id, f"User {user_id} left the room"))

        # Check if host left - transfer host or end room
        room = conn.execute("""
            SELECT host_user_id FROM watch_rooms WHERE room_id = ?
        """, (room_id,)).fetchone()

        if room and room[0] == user_id:
            # Find next moderator or participant to promote
            next_host = conn.execute("""
                SELECT user_id FROM room_participants
                WHERE room_id = ? AND left_at IS NULL AND user_id != ?
                ORDER BY CASE role WHEN 'moderator' THEN 1 ELSE 2 END, joined_at
                LIMIT 1
            """, (room_id, user_id)).fetchone()

            if next_host:
                # Transfer host
                conn.execute("""
                    UPDATE watch_rooms SET host_user_id = ? WHERE room_id = ?
                """, (next_host[0], room_id))
                conn.execute("""
                    UPDATE room_participants SET role = 'host'
                    WHERE room_id = ? AND user_id = ?
                """, (room_id, next_host[0]))
                conn.execute("""
                    INSERT INTO room_chat_messages (room_id, user_id, content, message_type)
                    VALUES (?, ?, ?, 'system')
                """, (room_id, next_host[0], f"User {next_host[0]} is now the host"))
            else:
                # No one left, end room
                conn.execute("""
                    UPDATE watch_rooms SET status = 'ended', ended_at = datetime('now')
                    WHERE room_id = ?
                """, (room_id,))

        conn.commit()
        return True
    finally:
        conn.close()


def kick_participant(room_id: str, user_id: int, target_id: int) -> bool:
    """Kick a participant from the room (host/moderator only)"""
    conn = get_connection()
    try:
        # Check if user has permission
        role = conn.execute("""
            SELECT role FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not role or role[0] not in ('host', 'moderator'):
            raise ValueError("Insufficient permissions")

        # Can't kick host
        target_role = conn.execute("""
            SELECT role FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, target_id)).fetchone()

        if not target_role:
            raise ValueError("Target not in room")

        if target_role[0] == 'host':
            raise ValueError("Cannot kick host")

        # Kick participant
        conn.execute("""
            UPDATE room_participants
            SET left_at = datetime('now')
            WHERE room_id = ? AND user_id = ?
        """, (room_id, target_id))

        # Log system message
        conn.execute("""
            INSERT INTO room_chat_messages (room_id, user_id, content, message_type)
            VALUES (?, ?, ?, 'system')
        """, (room_id, user_id, f"User {target_id} was kicked from the room"))

        conn.commit()
        return True
    finally:
        conn.close()


def promote_to_moderator(room_id: str, user_id: int, target_id: int) -> bool:
    """Promote a participant to moderator (host only)"""
    conn = get_connection()
    try:
        # Check if user is host
        role = conn.execute("""
            SELECT role FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not role or role[0] != 'host':
            raise ValueError("Only host can promote moderators")

        # Promote target
        conn.execute("""
            UPDATE room_participants SET role = 'moderator'
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, target_id))

        # Log system message
        conn.execute("""
            INSERT INTO room_chat_messages (room_id, user_id, content, message_type)
            VALUES (?, ?, ?, 'system')
        """, (room_id, user_id, f"User {target_id} was promoted to moderator"))

        conn.commit()
        return True
    finally:
        conn.close()


def update_room_settings(
    room_id: str,
    user_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
    password: Optional[str] = None,
    max_participants: Optional[int] = None,
    sync_mode: Optional[str] = None,
    voice_chat_enabled: Optional[bool] = None
) -> Dict[str, Any]:
    """Update room settings (host only)"""
    conn = get_connection()
    try:
        # Check if user is host
        role = conn.execute("""
            SELECT role FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not role or role[0] != 'host':
            raise ValueError("Only host can update settings")

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if is_public is not None:
            updates.append("is_public = ?")
            params.append(1 if is_public else 0)

        if password is not None:
            hashed_password = hashlib.sha256(
                password.encode()).hexdigest() if password else None
            updates.append("password = ?")
            params.append(hashed_password)

        if max_participants is not None:
            updates.append("max_participants = ?")
            params.append(max_participants)

        if sync_mode is not None:
            updates.append("sync_mode = ?")
            params.append(sync_mode)

        if voice_chat_enabled is not None:
            updates.append("voice_chat_enabled = ?")
            params.append(1 if voice_chat_enabled else 0)

        if updates:
            params.append(room_id)
            conn.execute("""
                UPDATE watch_rooms SET {', '.join(updates)}
                WHERE room_id = ?
            """, params)
            conn.commit()

        return get_room_details(room_id)
    finally:
        conn.close()


def delete_room(room_id: str, user_id: int) -> bool:
    """Delete a room (host only)"""
    conn = get_connection()
    try:
        # Check if user is host
        role = conn.execute("""
            SELECT role FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not role or role[0] != 'host':
            raise ValueError("Only host can delete room")

        # End room
        conn.execute("""
            UPDATE watch_rooms SET status = 'ended', ended_at = datetime('now')
            WHERE room_id = ?
        """, (room_id,))

        # Mark all participants as left
        conn.execute("""
            UPDATE room_participants SET left_at = datetime('now')
            WHERE room_id = ? AND left_at IS NULL
        """, (room_id,))

        conn.commit()
        return True
    finally:
        conn.close()


def get_active_rooms(
    limit: int = 50,
    offset: int = 0,
    content_type: Optional[str] = None,
    is_public: bool = True
) -> List[Dict[str, Any]]:
    """Get list of active rooms"""
    conn = get_connection()
    try:
        query = """
            SELECT
                r.*,
                COUNT(DISTINCT p.user_id) as participant_count
            FROM watch_rooms r
            LEFT JOIN room_participants p ON r.room_id = p.room_id AND p.left_at IS NULL
            WHERE r.status != 'ended'
        """
        params = []

        if is_public:
            query += " AND r.is_public = 1"

        if content_type:
            query += " AND r.content_type = ?"
            params.append(content_type)

        query += """
            GROUP BY r.room_id
            ORDER BY r.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()

        rooms = []
        for row in rows:
            room = dict(row)
            room['is_public'] = bool(room['is_public'])
            room['voice_chat_enabled'] = bool(room['voice_chat_enabled'])
            room['has_password'] = bool(room['password'])
            del room['password']  # Don't expose password hash
            rooms.append(room)

        return rooms
    finally:
        conn.close()


def get_room_details(room_id: str) -> Dict[str, Any]:
    """Get detailed room information"""
    conn = get_connection()
    try:
        room = conn.execute("""
            SELECT * FROM watch_rooms WHERE room_id = ?
        """, (room_id,)).fetchone()

        if not room:
            raise ValueError("Room not found")

        room_dict = dict(room)
        room_dict['is_public'] = bool(room_dict['is_public'])
        room_dict['voice_chat_enabled'] = bool(room_dict['voice_chat_enabled'])
        room_dict['has_password'] = bool(room_dict['password'])
        del room_dict['password']  # Don't expose password hash

        # Get participants
        participants = conn.execute("""
            SELECT user_id, role, joined_at, is_muted, is_video_synced, last_ping
            FROM room_participants
            WHERE room_id = ? AND left_at IS NULL
            ORDER BY CASE role WHEN 'host' THEN 1 WHEN 'moderator' THEN 2 ELSE 3 END, joined_at
        """, (room_id,)).fetchall()

        room_dict['participants'] = [dict(p) for p in participants]
        room_dict['participant_count'] = len(room_dict['participants'])

        return room_dict
    finally:
        conn.close()


def search_rooms(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search for rooms by name or description"""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT
                r.*,
                COUNT(DISTINCT p.user_id) as participant_count
            FROM watch_rooms r
            LEFT JOIN room_participants p ON r.room_id = p.room_id AND p.left_at IS NULL
            WHERE r.status != 'ended'
            AND r.is_public = 1
            AND (r.name LIKE ? OR r.description LIKE ?)
            GROUP BY r.room_id
            ORDER BY participant_count DESC, r.created_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit)).fetchall()

        rooms = []
        for row in rows:
            room = dict(row)
            room['is_public'] = bool(room['is_public'])
            room['voice_chat_enabled'] = bool(room['voice_chat_enabled'])
            room['has_password'] = bool(room['password'])
            del room['password']
            rooms.append(room)

        return rooms
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Chat Functions
# ══════════════════════════════════════════════════════════════════════════════

def send_room_message(
    room_id: str,
    user_id: int,
    content: str,
    message_type: str = "text",
    reply_to: Optional[int] = None
) -> Dict[str, Any]:
    """Send a message in the room chat"""
    conn = get_connection()
    try:
        # Check if user is in room
        participant = conn.execute("""
            SELECT 1 FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not participant:
            raise ValueError("Not in room")

        cursor = conn.execute("""
            INSERT INTO room_chat_messages (room_id, user_id, content, message_type, reply_to)
            VALUES (?, ?, ?, ?, ?)
        """, (room_id, user_id, content, message_type, reply_to))

        message_id = cursor.lastrowid
        conn.commit()

        # Get the message
        message = conn.execute("""
            SELECT * FROM room_chat_messages WHERE message_id = ?
        """, (message_id,)).fetchone()

        return dict(message)
    finally:
        conn.close()


def get_room_messages(
    room_id: str,
    limit: int = 50,
    offset: int = 0,
    before_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Get chat messages from a room"""
    conn = get_connection()
    try:
        query = """
            SELECT * FROM room_chat_messages
            WHERE room_id = ? AND deleted_at IS NULL
        """
        params = [room_id]

        if before_id:
            query += " AND message_id < ?"
            params.append(before_id)

        query += " ORDER BY message_id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        messages = [dict(row) for row in rows]
        messages.reverse()  # Return in chronological order

        return messages
    finally:
        conn.close()


def delete_room_message(message_id: int, user_id: int) -> bool:
    """Delete a chat message (author, moderator, or host only)"""
    conn = get_connection()
    try:
        # Get message and check permissions
        message = conn.execute("""
            SELECT m.room_id, m.user_id, p.role
            FROM room_chat_messages m
            JOIN room_participants p ON m.room_id = p.room_id AND p.user_id = ?
            WHERE m.message_id = ? AND p.left_at IS NULL
        """, (user_id, message_id)).fetchone()

        if not message:
            raise ValueError("Message not found or insufficient permissions")

        room_id, msg_user_id, role = message

        # Check if user can delete (author, moderator, or host)
        if msg_user_id != user_id and role not in ('host', 'moderator'):
            raise ValueError("Insufficient permissions")

        conn.execute("""
            UPDATE room_chat_messages SET deleted_at = datetime('now')
            WHERE message_id = ?
        """, (message_id,))

        conn.commit()
        return True
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Participant Management
# ══════════════════════════════════════════════════════════════════════════════

def update_participant_ping(room_id: str, user_id: int) -> bool:
    """Update participant's last ping time"""
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE room_participants
            SET last_ping = datetime('now')
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id))
        conn.commit()
        return True
    finally:
        conn.close()


def mute_participant(room_id: str, user_id: int, target_id: int) -> bool:
    """Mute a participant (host/moderator only)"""
    conn = get_connection()
    try:
        # Check permissions
        role = conn.execute("""
            SELECT role FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not role or role[0] not in ('host', 'moderator'):
            raise ValueError("Insufficient permissions")

        conn.execute("""
            UPDATE room_participants SET is_muted = 1
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, target_id))

        conn.commit()
        return True
    finally:
        conn.close()


def unmute_participant(room_id: str, user_id: int, target_id: int) -> bool:
    """Unmute a participant (host/moderator only)"""
    conn = get_connection()
    try:
        # Check permissions
        role = conn.execute("""
            SELECT role FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not role or role[0] not in ('host', 'moderator'):
            raise ValueError("Insufficient permissions")

        conn.execute("""
            UPDATE room_participants SET is_muted = 0
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, target_id))

        conn.commit()
        return True
    finally:
        conn.close()


def get_room_participants(room_id: str) -> List[Dict[str, Any]]:
    """Get all active participants in a room"""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT user_id, role, joined_at, is_muted, is_video_synced, last_ping
            FROM room_participants
            WHERE room_id = ? AND left_at IS NULL
            ORDER BY CASE role WHEN 'host' THEN 1 WHEN 'moderator' THEN 2 ELSE 3 END, joined_at
        """, (room_id,)).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Reactions & Timestamps
# ══════════════════════════════════════════════════════════════════════════════

def add_reaction(
        room_id: str,
        user_id: int,
        reaction_type: str,
        timestamp: float) -> int:
    """Add a reaction at a specific timestamp"""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO room_reactions (room_id, user_id, reaction_type, timestamp)
            VALUES (?, ?, ?, ?)
        """, (room_id, user_id, reaction_type, timestamp))

        reaction_id = cursor.lastrowid
        conn.commit()
        return reaction_id
    finally:
        conn.close()


def get_recent_reactions(
        room_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent reactions in a room"""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM room_reactions
            WHERE room_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (room_id, limit)).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def add_timestamp_marker(
    room_id: str,
    user_id: int,
    timestamp: float,
    label: str,
    description: str = ""
) -> int:
    """Add a timestamp marker for important moments"""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO room_timestamps (room_id, user_id, timestamp, label, description)
            VALUES (?, ?, ?, ?, ?)
        """, (room_id, user_id, timestamp, label, description))

        marker_id = cursor.lastrowid
        conn.commit()
        return marker_id
    finally:
        conn.close()


def get_timestamp_markers(room_id: str) -> List[Dict[str, Any]]:
    """Get all timestamp markers for a room"""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM room_timestamps
            WHERE room_id = ?
            ORDER BY timestamp
        """, (room_id,)).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Polls
# ══════════════════════════════════════════════════════════════════════════════

def create_poll(
    room_id: str,
    user_id: int,
    question: str,
    options: List[str]
) -> Dict[str, Any]:
    """Create a poll in the room"""
    conn = get_connection()
    try:
        # Check if user is in room
        participant = conn.execute("""
            SELECT role FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not participant:
            raise ValueError("Not in room")

        options_json = json.dumps(options)
        votes_json = json.dumps({})

        cursor = conn.execute("""
            INSERT INTO room_polls (room_id, user_id, question, options, votes)
            VALUES (?, ?, ?, ?, ?)
        """, (room_id, user_id, question, options_json, votes_json))

        poll_id = cursor.lastrowid
        conn.commit()

        poll = conn.execute("""
            SELECT * FROM room_polls WHERE poll_id = ?
        """, (poll_id,)).fetchone()

        poll_dict = dict(poll)
        poll_dict['options'] = json.loads(poll_dict['options'])
        poll_dict['votes'] = json.loads(poll_dict['votes'])

        return poll_dict
    finally:
        conn.close()


def vote_poll(poll_id: int, user_id: int, option_index: int) -> Dict[str, Any]:
    """Vote on a poll"""
    conn = get_connection()
    try:
        poll = conn.execute("""
            SELECT room_id, options, votes, status FROM room_polls WHERE poll_id = ?
        """, (poll_id,)).fetchone()

        if not poll:
            raise ValueError("Poll not found")

        room_id, options_json, votes_json, status = poll

        if status != 'active':
            raise ValueError("Poll is closed")

        # Check if user is in room
        participant = conn.execute("""
            SELECT 1 FROM room_participants
            WHERE room_id = ? AND user_id = ? AND left_at IS NULL
        """, (room_id, user_id)).fetchone()

        if not participant:
            raise ValueError("Not in room")

        options = json.loads(options_json)
        votes = json.loads(votes_json)

        if option_index < 0 or option_index >= len(options):
            raise ValueError("Invalid option")

        # Record vote
        votes[str(user_id)] = option_index

        conn.execute("""
            UPDATE room_polls SET votes = ? WHERE poll_id = ?
        """, (json.dumps(votes), poll_id))

        conn.commit()

        # Return updated poll
        poll = conn.execute("""
            SELECT * FROM room_polls WHERE poll_id = ?
        """, (poll_id,)).fetchone()

        poll_dict = dict(poll)
        poll_dict['options'] = json.loads(poll_dict['options'])
        poll_dict['votes'] = json.loads(poll_dict['votes'])

        return poll_dict
    finally:
        conn.close()


def close_poll(poll_id: int, user_id: int) -> Dict[str, Any]:
    """Close a poll (creator, moderator, or host only)"""
    conn = get_connection()
    try:
        poll = conn.execute("""
            SELECT p.room_id, p.user_id, rp.role
            FROM room_polls p
            JOIN room_participants rp ON p.room_id = rp.room_id AND rp.user_id = ?
            WHERE p.poll_id = ? AND rp.left_at IS NULL
        """, (user_id, poll_id)).fetchone()

        if not poll:
            raise ValueError("Poll not found or insufficient permissions")

        room_id, poll_user_id, role = poll

        if poll_user_id != user_id and role not in ('host', 'moderator'):
            raise ValueError("Insufficient permissions")

        conn.execute("""
            UPDATE room_polls SET status = 'closed', closed_at = datetime('now')
            WHERE poll_id = ?
        """, (poll_id,))

        conn.commit()

        # Return updated poll
        poll = conn.execute("""
            SELECT * FROM room_polls WHERE poll_id = ?
        """, (poll_id,)).fetchone()

        poll_dict = dict(poll)
        poll_dict['options'] = json.loads(poll_dict['options'])
        poll_dict['votes'] = json.loads(poll_dict['votes'])

        return poll_dict
    finally:
        conn.close()


def get_room_polls(
        room_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
    """Get polls in a room"""
    conn = get_connection()
    try:
        query = "SELECT * FROM room_polls WHERE room_id = ?"
        params = [room_id]

        if active_only:
            query += " AND status = 'active'"

        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, params).fetchall()

        polls = []
        for row in rows:
            poll = dict(row)
            poll['options'] = json.loads(poll['options'])
            poll['votes'] = json.loads(poll['votes'])
            polls.append(poll)

        return polls
    finally:
        conn.close()

# Made with Bob
