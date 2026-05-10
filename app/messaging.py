"""
Messaging System
Handles direct messages, group chats, media messages, and real-time features
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app import database as db

logger = logging.getLogger(__name__)


class MessagingManager:
    """Comprehensive messaging system"""

    @staticmethod
    def create_conversation(user_ids: List[int],
                            conversation_type: str = 'direct',
                            name: Optional[str] = None,
                            created_by: Optional[int] = None) -> Dict[str,
                                                                      Any]:
        """
        Create a new conversation

        Args:
            user_ids: List of user IDs to include
            conversation_type: 'direct' or 'group'
            name: Name for group conversations
            created_by: User ID who created the conversation

        Returns:
            Result dictionary with conversation_id
        """
        try:
            if len(user_ids) < 2:
                return {"success": False, "error": "At least 2 users required"}

            if conversation_type == 'direct' and len(user_ids) != 2:
                return {
                    "success": False,
                    "error": "Direct conversations must have exactly 2 users"}

            conn = db.get_connection()
            cursor = conn.cursor()

            # For direct conversations, check if one already exists
            if conversation_type == 'direct':
                existing = cursor.execute("""
                    SELECT c.id
                    FROM conversations c
                    JOIN conversation_participants cp1 ON c.id = cp1.conversation_id
                    JOIN conversation_participants cp2 ON c.id = cp2.conversation_id
                    WHERE c.type = 'direct'
                        AND cp1.user_id = ? AND cp1.is_active = 1
                        AND cp2.user_id = ? AND cp2.is_active = 1
                """, (user_ids[0], user_ids[1])).fetchone()

                if existing:
                    conn.close()
                    return {
                        "success": True,
                        "conversation_id": existing['id'],
                        "existing": True
                    }

            # Create conversation
            cursor.execute("""
                INSERT INTO conversations (type, name, created_by)
                VALUES (?, ?, ?)
            """, (conversation_type, name, created_by or user_ids[0]))

            conversation_id = cursor.lastrowid

            # Add participants
            for user_id in user_ids:
                role = 'admin' if user_id == created_by else 'member'
                cursor.execute("""
                    INSERT INTO conversation_participants (conversation_id, user_id, role)
                    VALUES (?, ?, ?)
                """, (conversation_id, user_id, role))

            conn.commit()
            conn.close()

            return {
                "success": True,
                "conversation_id": conversation_id,
                "existing": False
            }

        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_message(conversation_id: int,
                     sender_id: int,
                     content: Optional[str] = None,
                     media_type: str = 'text',
                     media_file_id: Optional[str] = None,
                     media_metadata: Optional[Dict] = None,
                     reply_to_message_id: Optional[int] = None) -> Dict[str,
                                                                        Any]:
        """
        Send a message in a conversation

        Args:
            conversation_id: ID of the conversation
            sender_id: ID of the sender
            content: Text content (required for text messages)
            media_type: Type of media (text, photo, video, audio, document, voice, sticker)
            media_file_id: Telegram file_id for media
            media_metadata: Additional media information (size, duration, dimensions, etc.)
            reply_to_message_id: ID of message being replied to

        Returns:
            Result dictionary with message_id
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Verify user is participant
            participant = cursor.execute("""
                SELECT id FROM conversation_participants
                WHERE conversation_id = ? AND user_id = ? AND is_active = 1
            """, (conversation_id, sender_id)).fetchone()

            if not participant:
                return {
                    "success": False,
                    "error": "Not a participant of this conversation"}

            # Prepare media metadata
            media_file_unique_id = None
            media_file_size = None
            media_thumbnail = None
            media_duration = None
            media_width = None
            media_height = None

            if media_metadata:
                media_file_unique_id = media_metadata.get('file_unique_id')
                media_file_size = media_metadata.get('file_size')
                media_thumbnail = media_metadata.get('thumbnail')
                media_duration = media_metadata.get('duration')
                media_width = media_metadata.get('width')
                media_height = media_metadata.get('height')

            # Insert message
            cursor.execute(
                """
                INSERT INTO messages (
                    conversation_id, sender_id, content, media_type, media_file_id,
                    media_file_unique_id, media_file_size, media_thumbnail, media_duration,
                    media_width, media_height, reply_to_message_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (conversation_id,
                 sender_id,
                 content,
                 media_type,
                 media_file_id,
                 media_file_unique_id,
                 media_file_size,
                 media_thumbnail,
                 media_duration,
                 media_width,
                 media_height,
                 reply_to_message_id))

            message_id = cursor.lastrowid

            # Update conversation last_message
            cursor.execute("""
                UPDATE conversations
                SET last_message_id = ?, last_message_at = datetime('now'), updated_at = datetime('now')
                WHERE id = ?
            """, (message_id, conversation_id))

            conn.commit()
            conn.close()

            # Send notifications to other participants
            try:
                from app.notifications import NotificationManager
                NotificationManager.send_new_message_notification(
                    conversation_id, sender_id, message_id)
            except Exception as e:
                logger.warning(f"Could not send notification: {e}")

            return {
                "success": True,
                "message_id": message_id
            }

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def edit_message(message_id: int, user_id: int,
                     new_content: str) -> Dict[str, Any]:
        """Edit a message (text only)"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Verify ownership
            message = cursor.execute("""
                SELECT sender_id, media_type FROM messages WHERE id = ?
            """, (message_id,)).fetchone()

            if not message:
                return {"success": False, "error": "Message not found"}

            if message['sender_id'] != user_id:
                return {"success": False, "error": "Unauthorized"}

            if message['media_type'] != 'text':
                return {
                    "success": False,
                    "error": "Can only edit text messages"}

            # Update message
            cursor.execute("""
                UPDATE messages
                SET content = ?, is_edited = 1, edited_at = datetime('now')
                WHERE id = ?
            """, (new_content, message_id))

            conn.commit()
            conn.close()

            return {"success": True, "message": "Message edited"}

        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_message(message_id: int, user_id: int) -> Dict[str, Any]:
        """Delete a message (soft delete)"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Verify ownership or admin
            message = cursor.execute("""
                SELECT m.sender_id, m.conversation_id, cp.role
                FROM messages m
                JOIN conversation_participants cp ON
                    cp.conversation_id = m.conversation_id AND cp.user_id = ?
                WHERE m.id = ?
            """, (user_id, message_id)).fetchone()

            if not message:
                return {"success": False, "error": "Message not found"}

            if message['sender_id'] != user_id and message['role'] != 'admin':
                return {"success": False, "error": "Unauthorized"}

            # Soft delete
            cursor.execute("""
                UPDATE messages
                SET is_deleted = 1, deleted_at = datetime('now'), content = NULL
                WHERE id = ?
            """, (message_id,))

            conn.commit()
            conn.close()

            return {"success": True, "message": "Message deleted"}

        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_messages(conversation_id: int, user_id: int, limit: int = 50,
                     before_message_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation with pagination

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the requesting user
            limit: Number of messages to return
            before_message_id: Get messages before this ID (for pagination)

        Returns:
            List of message dictionaries
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Verify user is participant
            participant = cursor.execute("""
                SELECT id FROM conversation_participants
                WHERE conversation_id = ? AND user_id = ? AND is_active = 1
            """, (conversation_id, user_id)).fetchone()

            if not participant:
                return []

            # Build query
            query = """
                SELECT
                    m.id as message_id,
                    m.sender_id,
                    m.content,
                    m.media_type,
                    m.media_file_id,
                    m.media_file_size,
                    m.media_thumbnail,
                    m.media_duration,
                    m.media_width,
                    m.media_height,
                    m.reply_to_message_id,
                    m.is_edited,
                    m.is_deleted,
                    m.created_at,
                    m.edited_at,
                    u.username,
                    u.first_name,
                    u.last_name,
                    up.avatar_url,
                    (SELECT COUNT(*) FROM message_reactions WHERE message_id = m.id) as reaction_count,
                    (SELECT GROUP_CONCAT(reaction || ':' || COUNT(*))
                     FROM message_reactions
                     WHERE message_id = m.id
                     GROUP BY reaction) as reactions
                FROM messages m
                JOIN users u ON u.user_id = m.sender_id
                LEFT JOIN user_profiles up ON u.user_id = up.user_id
                WHERE m.conversation_id = ?
            """

            params = [conversation_id]

            if before_message_id:
                query += " AND m.id < ?"
                params.append(before_message_id)

            query += " ORDER BY m.id DESC LIMIT ?"
            params.append(limit)

            messages = cursor.execute(query, params).fetchall()

            conn.close()

            # Reverse to get chronological order
            return [dict(row) for row in reversed(messages)]

        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []

    @staticmethod
    def mark_as_read(conversation_id: int, user_id: int,
                     message_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Mark messages as read

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user
            message_id: Specific message ID (if None, marks all as read)
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            if message_id:
                # Mark specific message
                cursor.execute("""
                    INSERT OR REPLACE INTO message_read_receipts (message_id, user_id)
                    VALUES (?, ?)
                """, (message_id, user_id))

                # Update participant last_read
                cursor.execute("""
                    UPDATE conversation_participants
                    SET last_read_at = datetime('now'), last_read_message_id = ?
                    WHERE conversation_id = ? AND user_id = ?
                """, (message_id, conversation_id, user_id))
            else:
                # Mark all messages as read
                last_message = cursor.execute("""
                    SELECT id FROM messages
                    WHERE conversation_id = ?
                    ORDER BY id DESC LIMIT 1
                """, (conversation_id,)).fetchone()

                if last_message:
                    cursor.execute("""
                        UPDATE conversation_participants
                        SET last_read_at = datetime('now'), last_read_message_id = ?
                        WHERE conversation_id = ? AND user_id = ?
                    """, (last_message['id'], conversation_id, user_id))

            conn.commit()
            conn.close()

            return {"success": True}

        except Exception as e:
            logger.error(f"Error marking as read: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def add_reaction(message_id: int, user_id: int,
                     reaction: str) -> Dict[str, Any]:
        """Add a reaction to a message"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Verify user can access this message
            message = cursor.execute("""
                SELECT m.conversation_id
                FROM messages m
                JOIN conversation_participants cp ON
                    cp.conversation_id = m.conversation_id AND cp.user_id = ?
                WHERE m.id = ? AND cp.is_active = 1
            """, (user_id, message_id)).fetchone()

            if not message:
                return {"success": False, "error": "Message not found"}

            # Add reaction
            cursor.execute("""
                INSERT OR IGNORE INTO message_reactions (message_id, user_id, reaction)
                VALUES (?, ?, ?)
            """, (message_id, user_id, reaction))

            conn.commit()
            conn.close()

            return {"success": True}

        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def remove_reaction(message_id: int, user_id: int,
                        reaction: str) -> Dict[str, Any]:
        """Remove a reaction from a message"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM message_reactions
                WHERE message_id = ? AND user_id = ? AND reaction = ?
            """, (message_id, user_id, reaction))

            conn.commit()
            conn.close()

            return {"success": True}

        except Exception as e:
            logger.error(f"Error removing reaction: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_conversations(
            user_id: int, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get user's conversations with last message and unread count"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT
                    c.id as conversation_id,
                    c.type,
                    c.name,
                    c.avatar_url,
                    c.is_pinned,
                    c.is_muted,
                    c.is_archived,
                    c.last_message_at,
                    cp.last_read_message_id,
                    lm.id as last_message_id,
                    lm.sender_id as last_sender_id,
                    lm.content as last_message_content,
                    lm.media_type as last_message_type,
                    lu.username as last_sender_username,
                    lu.first_name as last_sender_first_name,
                    (SELECT COUNT(*)
                     FROM messages m2
                     WHERE m2.conversation_id = c.id
                       AND m2.id > COALESCE(cp.last_read_message_id, 0)
                       AND m2.sender_id != ?) as unread_count,
                    CASE
                        WHEN c.type = 'direct' THEN (
                            SELECT u2.user_id
                            FROM conversation_participants cp2
                            JOIN users u2 ON u2.user_id = cp2.user_id
                            WHERE cp2.conversation_id = c.id
                              AND cp2.user_id != ?
                              AND cp2.is_active = 1
                            LIMIT 1
                        )
                        ELSE NULL
                    END as other_user_id,
                    CASE
                        WHEN c.type = 'direct' THEN (
                            SELECT u2.username
                            FROM conversation_participants cp2
                            JOIN users u2 ON u2.user_id = cp2.user_id
                            WHERE cp2.conversation_id = c.id
                              AND cp2.user_id != ?
                              AND cp2.is_active = 1
                            LIMIT 1
                        )
                        ELSE NULL
                    END as other_username,
                    CASE
                        WHEN c.type = 'direct' THEN (
                            SELECT u2.first_name
                            FROM conversation_participants cp2
                            JOIN users u2 ON u2.user_id = cp2.user_id
                            WHERE cp2.conversation_id = c.id
                              AND cp2.user_id != ?
                              AND cp2.is_active = 1
                            LIMIT 1
                        )
                        ELSE NULL
                    END as other_first_name,
                    CASE
                        WHEN c.type = 'direct' THEN (
                            SELECT up2.avatar_url
                            FROM conversation_participants cp2
                            JOIN user_profiles up2 ON up2.user_id = cp2.user_id
                            WHERE cp2.conversation_id = c.id
                              AND cp2.user_id != ?
                              AND cp2.is_active = 1
                            LIMIT 1
                        )
                        ELSE c.avatar_url
                    END as display_avatar,
                    CASE
                        WHEN c.type = 'direct' THEN (
                            SELECT uos.is_online
                            FROM conversation_participants cp2
                            JOIN user_online_status uos ON uos.user_id = cp2.user_id
                            WHERE cp2.conversation_id = c.id
                              AND cp2.user_id != ?
                              AND cp2.is_active = 1
                            LIMIT 1
                        )
                        ELSE NULL
                    END as other_user_online
                FROM conversations c
                JOIN conversation_participants cp ON cp.conversation_id = c.id AND cp.user_id = ?
                LEFT JOIN messages lm ON lm.id = c.last_message_id
                LEFT JOIN users lu ON lu.user_id = lm.sender_id
                WHERE cp.is_active = 1
            """

            params = [
                user_id,
                user_id,
                user_id,
                user_id,
                user_id,
                user_id,
                user_id]

            if not include_archived:
                query += " AND c.is_archived = 0"

            query += " ORDER BY c.is_pinned DESC, c.last_message_at DESC"

            conversations = cursor.execute(query, params).fetchall()

            conn.close()

            return [dict(row) for row in conversations]

        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return []

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Get total unread message count for user"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            count = cursor.execute("""
                SELECT COUNT(DISTINCT m.id)
                FROM messages m
                JOIN conversation_participants cp ON
                    cp.conversation_id = m.conversation_id AND cp.user_id = ?
                WHERE m.id > COALESCE(cp.last_read_message_id, 0)
                  AND m.sender_id != ?
                  AND cp.is_active = 1
            """, (user_id, user_id)).fetchone()[0]

            conn.close()

            return count or 0

        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    @staticmethod
    def set_typing_indicator(
            conversation_id: int, user_id: int, is_typing: bool = True) -> Dict[str, Any]:
        """Set typing indicator for a user in a conversation"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            if is_typing:
                expires_at = (
                    datetime.utcnow() +
                    timedelta(
                        seconds=5)).isoformat()
                cursor.execute("""
                    INSERT OR REPLACE INTO typing_indicators (conversation_id, user_id, expires_at)
                    VALUES (?, ?, ?)
                """, (conversation_id, user_id, expires_at))
            else:
                cursor.execute("""
                    DELETE FROM typing_indicators
                    WHERE conversation_id = ? AND user_id = ?
                """, (conversation_id, user_id))

            conn.commit()
            conn.close()

            return {"success": True}

        except Exception as e:
            logger.error(f"Error setting typing indicator: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_typing_users(conversation_id: int,
                         exclude_user_id: int) -> List[Dict[str, Any]]:
        """Get users currently typing in a conversation"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Clean up expired indicators
            cursor.execute("""
                DELETE FROM typing_indicators
                WHERE expires_at < datetime('now')
            """)

            # Get active typing users
            typing_users = cursor.execute("""
                SELECT
                    u.user_id,
                    u.username,
                    u.first_name
                FROM typing_indicators ti
                JOIN users u ON u.user_id = ti.user_id
                WHERE ti.conversation_id = ?
                  AND ti.user_id != ?
                  AND ti.expires_at > datetime('now')
            """, (conversation_id, exclude_user_id)).fetchall()

            conn.close()

            return [dict(row) for row in typing_users]

        except Exception as e:
            logger.error(f"Error getting typing users: {e}")
            return []

    @staticmethod
    def update_online_status(user_id: int,
                             is_online: bool = True,
                             status_text: Optional[str] = None) -> Dict[str,
                                                                        Any]:
        """Update user's online status"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO user_online_status (user_id, is_online, status_text, updated_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (user_id, 1 if is_online else 0, status_text))

            if not is_online:
                cursor.execute("""
                    UPDATE user_online_status
                    SET last_seen = datetime('now')
                    WHERE user_id = ?
                """, (user_id,))

            conn.commit()
            conn.close()

            return {"success": True}

        except Exception as e:
            logger.error(f"Error updating online status: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def toggle_conversation_setting(conversation_id: int, user_id: int,
                                    setting: str, value: bool) -> Dict[str, Any]:
        """
        Toggle conversation settings (pin, mute, archive)

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user
            setting: 'pin', 'mute', or 'archive'
            value: True or False
        """
        try:
            if setting not in ['pin', 'mute', 'archive']:
                return {"success": False, "error": "Invalid setting"}

            conn = db.get_connection()
            cursor = conn.cursor()

            # Verify user is participant
            participant = cursor.execute("""
                SELECT id FROM conversation_participants
                WHERE conversation_id = ? AND user_id = ? AND is_active = 1
            """, (conversation_id, user_id)).fetchone()

            if not participant:
                return {"success": False, "error": "Not a participant"}

            # Fixed: Validate setting against whitelist to prevent SQL
            # injection
            allowed_settings = {'pin', 'mute', 'archive'}
            if setting not in allowed_settings:
                return {"success": False, "error": "Invalid setting"}

            column = f"is_{setting}ped" if setting == 'pin' else f"is_{setting}d"  # noqa: F841

            cursor.execute("""
                UPDATE conversations
                SET {column} = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (1 if value else 0, conversation_id))

            conn.commit()
            conn.close()

            return {"success": True}

        except Exception as e:
            logger.error(f"Error toggling conversation setting: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def search_messages(conversation_id: int, user_id: int,
                        query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search messages in a conversation"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Verify user is participant
            participant = cursor.execute("""
                SELECT id FROM conversation_participants
                WHERE conversation_id = ? AND user_id = ? AND is_active = 1
            """, (conversation_id, user_id)).fetchone()

            if not participant:
                return []

            search_pattern = f"%{query}%"
            messages = cursor.execute("""
                SELECT
                    m.id as message_id,
                    m.sender_id,
                    m.content,
                    m.media_type,
                    m.created_at,
                    u.username,
                    u.first_name
                FROM messages m
                JOIN users u ON u.user_id = m.sender_id
                WHERE m.conversation_id = ?
                  AND m.is_deleted = 0
                  AND m.content LIKE ?
                ORDER BY m.id DESC
                LIMIT ?
            """, (conversation_id, search_pattern, limit)).fetchall()

            conn.close()

            return [dict(row) for row in messages]

        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return []

# Made with Bob
