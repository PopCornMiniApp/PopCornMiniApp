"""
Sync Bot — automatic sync from POPCORN DB private group.

Topic name format (ignore 'general' topic):
  Movies:  #Title #movies #midXXXXX #TMDB_ID
  Series:  #Title #series #sN #sidXXXXX #TMDB_ID

File caption format:
  Movie:   #Title #Movie
  Episode: #Title #SN #EN
"""
import re
import logging
import asyncio
import sqlite3
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from app.config import MAIN_BOT_TOKEN, PRIVATE_GROUP_ID, ADMIN_ID, DB_PATH
from app import database as db
from app.tmdb import fetch_movie, fetch_series, fetch_episode_info
from app.database import push_db_to_hf
from app.cache import cache_clear_all

logger = logging.getLogger(__name__)

MOVIE_TOPIC_RE = re.compile(r'#([\w&]+)\s+#movies\s+#(mid\d+)\s+#(\d+)', re.IGNORECASE)
SERIES_TOPIC_RE = re.compile(r'#([\w&]+)\s+#series\s+(?:#s\d+\s+)?#(sid\d+)\s+#(\d+)', re.IGNORECASE)
EPISODE_CAP_RE = re.compile(r'#[\w&]+\s+#[Ss](\d+)\s+#[Ee](\d+)', re.IGNORECASE)
MOVIE_CAP_RE   = re.compile(r'#[\w&]+\s+#Movie\b', re.IGNORECASE)
GENERAL_RE     = re.compile(r'general', re.IGNORECASE)


def parse_topic_name(name: str) -> dict | None:
    if GENERAL_RE.search(name):
        return None
    m = MOVIE_TOPIC_RE.search(name)
    if m:
        return {"type": "movie", "slug": m.group(1), "internal_id": m.group(2), "tmdb_id": int(m.group(3))}
    m = SERIES_TOPIC_RE.search(name)
    if m:
        return {"type": "series", "slug": m.group(1), "internal_id": m.group(2), "tmdb_id": int(m.group(3))}
    return None


async def register_topic(topic_name: str, topic_id: int) -> bool:
    parsed = parse_topic_name(topic_name)
    if not parsed:
        return False

    if parsed["type"] == "movie":
        existing = db.get_movie(movie_id=parsed["internal_id"])
        if existing:
            return True
        tmdb_data = await fetch_movie(parsed["tmdb_id"])
        if not tmdb_data:
            return False
        db.upsert_movie({
            "id": parsed["internal_id"], "topic_id": topic_id,
            "message_id": None, "file_id": None, "file_size": None, "duration": None,
            **tmdb_data,
        })
        logger.info(f"✅ Movie registered: {tmdb_data['title']}")

    elif parsed["type"] == "series":
        existing = db.get_series(series_id=parsed["internal_id"])
        if existing:
            return True
        tmdb_data = await fetch_series(parsed["tmdb_id"])
        if not tmdb_data:
            return False
        db.upsert_series({"id": parsed["internal_id"], **tmdb_data})
        logger.info(f"✅ Series registered: {tmdb_data['title']}")

    push_db_to_hf()
    # Clear all in-memory cache so new content appears immediately in API
    cache_clear_all()
    return True


def _find_movie_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM movies WHERE topic_id=?", (topic_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _map_topic_to_series(topic_id: int) -> str | None:
    """Return series_id for a topic_id from topic_series_map table (if exists)."""
    conn = sqlite3.connect(DB_PATH)
    try:
        try:
            row = conn.execute(
                "SELECT series_id FROM topic_series_map WHERE topic_id=?", (topic_id,)
            ).fetchone()
            return row[0] if row else None
        except sqlite3.OperationalError:
            return None
    finally:
        conn.close()


def _find_series_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT s.* FROM series s "
            "INNER JOIN episodes e ON e.series_id=s.id "
            "WHERE e.topic_id=? LIMIT 1", (topic_id,)
        ).fetchone()
        if row:
            return dict(row)
        # Fallback: topic_series_map
        sid = _map_topic_to_series(topic_id)
        if sid:
            row2 = conn.execute("SELECT * FROM series WHERE id=?", (sid,)).fetchone()
            return dict(row2) if row2 else None
        return None
    finally:
        conn.close()


async def handle_file_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video/document messages in the private group topics."""
    msg = update.effective_message
    if not msg:
        return

    # Only care about messages from the private group
    chat_id = msg.chat_id if msg.chat_id else (msg.chat.id if msg.chat else None)
    if chat_id != PRIVATE_GROUP_ID:
        return

    # Must have a caption with hashtags
    caption = msg.caption or ""
    if not caption.strip():
        return

    # Extract file info
    file_obj = msg.video or msg.document
    if not file_obj:
        return

    file_id = file_obj.file_id
    file_size = getattr(file_obj, "file_size", None) or 0
    duration = getattr(file_obj, "duration", None) or 0
    message_id = msg.message_id
    topic_id = getattr(msg, "message_thread_id", None) or 0

    # ── Movie file ──────────────────────────────────────────────────────────
    if MOVIE_CAP_RE.search(caption):
        movie = _find_movie_by_topic(topic_id)
        if movie:
            db.update_movie_file(movie["id"], file_id, file_size, duration, message_id)
            push_db_to_hf()
            cache_clear_all()
            logger.info(f"✅ Movie file saved: {movie['title']} — file_id={file_id[:20]}...")
        else:
            logger.warning(f"No movie found for topic_id={topic_id}")
        return

    # ── Episode file ────────────────────────────────────────────────────────
    ep_match = EPISODE_CAP_RE.search(caption)
    if ep_match:
        season_num  = int(ep_match.group(1))
        episode_num = int(ep_match.group(2))

        series = _find_series_by_topic(topic_id)
        if not series:
            logger.warning(f"No series found for topic_id={topic_id}")
            return

        # Ensure episode row exists (upsert metadata from TMDB if needed)
        existing_ep = db.get_episode(series["id"], season_num, episode_num)
        if not existing_ep:
            ep_meta = await fetch_episode_info(series.get("tmdb_id"), season_num, episode_num)
            db.upsert_episode({
                "series_id": series["id"],
                "season_number": season_num,
                "episode_number": episode_num,
                "title": ep_meta.get("title", f"الحلقة {episode_num}") if ep_meta else f"الحلقة {episode_num}",
                "overview": ep_meta.get("overview", "") if ep_meta else "",
                "still_path": ep_meta.get("still_path", "") if ep_meta else "",
                "air_date": ep_meta.get("air_date", "") if ep_meta else "",
                "runtime": ep_meta.get("runtime", 0) if ep_meta else 0,
                "topic_id": topic_id,
            })

        db.update_episode_file(series["id"], season_num, episode_num,
                               file_id, file_size, duration, message_id, topic_id)
        push_db_to_hf()
        cache_clear_all()
        logger.info(
            f"✅ Episode saved: {series['title']} S{season_num:02d}E{episode_num:02d} — file_id={file_id[:20]}..."
        )
        return

    logger.debug(f"Message in topic {topic_id} has no recognised caption pattern: {caption[:80]}")


def build_sync_app() -> Application:
    app = Application.builder().token(MAIN_BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=PRIVATE_GROUP_ID) & (filters.VIDEO | filters.Document.VIDEO),
            handle_file_message,
        )
    )
    return app
