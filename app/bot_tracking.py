"""
PopCorn Bot Tracking Module
Integrates bot interactions with the existing user tracking system.
Tracks all bot commands, button clicks, and user sessions.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Bot Interaction Tracking
# ══════════════════════════════════════════════════════════════════════════════

class BotTracker:
    """Tracks bot interactions and integrates with user tracking system."""

    def __init__(self, db_connection_pool):
        """
        Initialize bot tracker.

        Args:
            db_connection_pool: Database connection pool instance
        """
        self.db_pool = db_connection_pool
        self._init_tracking_tables()

    def _init_tracking_tables(self):
        """Initialize bot tracking tables if they don't exist."""
        try:
            with self.db_pool.get_connection() as conn:
                # Bot sessions table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bot_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ended_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        platform TEXT DEFAULT 'telegram_bot',
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)

                # Bot interactions table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bot_interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_id TEXT,
                        interaction_type TEXT NOT NULL,
                        interaction_data TEXT,
                        callback_data TEXT,
                        command TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (session_id) REFERENCES bot_sessions(session_id)
                    )
                """)

                # Button clicks table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bot_button_clicks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_id TEXT,
                        button_callback TEXT NOT NULL,
                        button_text TEXT,
                        context_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (session_id) REFERENCES bot_sessions(session_id)
                    )
                """)

                # Create indexes for performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_bot_interactions_user
                    ON bot_interactions(user_id, timestamp DESC)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_bot_interactions_type
                    ON bot_interactions(interaction_type, timestamp DESC)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_bot_button_clicks_user
                    ON bot_button_clicks(user_id, timestamp DESC)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_bot_sessions_user
                    ON bot_sessions(user_id, is_active)
                """)

                logger.info("✅ Bot tracking tables initialized")
        except Exception as e:
            logger.error(
                f"Error initializing bot tracking tables: {e}",
                exc_info=True)

    def get_or_create_session(self, user_id: int) -> Optional[str]:
        """
        Get active session or create new one for user.

        Args:
            user_id: Telegram user ID

        Returns:
            Session ID or None if error
        """
        try:
            with self.db_pool.get_connection() as conn:
                # Check for active session
                cursor = conn.execute("""
                    SELECT session_id FROM bot_sessions
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY started_at DESC LIMIT 1
                """, (user_id,))

                result = cursor.fetchone()

                if result:
                    session_id = result[0]
                    # Update last activity
                    conn.execute("""
                        UPDATE bot_sessions
                        SET last_activity = ?
                        WHERE session_id = ?
                    """, (datetime.now(), session_id))
                    return session_id

                # Create new session
                session_id = f"bot_{user_id}_{int(datetime.now().timestamp())}"
                conn.execute("""
                    INSERT INTO bot_sessions (session_id, user_id, started_at, last_activity)
                    VALUES (?, ?, ?, ?)
                """, (session_id, user_id, datetime.now(), datetime.now()))

                logger.info(
                    f"📱 Created new bot session: {session_id} for user {user_id}")
                return session_id

        except Exception as e:
            logger.error(f"Error managing bot session for user {user_id}: {e}")
            return None

    def end_session(self, session_id: str):
        """
        End a bot session.

        Args:
            session_id: Session ID to end
        """
        try:
            with self.db_pool.get_connection() as conn:
                conn.execute("""
                    UPDATE bot_sessions
                    SET ended_at = ?, is_active = 0
                    WHERE session_id = ?
                """, (datetime.now(), session_id))

                logger.info(f"🔚 Ended bot session: {session_id}")
        except Exception as e:
            logger.error(f"Error ending bot session {session_id}: {e}")

    def track_interaction(
        self,
        user_id: int,
        interaction_type: str,
        interaction_data: Optional[Dict[str, Any]] = None,
        callback_data: Optional[str] = None,
        command: Optional[str] = None
    ):
        """
        Track a bot interaction.

        Args:
            user_id: Telegram user ID
            interaction_type: Type of interaction (command, callback, message, etc.)
            interaction_data: Additional data about the interaction
            callback_data: Callback data if applicable
            command: Command name if applicable
        """
        try:
            session_id = self.get_or_create_session(user_id)

            import json
            data_json = json.dumps(
                interaction_data) if interaction_data else None

            with self.db_pool.get_connection() as conn:
                conn.execute("""
                    INSERT INTO bot_interactions
                    (user_id, session_id, interaction_type, interaction_data, callback_data, command, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, session_id, interaction_type, data_json, callback_data, command, datetime.now()))

                logger.debug(
                    f"📊 Tracked {interaction_type} interaction for user {user_id}")

        except Exception as e:
            logger.error(f"Error tracking interaction for user {user_id}: {e}")

    def track_button_click(
        self,
        user_id: int,
        button_callback: str,
        button_text: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ):
        """
        Track a button click.

        Args:
            user_id: Telegram user ID
            button_callback: Callback data of the button
            button_text: Text displayed on the button
            context_data: Additional context about the click
        """
        try:
            session_id = self.get_or_create_session(user_id)

            import json
            context_json = json.dumps(context_data) if context_data else None

            with self.db_pool.get_connection() as conn:
                conn.execute("""
                    INSERT INTO bot_button_clicks
                    (user_id, session_id, button_callback, button_text, context_data, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, session_id, button_callback, button_text, context_json, datetime.now()))

                logger.debug(
                    f"🔘 Tracked button click: {button_callback} for user {user_id}")

        except Exception as e:
            logger.error(
                f"Error tracking button click for user {user_id}: {e}")

    def track_command(
            self,
            user_id: int,
            command: str,
            args: Optional[str] = None):
        """
        Track a bot command.

        Args:
            user_id: Telegram user ID
            command: Command name (without /)
            args: Command arguments if any
        """
        self.track_interaction(
            user_id=user_id,
            interaction_type="command",
            command=command,
            interaction_data={"args": args} if args else None
        )

    def track_message(self, user_id: int, message_type: str,
                      content_preview: Optional[str] = None):
        """
        Track a user message.

        Args:
            user_id: Telegram user ID
            message_type: Type of message (text, photo, video, etc.)
            content_preview: Preview of message content
        """
        self.track_interaction(
            user_id=user_id,
            interaction_type="message",
            interaction_data={
                "message_type": message_type,
                "preview": content_preview[:100] if content_preview else None
            }
        )

    def get_user_interactions(
        self,
        user_id: int,
        limit: int = 50,
        interaction_type: Optional[str] = None
    ) -> list:
        """
        Get recent interactions for a user.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of interactions to return
            interaction_type: Filter by interaction type

        Returns:
            List of interaction dictionaries
        """
        try:
            with self.db_pool.get_connection() as conn:
                query = """
                    SELECT * FROM bot_interactions
                    WHERE user_id = ?
                """
                params = [user_id]

                if interaction_type:
                    query += " AND interaction_type = ?"
                    params.append(interaction_type)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting interactions for user {user_id}: {e}")
            return []

    def get_button_click_stats(self, days: int = 7) -> Dict[str, int]:
        """
        Get button click statistics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary mapping button callbacks to click counts
        """
        try:
            with self.db_pool.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT button_callback, COUNT(*) as click_count
                    FROM bot_button_clicks
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY button_callback
                    ORDER BY click_count DESC
                """, (days,))

                rows = cursor.fetchall()
                return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"Error getting button click stats: {e}")
            return {}

    def get_active_sessions_count(self) -> int:
        """
        Get count of currently active bot sessions.

        Returns:
            Number of active sessions
        """
        try:
            with self.db_pool.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM bot_sessions
                    WHERE is_active = 1
                """)
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting active sessions count: {e}")
            return 0


# ══════════════════════════════════════════════════════════════════════════════
# Decorator for Automatic Tracking
# ══════════════════════════════════════════════════════════════════════════════

def track_bot_interaction(interaction_type: str):
    """
    Decorator to automatically track bot interactions.

    Usage:
        @track_bot_interaction("command")
        async def start_command(update, context):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(
                update: Update,
                context: ContextTypes.DEFAULT_TYPE,
                *args,
                **kwargs):
            user = update.effective_user

            if user:
                # Get tracker from context
                tracker = context.bot_data.get('bot_tracker')

                if tracker:
                    # Extract relevant data
                    callback_data = None
                    command = None

                    if update.callback_query:
                        callback_data = update.callback_query.data
                        tracker.track_button_click(
                            user_id=user.id,
                            button_callback=callback_data,
                            button_text=update.callback_query.message.text[:50] if update.callback_query.message else None
                        )

                    if update.message and update.message.text and update.message.text.startswith(
                            '/'):
                        command = update.message.text.split()[
                            0][1:]  # Remove /
                        tracker.track_command(user_id=user.id, command=command)

                    # Track general interaction
                    tracker.track_interaction(
                        user_id=user.id,
                        interaction_type=interaction_type,
                        callback_data=callback_data,
                        command=command
                    )

            # Execute the original function
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
# Integration with User Tracking
# ══════════════════════════════════════════════════════════════════════════════

def integrate_with_user_tracking(
        user_id: int,
        activity_type: str,
        details: Optional[str] = None):
    """
    Integrate bot tracking with the existing user_tracking system.

    Args:
        user_id: Telegram user ID
        activity_type: Type of activity
        details: Additional details
    """
    try:
        from app import database as db
        db.log_user_activity(
            user_id=user_id,
            activity_type=activity_type,
            activity_details=details
        )
    except Exception as e:
        logger.error(f"Error integrating with user tracking: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════════════

def get_popular_buttons(tracker: BotTracker, limit: int = 10) -> list:
    """
    Get most popular buttons by click count.

    Args:
        tracker: BotTracker instance
        limit: Number of buttons to return

    Returns:
        List of tuples (button_callback, click_count)
    """
    stats = tracker.get_button_click_stats(days=30)
    sorted_buttons = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    return sorted_buttons[:limit]


def get_user_journey(
        tracker: BotTracker,
        user_id: int,
        limit: int = 20) -> list:
    """
    Get user's interaction journey (sequence of actions).

    Args:
        tracker: BotTracker instance
        user_id: Telegram user ID
        limit: Number of interactions to return

    Returns:
        List of interactions in chronological order
    """
    interactions = tracker.get_user_interactions(user_id, limit=limit)
    return list(reversed(interactions))  # Chronological order


# Made with Bob
