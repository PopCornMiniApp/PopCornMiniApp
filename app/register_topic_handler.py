"""
Handler for new forum topics created in the private group.
When admin creates a new topic with the proper naming, it gets auto-registered.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.config import PRIVATE_GROUP_ID, ADMIN_ID
from app.sync_bot import register_topic, parse_topic_name

logger = logging.getLogger(__name__)


async def handle_new_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when a new forum topic is created."""
    msg = update.effective_message
    if not msg:
        return

    if msg.chat_id != PRIVATE_GROUP_ID:
        return

    if msg.forum_topic_created:
        topic_name = msg.forum_topic_created.name
        topic_id = msg.message_thread_id or msg.message_id

        parsed = parse_topic_name(topic_name)
        if parsed:
            logger.info(f"New topic detected: {topic_name} (id={topic_id})")
            ok = await register_topic(topic_name, topic_id)
            if ok:
                logger.info(f"✅ Auto-registered topic: {topic_name}")
            else:
                logger.warning(f"❌ Failed to register topic: {topic_name}")


async def handle_edited_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when a forum topic is renamed."""
    msg = update.effective_message
    if not msg or msg.chat_id != PRIVATE_GROUP_ID:
        return

    if msg.forum_topic_edited:
        new_name = msg.forum_topic_edited.name
        topic_id = msg.message_thread_id or msg.message_id

        parsed = parse_topic_name(new_name)
        if parsed:
            logger.info(f"Topic renamed: {new_name} (id={topic_id})")
            ok = await register_topic(new_name, topic_id)
            if ok:
                logger.info(f"✅ Re-registered renamed topic: {new_name}")
