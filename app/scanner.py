"""
Full scanner — scans ALL forum topics and messages in the private group
to register missing movies/series and attach missing file_ids.
Called by the /fullscan admin command.
"""
import re, logging, sqlite3
from app.config import PRIVATE_GROUP_ID, DB_PATH
from app import database as db
from app.database import push_db_to_hf
from app.tmdb import fetch_movie, fetch_series, fetch_episode_info
from app.cache import cache_clear_all

logger = logging.getLogger(__name__)

MOVIE_TOPIC_RE  = re.compile(r'#([\w&]+)\s+#movies\s+#(mid\d+)\s+#(\d+)', re.IGNORECASE)
SERIES_TOPIC_RE = re.compile(r'#([\w&]+)\s+#series\s+(?:#s\d+\s+)?#(sid\d+)\s+#(\d+)', re.IGNORECASE)
EPISODE_CAP_RE  = re.compile(r'#[\w&]+\s+#[Ss](\d+)\s+#[Ee](\d+)', re.IGNORECASE)
MOVIE_CAP_RE    = re.compile(r'#[\w&]+\s+#Movie\b', re.IGNORECASE)
GENERAL_RE      = re.compile(r'general', re.IGNORECASE)


def _parse_topic(name: str) -> dict | None:
    if GENERAL_RE.search(name):
        return None
    m = MOVIE_TOPIC_RE.search(name)
    if m:
        return {"type": "movie", "slug": m.group(1), "internal_id": m.group(2), "tmdb_id": int(m.group(3))}
    m = SERIES_TOPIC_RE.search(name)
    if m:
        return {"type": "series", "slug": m.group(1), "internal_id": m.group(2), "tmdb_id": int(m.group(3))}
    return None


async def _ensure_registered(parsed: dict, topic_id: int) -> bool:
    """Register movie/series if not in DB. Returns True if a new entry was created."""
    if parsed["type"] == "movie":
        if db.get_movie(movie_id=parsed["internal_id"]):
            return False
        tmdb = await fetch_movie(parsed["tmdb_id"])
        if not tmdb:
            return False
        db.upsert_movie({
            "id": parsed["internal_id"], "topic_id": topic_id,
            "message_id": None, "file_id": None, "file_size": None, "duration": None,
            **tmdb,
        })
        logger.info(f"[scanner] Registered movie: {tmdb['title']}")
        return True

    elif parsed["type"] == "series":
        if db.get_series(series_id=parsed["internal_id"]):
            return False
        tmdb = await fetch_series(parsed["tmdb_id"])
        if not tmdb:
            return False
        db.upsert_series({"id": parsed["internal_id"], **tmdb})
        logger.info(f"[scanner] Registered series: {tmdb['title']}")
        return True

    return False


def _movie_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM movies WHERE topic_id=?", (topic_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _series_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT s.* FROM series s "
            "INNER JOIN episodes e ON e.series_id=s.id "
            "WHERE e.topic_id=? LIMIT 1", (topic_id,)
        ).fetchone()
        if row:
            return dict(row)
        try:
            row2 = conn.execute(
                "SELECT s.* FROM series s "
                "INNER JOIN topic_series_map t ON t.series_id=s.id "
                "WHERE t.topic_id=?", (topic_id,)
            ).fetchone()
            return dict(row2) if row2 else None
        except sqlite3.OperationalError:
            return None
    finally:
        conn.close()


async def _process_file_message(message, topic_id: int) -> bool:
    """Process a single Pyrogram message and attach file to movie/episode. Returns True if saved."""
    caption = message.caption or ""
    if not caption.strip():
        return False

    file_obj = message.video or message.document
    if not file_obj:
        return False

    file_id   = file_obj.file_id
    file_size = getattr(file_obj, "file_size",  None) or 0
    duration  = getattr(file_obj, "duration",   None) or 0
    msg_id    = message.id

    if MOVIE_CAP_RE.search(caption):
        movie = _movie_by_topic(topic_id)
        if movie and not movie.get("file_id"):
            db.update_movie_file(movie["id"], file_id, file_size, duration, msg_id)
            logger.info(f"[scanner] Movie file attached: {movie['title']}")
            return True
        return False

    ep_m = EPISODE_CAP_RE.search(caption)
    if ep_m:
        s_num, e_num = int(ep_m.group(1)), int(ep_m.group(2))
        series = _series_by_topic(topic_id)
        if not series:
            return False
        existing = db.get_episode(series["id"], s_num, e_num)
        if not existing:
            ep_meta = await fetch_episode_info(series.get("tmdb_id"), s_num, e_num)
            db.upsert_episode({
                "series_id": series["id"], "season_number": s_num, "episode_number": e_num,
                "title": ep_meta.get("title", f"الحلقة {e_num}") if ep_meta else f"الحلقة {e_num}",
                "overview": ep_meta.get("overview", "") if ep_meta else "",
                "still_path": ep_meta.get("still_path", "") if ep_meta else "",
                "air_date": ep_meta.get("air_date", "") if ep_meta else "",
                "runtime": ep_meta.get("runtime", 0) if ep_meta else 0,
                "topic_id": topic_id,
            })
        else:
            if existing.get("file_id"):
                return False  # already has file
        db.update_episode_file(series["id"], s_num, e_num, file_id, file_size, duration, msg_id, topic_id)
        logger.info(f"[scanner] Episode file: {series['title']} S{s_num:02d}E{e_num:02d}")
        return True

    return False


async def run_full_scan(pyro_client) -> dict:
    """
    Main entry: iterate all forum topics, register missing content,
    then scan last 200 messages per topic for missing files.
    """
    results = {"topics_scanned": 0, "registered": 0, "files_attached": 0, "errors": 0}
    changed = False

    # Step 1: Get all forum topics via Pyrogram
    try:
        topics = []
        async for topic in pyro_client.get_forum_topics(PRIVATE_GROUP_ID):
            topics.append(topic)
        results["topics_scanned"] = len(topics)
        logger.info(f"[scanner] Found {len(topics)} topics")
    except Exception as e:
        logger.error(f"[scanner] get_forum_topics error: {e}")
        results["errors"] += 1
        return results

    for topic in topics:
        topic_id   = topic.id
        topic_name = topic.title or ""

        parsed = _parse_topic(topic_name)
        if not parsed:
            continue

        # Step 2: Register if missing
        try:
            added = await _ensure_registered(parsed, topic_id)
            if added:
                results["registered"] += 1
                changed = True
        except Exception as e:
            logger.error(f"[scanner] register error for {topic_name}: {e}")
            results["errors"] += 1

        # Step 3: Scan messages for files
        try:
            async for message in pyro_client.get_chat_history(
                PRIVATE_GROUP_ID, limit=200, reply_to_message_id=topic_id
            ):
                try:
                    saved = await _process_file_message(message, topic_id)
                    if saved:
                        results["files_attached"] += 1
                        changed = True
                except Exception as me:
                    logger.warning(f"[scanner] message process error: {me}")
        except Exception as e:
            logger.error(f"[scanner] scan messages error for topic {topic_id}: {e}")
            results["errors"] += 1

    if changed:
        push_db_to_hf()
        cache_clear_all()
        logger.info(f"[scanner] Scan complete: {results}")

    return results
