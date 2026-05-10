"""
Handlers for forum_topic_created / forum_topic_edited events.
Delegates to sync_bot.register_topic().
"""
from telegram import Update
from telegram.ext import ContextTypes
from app.sync_bot import register_topic, parse_topic_name
from app.database import set_topic_series_map
import logging

logger = logging.getLogger(__name__)


async def handle_new_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.forum_topic_created:
        return
    topic_name = msg.forum_topic_created.name
    topic_id = msg.message_thread_id or msg.message_id
    logger.info(f"New topic: '{topic_name}' id={topic_id}")
    ok = await register_topic(topic_name, topic_id)
    parsed = parse_topic_name(topic_name)
    if parsed and parsed["type"] == "series":
        set_topic_series_map(topic_id, parsed["internal_id"])
    if ok:
        logger.info(f"✅ Auto-registered: {topic_name}")


async def handle_edited_topic(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.forum_topic_edited:
        return
    topic_name = msg.forum_topic_edited.name
    topic_id = msg.message_thread_id or msg.message_id
    logger.info(f"Topic renamed: '{topic_name}' id={topic_id}")
    await register_topic(topic_name, topic_id)
    parsed = parse_topic_name(topic_name)
    if parsed and parsed["type"] == "series":
        set_topic_series_map(topic_id, parsed["internal_id"])
