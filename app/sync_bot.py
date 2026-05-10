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
import sqlite3
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from app.config import MAIN_BOT_TOKEN, PRIVATE_GROUP_ID, ADMIN_ID, DB_PATH
from app import database as db
from app.tmdb import fetch_movie, fetch_series, fetch_episode_info
from app.database import push_db_to_hf, set_topic_series_map
from app.cache import cache_clear_all

logger = logging.getLogger(__name__)

MOVIE_TOPIC_RE = re.compile(
    r'#([\w&]+)\s+#movies\s+#(mid\d+)\s+#(\d+)',
    re.IGNORECASE)
SERIES_TOPIC_RE = re.compile(
    r'#([\w&]+)\s+#series\s+(?:#s\d+\s+)?#(sid\d+)\s+#(\d+)',
    re.IGNORECASE)
EPISODE_CAP_RE = re.compile(
    r'#[\w&]+\s+#[Ss](\d+)\s+#[Ee](\d+)',
    re.IGNORECASE)
MOVIE_CAP_RE = re.compile(r'#[\w&]+\s+#Movie\b', re.IGNORECASE)
GENERAL_RE = re.compile(r'general', re.IGNORECASE)


def parse_topic_name(name: str) -> dict | None:
    if GENERAL_RE.search(name):
        return None
    m = MOVIE_TOPIC_RE.search(name)
    if m:
        return {
            "type": "movie",
            "slug": m.group(1),
            "internal_id": m.group(2),
            "tmdb_id": int(
                m.group(3))}
    m = SERIES_TOPIC_RE.search(name)
    if m:
        return {
            "type": "series",
            "slug": m.group(1),
            "internal_id": m.group(2),
            "tmdb_id": int(
                m.group(3))}
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
            # Still ensure topic→series map is up-to-date
            set_topic_series_map(topic_id, parsed["internal_id"])
            return True
        tmdb_data = await fetch_series(parsed["tmdb_id"])
        if not tmdb_data:
            return False
        db.upsert_series({"id": parsed["internal_id"], **tmdb_data})
        set_topic_series_map(topic_id, parsed["internal_id"])
        logger.info(f"✅ Series registered: {tmdb_data['title']}")

    push_db_to_hf()
    cache_clear_all()
    return True


def _find_movie_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM movies WHERE topic_id=?", (topic_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _find_series_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Try topic_series_map first (fastest)
        try:
            row_map = conn.execute(
                "SELECT s.* FROM series s "
                "INNER JOIN topic_series_map t ON t.series_id=s.id "
                "WHERE t.topic_id=?", (topic_id,)
            ).fetchone()
            if row_map:
                return dict(row_map)
        except sqlite3.OperationalError:
            pass

        # Fallback: look up via episodes
        row = conn.execute(
            "SELECT s.* FROM series s "
            "INNER JOIN episodes e ON e.series_id=s.id "
            "WHERE e.topic_id=? LIMIT 1", (topic_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


async def handle_file_message(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    chat_id = msg.chat_id if msg.chat_id else (
        msg.chat.id if msg.chat else None)
    if chat_id != PRIVATE_GROUP_ID:
        return

    caption = msg.caption or ""
    if not caption.strip():
        return

    file_obj = msg.video or msg.document
    if not file_obj:
        return

    file_id = file_obj.file_id
    file_size = getattr(file_obj, "file_size", None) or 0
    duration = getattr(file_obj, "duration", None) or 0
    message_id = msg.message_id
    topic_id = getattr(msg, "message_thread_id", None) or 0

    if MOVIE_CAP_RE.search(caption):
        movie = _find_movie_by_topic(topic_id)
        if movie:
            db.update_movie_file(
                movie["id"],
                file_id,
                file_size,
                duration,
                message_id)
            push_db_to_hf()
            cache_clear_all()
            logger.info(
                f"✅ Movie file saved: {movie['title']} — file_id={file_id[:20]}...")
        else:
            logger.warning(f"No movie found for topic_id={topic_id}")
        return

    ep_match = EPISODE_CAP_RE.search(caption)
    if ep_match:
        season_num = int(ep_match.group(1))
        episode_num = int(ep_match.group(2))

        series = _find_series_by_topic(topic_id)
        if not series:
            logger.warning(f"No series found for topic_id={topic_id}")
            return

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
                "file_id": file_id,
                "file_unique_id": getattr(file_obj, "file_unique_id", None),
                "file_size": file_size,
                "duration": duration,
                "topic_id": topic_id,
                "message_id": message_id,
            })
        else:
            db.update_episode_file(
                series["id"],
                season_num,
                episode_num,
                file_id,
                file_size,
                duration,
                message_id,
                topic_id)
        push_db_to_hf()
        cache_clear_all()
        logger.info(
            f"✅ Episode saved: {series['title']} S{season_num:02d}E{episode_num:02d}"
        )
        return

    logger.debug(
        f"Message in topic {topic_id} has no recognised caption pattern: {caption[:80]}")


async def cmd_fullscan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: scan ALL topics and messages to sync missing content."""
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.effective_message
    await msg.reply_text("🔍 بدء المسح الكامل للمجموعة... قد يستغرق بضع دقائق.")
    try:
        from app.stream import _pyro_clients
        from app.scanner import run_full_scan
        if not _pyro_clients:
            await msg.reply_text("❌ لا يوجد عميل Pyrogram متاح. تأكد من تشغيل الخدمة.")
            return
        results = await run_full_scan(_pyro_clients[0])
        s = db.get_stats()
        await msg.reply_text(
            "✅ اكتمل المسح!\n"
            f"📋 مواضيع مفحوصة: {results['topics_scanned']}\n"
            f"➕ محتوى جديد مسجّل: {results['registered']}\n"
            f"🎬 ملفات مرفقة: {results['files_attached']}\n"
            f"⚠️ أخطاء: {results['errors']}\n\n"
            "📊 المكتبة الآن:\n"
            f"• {s['movies_count']} فيلم | {s['series_count']} مسلسل | {s['episodes_count']} حلقة"
        )
    except Exception as e:
        logger.error(f"fullscan error: {e}", exc_info=True)
        await msg.reply_text(f"❌ خطأ أثناء المسح: {e}")


def build_sync_app() -> Application:
    app = Application.builder().token(MAIN_BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(
            filters.Chat(
                chat_id=PRIVATE_GROUP_ID) & (
                filters.VIDEO | filters.Document.VIDEO),
            handle_file_message,
        ))
    app.add_handler(CommandHandler("fullscan", cmd_fullscan))
    return app
