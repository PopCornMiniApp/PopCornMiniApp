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
    return True


def _find_movie_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM movies WHERE topic_id=?", (topic_id,)).fetchone()
        return dict(row) if row else None
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
        # Fallback: look up by topic_id in a temporary mapping
        row2 = conn.execute(
            "SELECT * FROM series WHERE id IN "
            "(SELECT series_id FROM topic_series_map WHERE topic_id=?) LIMIT 1", (topic_id,)
        ).fetchone()
        return dict(row2) if row2 else None
    except Exception:
        return None
    finally:
        conn.close()


def _map_topic_to_series(topic_id: int, series_id: str):
    """Store topic→series mapping so episode uploads can find their series."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_series_map (
                topic_id INTEGER PRIMARY KEY,
                series_id TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT OR REPLACE INTO topic_series_map(topic_id, series_id) VALUES(?,?)",
            (topic_id, series_id)
        )
        conn.commit()
    finally:
        conn.close()


def _get_series_for_topic(topic_id: int) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_series_map (
                topic_id INTEGER PRIMARY KEY, series_id TEXT NOT NULL
            )
        """)
        row = conn.execute(
            "SELECT series_id FROM topic_series_map WHERE topic_id=?", (topic_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


async def handle_group_message(update: Update, context):
    msg = update.effective_message
    if not msg or msg.chat_id != PRIVATE_GROUP_ID:
        return

    thread_id = msg.message_thread_id

    # ── New / renamed topic ──────────────────────────────────────────────────
    for ev in ["forum_topic_created", "forum_topic_edited"]:
        event = getattr(msg, ev, None)
        if event:
            topic_name = event.name
            logger.info(f"Topic event '{ev}': {topic_name} (id={thread_id})")
            ok = await register_topic(topic_name, thread_id)

            # Store series<→topic mapping
            parsed = parse_topic_name(topic_name)
            if parsed and parsed["type"] == "series":
                _map_topic_to_series(thread_id, parsed["internal_id"])
            if ok:
                await msg.reply_text(f"✅ تم تسجيل: {topic_name[:50]}", message_thread_id=thread_id)
            return

    # ── Video / Document file ────────────────────────────────────────────────
    video = msg.video or (
        msg.document if msg.document and msg.document.mime_type
        and 'video' in msg.document.mime_type else None
    )
    if not video or not thread_id:
        return

    caption = (msg.caption or msg.text or "").strip()
    ep_m  = EPISODE_CAP_RE.search(caption)
    mov_m = MOVIE_CAP_RE.search(caption)

    if ep_m:
        season, ep_num = int(ep_m.group(1)), int(ep_m.group(2))
        await _save_episode(video, thread_id, msg.message_id, season, ep_num)
    elif mov_m:
        await _save_movie_file(video, thread_id, msg.message_id)
    else:
        logger.debug(f"Unrecognised caption: '{caption}' in topic {thread_id}")


async def _save_movie_file(video, topic_id: int, message_id: int):
    movie = _find_movie_by_topic(topic_id)
    if not movie:
        logger.warning(f"No movie for topic {topic_id}")
        return
    db.upsert_movie({
        **movie,
        "file_id":   video.file_id,
        "file_size": getattr(video, "file_size", 0),
        "duration":  getattr(video, "duration", 0),
        "topic_id":  topic_id,
        "message_id": message_id,
    })
    push_db_to_hf()
    logger.info(f"✅ Movie file saved: {movie.get('title')}")


async def _save_episode(video, topic_id: int, message_id: int, season: int, ep_num: int):
    series_id = _get_series_for_topic(topic_id)
    if not series_id:
        logger.warning(f"No series mapped to topic {topic_id}")
        return
    series = db.get_series(series_id=series_id)
    if not series:
        logger.warning(f"Series {series_id} not in DB")
        return

    duration = getattr(video, "duration", 0)
    ep_info = await fetch_episode_info(series["tmdb_id"], season, ep_num) or {}
    db.upsert_episode({
        "series_id":      series_id,
        "season_number":  season,
        "episode_number": ep_num,
        "title":     ep_info.get("title", f"Episode {ep_num}"),
        "overview":  ep_info.get("overview", ""),
        "still_path": ep_info.get("still_path", ""),
        "air_date":  ep_info.get("air_date", ""),
        "runtime":   ep_info.get("runtime") or (duration // 60 if duration else 0),
        "file_id":       video.file_id,
        "file_unique_id": getattr(video, "file_unique_id", ""),
        "file_size":     getattr(video, "file_size", 0),
        "duration":      duration,
        "topic_id":      topic_id,
        "message_id":    message_id,
    })
    push_db_to_hf()
    logger.info(f"✅ Episode saved: {series.get('title')} S{season}E{ep_num}")


async def handle_admin_cmd(update: Update, context):
    msg = update.effective_message
    if not msg or msg.from_user.id != ADMIN_ID:
        return
    text = (msg.text or "").strip()

    if text.startswith("/stats"):
        s = db.get_stats()
        await msg.reply_text(
            f"📊 *PopCorn Stats*\n\n🎬 أفلام: {s['movies_count']}\n"
            f"📺 مسلسلات: {s['series_count']}\n🎞 حلقات: {s['episodes_count']}",
            parse_mode="Markdown"
        )

    elif text.startswith("/register"):
        parts = text.split()
        if len(parts) >= 3:
            topic_id   = int(parts[-1])
            topic_name = " ".join(parts[1:-1])
            ok = await register_topic(topic_name, topic_id)
            parsed = parse_topic_name(topic_name)
            if parsed and parsed["type"] == "series":
                _map_topic_to_series(topic_id, parsed["internal_id"])
            await msg.reply_text("✅ تم التسجيل!" if ok else "❌ فشل التسجيل")

    elif text.startswith("/sync_db"):
        push_db_to_hf()
        await msg.reply_text("✅ تمت المزامنة مع HuggingFace!")

    elif text.startswith("/list"):
        s = db.get_stats()
        movies = "\n".join(f"  🎬 {m['title']}" for m in s['latest_movies'])
        series = "\n".join(f"  📺 {s2['title']}" for s2 in s['latest_series'])
        await msg.reply_text(f"*أحدث الأفلام:*\n{movies}\n\n*أحدث المسلسلات:*\n{series}", parse_mode="Markdown")


def build_sync_app() -> Application:
    from app.register_topic_handler import handle_new_topic, handle_edited_topic

    application = Application.builder().token(MAIN_BOT_TOKEN).build()

    # Group messages
    application.add_handler(MessageHandler(
        filters.Chat(PRIVATE_GROUP_ID), handle_group_message
    ))

    # Admin commands (private)
    application.add_handler(CommandHandler(
        ["stats", "register", "sync_db", "list"],
        handle_admin_cmd,
        filters=filters.User(ADMIN_ID)
    ))

    return application
