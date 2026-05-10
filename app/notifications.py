"""
Notifications System
Handles real-time notifications via Telegram bot for friends and messages
"""

import logging
import asyncio
from typing import List, Dict, Any
from telegram import Bot
from telegram.error import TelegramError
from app.config import MAIN_BOT_TOKEN
from app import database as db

logger = logging.getLogger(__name__)


class NotificationManager:
    """Comprehensive notification system using Telegram bot"""

    _bot = None

    @classmethod
    def get_bot(cls) -> Bot:
        """Get or create bot instance"""
        if cls._bot is None:
            cls._bot = Bot(token=MAIN_BOT_TOKEN)
        return cls._bot

    @staticmethod
    def send_friend_request_notification(
            from_user_id: int,
            to_user_id: int,
            request_id: int):
        """Send notification when someone sends a friend request"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Get sender info
            sender = cursor.execute("""
                SELECT username, first_name, last_name
                FROM users WHERE user_id = ?
            """, (from_user_id,)).fetchone()

            conn.close()

            if not sender:
                return

            sender_name = sender['first_name'] or sender[
                'username'] or f"User {from_user_id}"

            message = (
                "🤝 *طلب صداقة جديد*\n\n"
                f"أرسل لك *{sender_name}* طلب صداقة!\n\n"
                "افتح التطبيق لقبول أو رفض الطلب."
            )

            # Send via Telegram
            asyncio.create_task(
                NotificationManager._send_telegram_message(to_user_id, message)
            )

        except Exception as e:
            logger.error(f"Error sending friend request notification: {e}")

    @staticmethod
    def send_friend_request_accepted_notification(
            accepter_id: int, requester_id: int):
        """Send notification when friend request is accepted"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Get accepter info
            accepter = cursor.execute("""
                SELECT username, first_name, last_name
                FROM users WHERE user_id = ?
            """, (accepter_id,)).fetchone()

            conn.close()

            if not accepter:
                return

            accepter_name = accepter['first_name'] or accepter[
                'username'] or f"User {accepter_id}"

            message = (
                "✅ *تم قبول طلب الصداقة*\n\n"
                f"قبل *{accepter_name}* طلب صداقتك!\n"
                "يمكنك الآن التواصل معه عبر الرسائل."
            )

            # Send via Telegram
            asyncio.create_task(
                NotificationManager._send_telegram_message(
                    requester_id, message))

        except Exception as e:
            logger.error(
                f"Error sending friend request accepted notification: {e}")

    @staticmethod
    def send_new_message_notification(
            conversation_id: int,
            sender_id: int,
            message_id: int):
        """Send notification for new message"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            # Get sender info
            sender = cursor.execute("""
                SELECT username, first_name, last_name
                FROM users WHERE user_id = ?
            """, (sender_id,)).fetchone()

            # Get message info
            message_info = cursor.execute("""
                SELECT content, media_type FROM messages WHERE id = ?
            """, (message_id,)).fetchone()

            # Get conversation participants (exclude sender)
            participants = cursor.execute("""
                SELECT user_id, notifications_enabled
                FROM conversation_participants
                WHERE conversation_id = ?
                  AND user_id != ?
                  AND is_active = 1
            """, (conversation_id, sender_id)).fetchall()

            # Get conversation info
            conversation = cursor.execute("""
                SELECT type, name, is_muted FROM conversations WHERE id = ?
            """, (conversation_id,)).fetchone()

            conn.close()

            if not sender or not message_info or not participants:
                return

            # Don't send if conversation is muted
            if conversation and conversation['is_muted']:
                return

            sender_name = sender['first_name'] or sender[
                'username'] or f"User {sender_id}"

            # Prepare message content
            if message_info['media_type'] == 'text':
                content_preview = message_info['content'][:50]
                if len(message_info['content']) > 50:
                    content_preview += "..."
            else:
                media_types = {
                    'photo': '📷 صورة',
                    'video': '🎥 فيديو',
                    'audio': '🎵 صوت',
                    'voice': '🎤 رسالة صوتية',
                    'document': '📄 ملف',
                    'sticker': '😊 ملصق'
                }
                content_preview = media_types.get(
                    message_info['media_type'], 'رسالة')

            # Prepare notification message
            if conversation['type'] == 'group':
                group_name = conversation['name'] or 'مجموعة'
                notification_text = (
                    f"💬 *رسالة جديدة في {group_name}*\n\n"
                    f"*{sender_name}:* {content_preview}"
                )
            else:
                notification_text = (
                    f"💬 *رسالة جديدة من {sender_name}*\n\n"
                    f"{content_preview}"
                )

            # Send to all participants
            for participant in participants:
                if participant['notifications_enabled']:
                    asyncio.create_task(
                        NotificationManager._send_telegram_message(
                            participant['user_id'],
                            notification_text
                        )
                    )

        except Exception as e:
            logger.error(f"Error sending new message notification: {e}")

    @staticmethod
    async def _send_telegram_message(
            user_id: int,
            text: str,
            parse_mode: str = 'Markdown'):
        """Send a message via Telegram bot"""
        try:
            bot = NotificationManager.get_bot()
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=parse_mode
            )
            logger.info(f"Notification sent to user {user_id}")
        except TelegramError as e:
            logger.warning(
                f"Could not send Telegram notification to {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")

    @staticmethod
    def send_bulk_notification(user_ids: List[int], title: str, message: str):
        """Send notification to multiple users"""
        try:
            notification_text = f"*{title}*\n\n{message}"

            for user_id in user_ids:
                asyncio.create_task(
                    NotificationManager._send_telegram_message(
                        user_id, notification_text))

            logger.info(f"Bulk notification sent to {len(user_ids)} users")

        except Exception as e:
            logger.error(f"Error sending bulk notification: {e}")

    @staticmethod
    def send_system_notification(
            user_id: int, notification_type: str, data: Dict[str, Any]):
        """
        Send system notifications for various events

        Args:
            user_id: Target user ID
            notification_type: Type of notification (subscription, content_update, etc.)
            data: Additional data for the notification
        """
        try:
            messages = {
                'subscription_expiring': (
                    "⚠️ *تنبيه الاشتراك*\n\n"
                    f"اشتراكك سينتهي خلال {data.get('days_left', 0)} أيام.\n"
                    "جدد اشتراكك للاستمرار في الاستمتاع بالمحتوى المميز!"
                ),
                'subscription_expired': (
                    "❌ *انتهى الاشتراك*\n\n"
                    "انتهى اشتراكك. جدده الآن للوصول إلى المحتوى المميز!"
                ),
                'new_content': (
                    "🎬 *محتوى جديد*\n\n"
                    f"تمت إضافة {data.get('content_type', 'محتوى')} جديد: "
                    f"*{data.get('title', '')}*"
                ),
                'account_warning': (
                    "⚠️ *تحذير*\n\n"
                    f"{data.get('message', 'تحذير من النظام')}"
                ),
                'account_suspended': (
                    "🚫 *تم تعليق الحساب*\n\n"
                    f"السبب: {data.get('reason', 'انتهاك الشروط')}\n"
                    "تواصل مع الدعم للمزيد من المعلومات."
                )
            }

            message = messages.get(
                notification_type, data.get(
                    'message', 'إشعار من النظام'))

            asyncio.create_task(
                NotificationManager._send_telegram_message(user_id, message)
            )

        except Exception as e:
            logger.error(f"Error sending system notification: {e}")

    @staticmethod
    def schedule_notification(user_id: int, message: str, delay_seconds: int):
        """Schedule a notification to be sent after a delay"""
        async def send_delayed():
            await asyncio.sleep(delay_seconds)
            await NotificationManager._send_telegram_message(user_id, message)

        asyncio.create_task(send_delayed())

    @staticmethod
    def get_notification_preferences(user_id: int) -> Dict[str, bool]:
        """Get user's notification preferences"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            prefs = cursor.execute("""
                SELECT notification_settings FROM user_profiles WHERE user_id = ?
            """, (user_id,)).fetchone()

            conn.close()

            if prefs and prefs['notification_settings']:
                import json
                return json.loads(prefs['notification_settings'])

            # Default preferences
            return {
                'friend_requests': True,
                'messages': True,
                'new_content': True,
                'system': True
            }

        except Exception as e:
            logger.error(f"Error getting notification preferences: {e}")
            return {}

    @staticmethod
    def update_notification_preferences(
            user_id: int, preferences: Dict[str, bool]) -> bool:
        """Update user's notification preferences"""
        try:
            import json
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO user_profiles (user_id, notification_settings)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    notification_settings = excluded.notification_settings,
                    updated_at = datetime('now')
            """, (user_id, json.dumps(preferences)))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error updating notification preferences: {e}")
            return False

    @staticmethod
    def send_typing_notification(
            conversation_id: int,
            user_id: int,
            is_typing: bool = True):
        """
        Send typing indicator notification (for WebSocket/SSE implementation)
        This is a placeholder for real-time typing indicators
        """
        # This would be implemented with WebSocket or Server-Sent Events
        # For now, we just log it
        logger.debug(
            f"User {user_id} {'started' if is_typing else 'stopped'} typing in conversation {conversation_id}")

    @staticmethod
    def send_online_status_notification(user_id: int, is_online: bool):
        """
        Send online status notification (for WebSocket/SSE implementation)
        This is a placeholder for real-time online status
        """
        # This would be implemented with WebSocket or Server-Sent Events
        logger.debug(
            f"User {user_id} is now {'online' if is_online else 'offline'}")

# Made with Bob
