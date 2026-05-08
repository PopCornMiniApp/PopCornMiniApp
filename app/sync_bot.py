"""
Sync Bot: reads POPCORN DB private group topics and syncs content to HF Dataset.

Topic name format:
  Movies:  #MovieName #movies #mid00019 #480530
  Series:  #SeriesName #series #s4 #sid00003 #80752

Episode caption format:
  Movie file:  #MovieName #Movie
  Episode:     #SeriesName #S4 #E8
"""

import re
import logging
import asyncio
import sqlite3
from telegram import Bot, Update
from telegram.ext import (
    Application, MessageHandler, CommandHandler, filters, ContextTypes
)
from app.config import (
    MAIN_BOT_TOKEN, PRIVATE_GROUP_ID, ADMIN_ID, DB_PATH,
)
from app import database as db
from app.tmdb import fetch_movie, fetch_series, fetch_episode_info
from app.database import push_db_to_hf

logger = logging.getLogger(__name__)

MOVIE_TOPIC_RE = re.compile(
    r'#(\w+)\s+#movies\s+#(mid\d+)\s+#(\d+)', re.IGNORECASE
)
SERIES_TOPIC_RE = re.compile(
    r'#(\w+)\s+#series\s+(?:#s\d+\s+)?#(sid\d+)\s+#(\d+)', re.IGNORECASE
)
EPISODE_CAP_RE = re.compile(
    r'#\w+\s+#[Ss](\d+)\s+#[Ee](\d+)', re.IGNORECASE
)
MOVIE_CAP_RE = re.compile(
    r'#\w+\s+#Movie\b', re.IGNORECASE
)


def parse_topic_name(name: str) -> dict | None:
    m = MOVIE_TOPIC_RE.search(name)
    if m:
        return {
            "type": "movie",
            "slug": m.group(1),
            "internal_id": m.group(2),
            "tmdb_id": int(m.group(3)),
        }
    m = SERIES_TOPIC_RE.search(name)
    if m:
        return {
            "type": "series",
            "slug": m.group(1),
            "internal_id": m.group(2),
            "tmdb_id": int(m.group(3)),
        }
    return None


def _find_movie_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM movies WHERE topic_id=?", (topic_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _find_series_by_topic(topic_id: int) -> dict | None:
    """Find a series whose episodes belong to this topic_id."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT s.* FROM series s
            INNER JOIN episodes e ON e.series_id = s.id
            WHERE e.topic_id = ?
            LIMIT 1
            """,
            (topic_id,),
        ).fetchone()
        if row:
            return dict(row)
        row2 = conn.execute(
            "SELECT * FROM series WHERE id IN (SELECT id FROM series WHERE id LIKE '%') LIMIT 1"
        ).fetchone()
        return None
    finally:
        conn.close()


def _find_series_by_topic_id_direct(topic_id: int) -> dict | None:
    """Find series that have this topic_id stored in any episode."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM series WHERE id IN "
            "(SELECT DISTINCT series_id FROM episodes WHERE topic_id=?) LIMIT 1",
            (topic_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


async def handle_private_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    if msg.chat_id != PRIVATE_GROUP_ID:
        return

    video = msg.video or (msg.document if msg.document and msg.document.mime_type and 'video' in msg.document.mime_type else None)
    if not video:
        return

    topic_id = msg.message_thread_id
    caption = (msg.caption or msg.text or "").strip()

    ep_match = EPISODE_CAP_RE.search(caption)
    mov_match = MOVIE_CAP_RE.search(caption)

    if ep_match:
        season = int(ep_match.group(1))
        episode = int(ep_match.group(2))
        await _handle_episode(video, topic_id, msg.message_id, season, episode)
    elif mov_match:
        await _handle_movie_file(video, topic_id, msg.message_id)
    else:
        logger.warning(f"No pattern matched for caption: '{caption}' in topic {topic_id}")


async def _handle_movie_file(video, topic_id: int, message_id: int):
    movie = _find_movie_by_topic(topic_id)
    if not movie:
        logger.warning(f"No movie registered for topic_id={topic_id}")
        return

    db.upsert_movie({
        **movie,
        "file_id": video.file_id,
        "file_size": getattr(video, "file_size", 0),
        "duration": getattr(video, "duration", 0),
        "topic_id": topic_id,
        "message_id": message_id,
    })
    push_db_to_hf()
    logger.info(f"✅ Movie file saved: {movie.get('title')} | file_id={video.file_id[:20]}...")


async def _handle_episode(video, topic_id: int, message_id: int, season: int, episode_num: int):
    series = _find_series_by_topic_id_direct(topic_id)
    if not series:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        all_series = [dict(r) for r in conn.execute("SELECT * FROM series").fetchall()]
        conn.close()
        logger.warning(f"No series for topic_id={topic_id}. Available series: {[s['id'] for s in all_series]}")
        return

    ep_info = await fetch_episode_info(series["tmdb_id"], season, episode_num) or {}

    duration = getattr(video, "duration", 0)
    db.upsert_episode({
        "series_id": series["id"],
        "season_number": season,
        "episode_number": episode_num,
        "title": ep_info.get("title", f"Episode {episode_num}"),
        "overview": ep_info.get("overview", ""),
        "still_path": ep_info.get("still_path", ""),
        "air_date": ep_info.get("air_date", ""),
        "runtime": ep_info.get("runtime") or (duration // 60 if duration else 0),
        "file_id": video.file_id,
        "file_unique_id": getattr(video, "file_unique_id", ""),
        "file_size": getattr(video, "file_size", 0),
        "duration": duration,
        "topic_id": topic_id,
        "message_id": message_id,
    })
    push_db_to_hf()
    logger.info(f"✅ Episode saved: {series.get('title')} S{season}E{episode_num}")


async def register_topic(topic_name: str, topic_id: int) -> bool:
    """Parse a topic name and register movie/series with TMDB data."""
    parsed = parse_topic_name(topic_name)
    if not parsed:
        logger.warning(f"Could not parse topic name: {topic_name}")
        return False

    if parsed["type"] == "movie":
        existing = db.get_movie(movie_id=parsed["internal_id"])
        if existing:
            logger.info(f"Movie already registered: {parsed['internal_id']}")
            return True

        tmdb_data = await fetch_movie(parsed["tmdb_id"])
        if not tmdb_data:
            return False

        db.upsert_movie({
            "id": parsed["internal_id"],
            "topic_id": topic_id,
            "message_id": None,
            "file_id": None,
            "file_size": None,
            "duration": None,
            **tmdb_data,
        })
        logger.info(f"✅ Movie registered: {tmdb_data['title']} (TMDB:{parsed['tmdb_id']})")

    elif parsed["type"] == "series":
        existing = db.get_series(series_id=parsed["internal_id"])
        if existing:
            logger.info(f"Series already registered: {parsed['internal_id']}")
            return True

        tmdb_data = await fetch_series(parsed["tmdb_id"])
        if not tmdb_data:
            return False

        db.upsert_series({
            "id": parsed["internal_id"],
            **tmdb_data,
        })
        logger.info(f"✅ Series registered: {tmdb_data['title']} (TMDB:{parsed['tmdb_id']})")

    push_db_to_hf()
    return True


async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or msg.from_user.id != ADMIN_ID:
        return

    text = (msg.text or "").strip()

    if text.startswith("/stats"):
        stats = db.get_stats()
        await msg.reply_text(
            f"📊 *PopCorn Stats*\n\n"
            f"🎬 Movies: {stats['movies_count']}\n"
            f"📺 Series: {stats['series_count']}\n"
            f"🎞 Episodes: {stats['episodes_count']}",
            parse_mode="Markdown"
        )

    elif text.startswith("/register"):
        parts = text.split()
        if len(parts) >= 3:
            topic_name_parts = parts[1:-1]
            topic_id = int(parts[-1])
            topic_name = " ".join(topic_name_parts)
            ok = await register_topic(topic_name, topic_id)
            await msg.reply_text("✅ Registered!" if ok else "❌ Failed to register")
        else:
            await msg.reply_text(
                "❌ Usage: /register #Name #movies #mid00001 #TMDB_ID TOPIC_ID\n"
                "Example: /register '#BeautifulBoy #movies #mid00019 #480530' 1234567"
            )

    elif text.startswith("/sync_db"):
        push_db_to_hf()
        await msg.reply_text("✅ Database synced to HuggingFace!")


def build_sync_app() -> Application:
    from app.register_topic_handler import handle_new_topic, handle_edited_topic

    app = (
        Application.builder()
        .token(MAIN_BOT_TOKEN)
        .build()
    )

    app.add_handler(MessageHandler(
        filters.Chat(PRIVATE_GROUP_ID) & (
            filters.VIDEO |
            (filters.Document.ALL & filters.Chat(PRIVATE_GROUP_ID))
        ),
        handle_private_group_message,
    ))

    app.add_handler(MessageHandler(
        filters.Chat(PRIVATE_GROUP_ID) & filters.StatusUpdate.FORUM_TOPIC_CREATED,
        handle_new_topic,
    ))

    app.add_handler(MessageHandler(
        filters.Chat(PRIVATE_GROUP_ID) & filters.StatusUpdate.FORUM_TOPIC_EDITED,
        handle_edited_topic,
    ))

    app.add_handler(CommandHandler(
        ["stats", "register", "sync_db"],
        handle_admin_command,
        filters=filters.User(ADMIN_ID),
    ))

    return app
