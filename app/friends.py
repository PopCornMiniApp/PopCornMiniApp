"""
Friends Management System
Handles friend requests, friendships, blocking, and user search
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app import database as db

logger = logging.getLogger(__name__)


class FriendsManager:
    """Comprehensive friends management system"""

    @staticmethod
    def search_users(query: str, current_user_id: int,
                     limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for users by username, first name, or last name

        Args:
            query: Search query
            current_user_id: ID of the user performing the search
            limit: Maximum number of results

        Returns:
            List of user dictionaries with friendship status
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Search users (exclude current user and bots)
            search_pattern = f"%{query}%"
            users = cursor.execute(
                """
                SELECT
                    u.user_id,
                    u.username,
                    u.first_name,
                    u.last_name,
                    u.is_premium,
                    u.last_active,
                    up.avatar_url,
                    up.bio,
                    CASE
                        WHEN f.id IS NOT NULL THEN 'friends'
                        WHEN fr_sent.id IS NOT NULL THEN 'request_sent'
                        WHEN fr_received.id IS NOT NULL THEN 'request_received'
                        WHEN b.id IS NOT NULL THEN 'blocked'
                        ELSE 'none'
                    END as friendship_status
                FROM users u
                LEFT JOIN user_profiles up ON u.user_id = up.user_id
                LEFT JOIN friendships f ON (
                    (f.user_id = ? AND f.friend_id = u.user_id) OR
                    (f.friend_id = ? AND f.user_id = u.user_id)
                ) AND f.status = 'accepted'
                LEFT JOIN friend_requests fr_sent ON
                    fr_sent.from_user_id = ? AND
                    fr_sent.to_user_id = u.user_id AND
                    fr_sent.status = 'pending'
                LEFT JOIN friend_requests fr_received ON
                    fr_received.from_user_id = u.user_id AND
                    fr_received.to_user_id = ? AND
                    fr_received.status = 'pending'
                LEFT JOIN blocked_users b ON
                    b.user_id = ? AND b.blocked_user_id = u.user_id
                WHERE u.user_id != ?
                    AND u.is_bot = 0
                    AND u.is_blocked = 0
                    AND (
                        u.username LIKE ? OR
                        u.first_name LIKE ? OR
                        u.last_name LIKE ?
                    )
                ORDER BY
                    CASE friendship_status
                        WHEN 'friends' THEN 1
                        WHEN 'request_received' THEN 2
                        WHEN 'request_sent' THEN 3
                        ELSE 4
                    END,
                    u.last_active DESC
                LIMIT ?
            """,
                (current_user_id,
                 current_user_id,
                 current_user_id,
                 current_user_id,
                 current_user_id,
                 current_user_id,
                 search_pattern,
                 search_pattern,
                 search_pattern,
                 limit)).fetchall()

            conn.close()

            return [dict(row) for row in users]

        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []

    @staticmethod
    def send_friend_request(from_user_id: int,
                            to_user_id: int,
                            message: Optional[str] = None) -> Dict[str,
                                                                   Any]:
        """
        Send a friend request

        Args:
            from_user_id: ID of user sending request
            to_user_id: ID of user receiving request
            message: Optional message with request

        Returns:
            Result dictionary with success status
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Check if users exist
            from_user = cursor.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (from_user_id,)).fetchone()
            to_user = cursor.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (to_user_id,)).fetchone()

            if not from_user or not to_user:
                return {"success": False, "error": "User not found"}

            # Check if already friends
            existing_friendship = cursor.execute("""
                SELECT id FROM friendships
                WHERE ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
                AND status = 'accepted'
            """, (from_user_id, to_user_id, to_user_id, from_user_id)).fetchone()

            if existing_friendship:
                return {"success": False, "error": "Already friends"}

            # Check if blocked
            is_blocked = cursor.execute("""
                SELECT id FROM blocked_users
                WHERE (user_id = ? AND blocked_user_id = ?) OR (user_id = ? AND blocked_user_id = ?)
            """, (from_user_id, to_user_id, to_user_id, from_user_id)).fetchone()

            if is_blocked:
                return {
                    "success": False,
                    "error": "Cannot send friend request"}

            # Check for existing pending request
            existing_request = cursor.execute("""
                SELECT id, from_user_id FROM friend_requests
                WHERE ((from_user_id = ? AND to_user_id = ?) OR (from_user_id = ? AND to_user_id = ?))
                AND status = 'pending'
            """, (from_user_id, to_user_id, to_user_id, from_user_id)).fetchone()

            if existing_request:
                # If the other user already sent a request, auto-accept it
                if existing_request['from_user_id'] == to_user_id:
                    return FriendsManager.accept_friend_request(
                        existing_request['id'], from_user_id)
                else:
                    return {
                        "success": False,
                        "error": "Friend request already sent"}

            # Create friend request
            expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
            cursor.execute("""
                INSERT INTO friend_requests (from_user_id, to_user_id, message, expires_at)
                VALUES (?, ?, ?, ?)
            """, (from_user_id, to_user_id, message, expires_at))

            request_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Send notification (will be implemented in notifications.py)
            try:
                from app.notifications import NotificationManager
                NotificationManager.send_friend_request_notification(
                    from_user_id, to_user_id, request_id)
            except Exception as e:
                logger.warning(f"Could not send notification: {e}")

            return {
                "success": True,
                "request_id": request_id,
                "message": "Friend request sent successfully"
            }

        except Exception as e:
            logger.error(f"Error sending friend request: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def accept_friend_request(request_id: int, user_id: int) -> Dict[str, Any]:
        """
        Accept a friend request

        Args:
            request_id: ID of the friend request
            user_id: ID of user accepting (must be the recipient)

        Returns:
            Result dictionary with success status
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Get request details
            request = cursor.execute("""
                SELECT from_user_id, to_user_id, status
                FROM friend_requests
                WHERE id = ?
            """, (request_id,)).fetchone()

            if not request:
                return {"success": False, "error": "Friend request not found"}

            if request['to_user_id'] != user_id:
                return {"success": False, "error": "Unauthorized"}

            if request['status'] != 'pending':
                return {"success": False, "error": "Request already processed"}

            # Update request status
            cursor.execute("""
                UPDATE friend_requests
                SET status = 'accepted', updated_at = datetime('now')
                WHERE id = ?
            """, (request_id,))

            # Create friendship (bidirectional)
            cursor.execute("""
                INSERT OR IGNORE INTO friendships (user_id, friend_id, status)
                VALUES (?, ?, 'accepted')
            """, (request['from_user_id'], request['to_user_id']))

            cursor.execute("""
                INSERT OR IGNORE INTO friendships (user_id, friend_id, status)
                VALUES (?, ?, 'accepted')
            """, (request['to_user_id'], request['from_user_id']))

            conn.commit()
            conn.close()

            # Send notification
            try:
                from app.notifications import NotificationManager
                NotificationManager.send_friend_request_accepted_notification(
                    request['to_user_id'], request['from_user_id']
                )
            except Exception as e:
                logger.warning(f"Could not send notification: {e}")

            return {
                "success": True,
                "message": "Friend request accepted"
            }

        except Exception as e:
            logger.error(f"Error accepting friend request: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def reject_friend_request(request_id: int, user_id: int) -> Dict[str, Any]:
        """Reject a friend request"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            request = cursor.execute("""
                SELECT to_user_id, status FROM friend_requests WHERE id = ?
            """, (request_id,)).fetchone()

            if not request:
                return {"success": False, "error": "Friend request not found"}

            if request['to_user_id'] != user_id:
                return {"success": False, "error": "Unauthorized"}

            if request['status'] != 'pending':
                return {"success": False, "error": "Request already processed"}

            cursor.execute("""
                UPDATE friend_requests
                SET status = 'rejected', updated_at = datetime('now')
                WHERE id = ?
            """, (request_id,))

            conn.commit()
            conn.close()

            return {"success": True, "message": "Friend request rejected"}

        except Exception as e:
            logger.error(f"Error rejecting friend request: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def cancel_friend_request(request_id: int, user_id: int) -> Dict[str, Any]:
        """Cancel a sent friend request"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            request = cursor.execute("""
                SELECT from_user_id, status FROM friend_requests WHERE id = ?
            """, (request_id,)).fetchone()

            if not request:
                return {"success": False, "error": "Friend request not found"}

            if request['from_user_id'] != user_id:
                return {"success": False, "error": "Unauthorized"}

            if request['status'] != 'pending':
                return {"success": False, "error": "Request already processed"}

            cursor.execute("""
                UPDATE friend_requests
                SET status = 'cancelled', updated_at = datetime('now')
                WHERE id = ?
            """, (request_id,))

            conn.commit()
            conn.close()

            return {"success": True, "message": "Friend request cancelled"}

        except Exception as e:
            logger.error(f"Error cancelling friend request: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def remove_friend(user_id: int, friend_id: int) -> Dict[str, Any]:
        """Remove a friend"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Delete both directions of friendship
            cursor.execute("""
                DELETE FROM friendships
                WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
            """, (user_id, friend_id, friend_id, user_id))

            if cursor.rowcount == 0:
                return {"success": False, "error": "Friendship not found"}

            conn.commit()
            conn.close()

            return {"success": True, "message": "Friend removed"}

        except Exception as e:
            logger.error(f"Error removing friend: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def block_user(user_id: int, blocked_user_id: int,
                   reason: Optional[str] = None) -> Dict[str, Any]:
        """Block a user"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Remove friendship if exists
            cursor.execute("""
                DELETE FROM friendships
                WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
            """, (user_id, blocked_user_id, blocked_user_id, user_id))

            # Cancel any pending requests
            cursor.execute("""
                UPDATE friend_requests
                SET status = 'cancelled', updated_at = datetime('now')
                WHERE (from_user_id = ? AND to_user_id = ?) OR (from_user_id = ? AND to_user_id = ?)
                AND status = 'pending'
            """, (user_id, blocked_user_id, blocked_user_id, user_id))

            # Add to blocked list
            cursor.execute("""
                INSERT OR IGNORE INTO blocked_users (user_id, blocked_user_id, reason)
                VALUES (?, ?, ?)
            """, (user_id, blocked_user_id, reason))

            conn.commit()
            conn.close()

            return {"success": True, "message": "User blocked"}

        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def unblock_user(user_id: int, blocked_user_id: int) -> Dict[str, Any]:
        """Unblock a user"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM blocked_users
                WHERE user_id = ? AND blocked_user_id = ?
            """, (user_id, blocked_user_id))

            if cursor.rowcount == 0:
                return {"success": False, "error": "User not blocked"}

            conn.commit()
            conn.close()

            return {"success": True, "message": "User unblocked"}

        except Exception as e:
            logger.error(f"Error unblocking user: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_friends_list(user_id: int, limit: int = 100,
                         offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's friends list with online status"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            friends = cursor.execute("""
                SELECT
                    u.user_id,
                    u.username,
                    u.first_name,
                    u.last_name,
                    u.is_premium,
                    up.avatar_url,
                    up.bio,
                    uos.is_online,
                    uos.last_seen,
                    f.created_at as friends_since
                FROM friendships f
                JOIN users u ON u.user_id = f.friend_id
                LEFT JOIN user_profiles up ON u.user_id = up.user_id
                LEFT JOIN user_online_status uos ON u.user_id = uos.user_id
                WHERE f.user_id = ? AND f.status = 'accepted'
                ORDER BY uos.is_online DESC, uos.last_seen DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset)).fetchall()

            conn.close()

            return [dict(row) for row in friends]

        except Exception as e:
            logger.error(f"Error getting friends list: {e}")
            return []

    @staticmethod
    def get_friend_requests(
            user_id: int, request_type: str = 'received') -> List[Dict[str, Any]]:
        """
        Get friend requests

        Args:
            user_id: User ID
            request_type: 'received' or 'sent'
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            if request_type == 'received':
                requests = cursor.execute("""
                    SELECT
                        fr.id as request_id,
                        fr.from_user_id,
                        fr.message,
                        fr.created_at,
                        u.username,
                        u.first_name,
                        u.last_name,
                        up.avatar_url,
                        up.bio
                    FROM friend_requests fr
                    JOIN users u ON u.user_id = fr.from_user_id
                    LEFT JOIN user_profiles up ON u.user_id = up.user_id
                    WHERE fr.to_user_id = ? AND fr.status = 'pending'
                    ORDER BY fr.created_at DESC
                """, (user_id,)).fetchall()
            else:  # sent
                requests = cursor.execute("""
                    SELECT
                        fr.id as request_id,
                        fr.to_user_id,
                        fr.message,
                        fr.created_at,
                        u.username,
                        u.first_name,
                        u.last_name,
                        up.avatar_url
                    FROM friend_requests fr
                    JOIN users u ON u.user_id = fr.to_user_id
                    LEFT JOIN user_profiles up ON u.user_id = up.user_id
                    WHERE fr.from_user_id = ? AND fr.status = 'pending'
                    ORDER BY fr.created_at DESC
                """, (user_id,)).fetchall()

            conn.close()

            return [dict(row) for row in requests]

        except Exception as e:
            logger.error(f"Error getting friend requests: {e}")
            return []

    @staticmethod
    def get_blocked_users(user_id: int) -> List[Dict[str, Any]]:
        """Get list of blocked users"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            blocked = cursor.execute("""
                SELECT
                    b.id,
                    b.blocked_user_id,
                    b.reason,
                    b.created_at,
                    u.username,
                    u.first_name,
                    u.last_name,
                    up.avatar_url
                FROM blocked_users b
                JOIN users u ON u.user_id = b.blocked_user_id
                LEFT JOIN user_profiles up ON u.user_id = up.user_id
                WHERE b.user_id = ?
                ORDER BY b.created_at DESC
            """, (user_id,)).fetchall()

            conn.close()

            return [dict(row) for row in blocked]

        except Exception as e:
            logger.error(f"Error getting blocked users: {e}")
            return []

    @staticmethod
    def get_friendship_status(user_id: int, other_user_id: int) -> str:
        """Get friendship status between two users"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Check if friends
            friendship = cursor.execute("""
                SELECT id FROM friendships
                WHERE ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
                AND status = 'accepted'
            """, (user_id, other_user_id, other_user_id, user_id)).fetchone()

            if friendship:
                conn.close()
                return 'friends'

            # Check for pending request
            request = cursor.execute("""
                SELECT from_user_id FROM friend_requests
                WHERE ((from_user_id = ? AND to_user_id = ?) OR (from_user_id = ? AND to_user_id = ?))
                AND status = 'pending'
            """, (user_id, other_user_id, other_user_id, user_id)).fetchone()

            if request:
                conn.close()
                return 'request_sent' if request['from_user_id'] == user_id else 'request_received'

            # Check if blocked
            blocked = cursor.execute("""
                SELECT id FROM blocked_users
                WHERE user_id = ? AND blocked_user_id = ?
            """, (user_id, other_user_id)).fetchone()

            conn.close()

            return 'blocked' if blocked else 'none'

        except Exception as e:
            logger.error(f"Error getting friendship status: {e}")
            return 'none'

# Made with Bob
