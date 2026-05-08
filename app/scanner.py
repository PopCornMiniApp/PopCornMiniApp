"""
Full scanner — scans ALL forum topics and messages in the private group
to register missing movies/series and attach missing file_ids.

Uses raw Pyrogram MTProto API for forum topics (get_forum_topics not available
in Pyrogram 2.0.106).
"""
import re
import logging
import sqlite3
import asyncio

from app.config import PRIVATE_GROUP_ID, DB_PATH
from app import database as db
from app.database import push_db_to_hf, set_topic_series_map
from app.tmdb import fetch_movie, fetch_series, fetch_episode_info
from app.cache import cache_clear_all

logger = logging.getLogger(__name__)

MOVIE_TOPIC_RE  = re.compile(r'#([\w&]+)\s+#movies\s+#(mid\d+)\s+#(\d+)', re.IGNORECASE)
SERIES_TOPIC_RE = re.compile(r'#([\w&]+)\s+#series\s+(?:#s\d+\s+)?#(sid\d+)\s+#(\d+)', re.IGNORECASE)
EPISODE_CAP_RE  = re.compile(r'#[\w&]+\s+#[Ss](\d+)\s+#[Ee](\d+)', re.IGNORECASE)
MOVIE_CAP_RE    = re.compile(r'#[\w&]+\s+#Movie\b', re.IGNORECASE)
GENERAL_RE      = re.compile(r'general', re.IGNORECASE)


def _parse_topic(name: str) -> dict | None:
    if GENERAL_RE.search(name): return None
    m = MOVIE_TOPIC_RE.search(name)
    if m: return {"type": "movie", "slug": m.group(1), "internal_id": m.group(2), "tmdb_id": int(m.group(3))}
    m = SERIES_TOPIC_RE.search(name)
    if m: return {"type": "series", "slug": m.group(1), "internal_id": m.group(2), "tmdb_id": int(m.group(3))}
    return None


async def _ensure_registered(parsed: dict, topic_id: int) -> bool:
    """Register a movie/series if not already in DB. Returns True if newly added."""
    if parsed["type"] == "movie":
        if db.get_movie(movie_id=parsed["internal_id"]): return False
        tmdb = await fetch_movie(parsed["tmdb_id"])
        if not tmdb: return False
        db.upsert_movie({
            "id": parsed["internal_id"], "topic_id": topic_id,
            "message_id": None, "file_id": None, "file_size": None, "duration": None,
            **tmdb,
        })
        logger.info(f"[scanner] Registered movie: {tmdb['title']}")
        return True
    elif parsed["type"] == "series":
        already = db.get_series(series_id=parsed["internal_id"])
        set_topic_series_map(topic_id, parsed["internal_id"])
        if already: return False
        tmdb = await fetch_series(parsed["tmdb_id"])
        if not tmdb: return False
        db.upsert_series({"id": parsed["internal_id"], **tmdb})
        logger.info(f"[scanner] Registered series: {tmdb['title']}")
        return True
    return False


def _movie_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM movies WHERE topic_id=?", (topic_id,)).fetchone()
        return dict(row) if row else None
    finally: conn.close()


def _series_by_topic(topic_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    try:
        try:
            row = conn.execute(
                "SELECT s.* FROM series s "
                "INNER JOIN topic_series_map t ON t.series_id=s.id "
                "WHERE t.topic_id=?", (topic_id,)
            ).fetchone()
            if row: return dict(row)
        except sqlite3.OperationalError:
            pass
        row = conn.execute(
            "SELECT s.* FROM series s "
            "INNER JOIN episodes e ON e.series_id=s.id "
            "WHERE e.topic_id=? LIMIT 1", (topic_id,)
        ).fetchone()
        return dict(row) if row else None
    finally: conn.close()


async def _process_file_message(message, topic_id: int) -> bool:
    caption = message.caption or ""
    if not caption.strip(): return False
    file_obj = message.video or message.document
    if not file_obj: return False

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
        if not series: return False
        existing = db.get_episode(series["id"], s_num, e_num)
        if not existing:
            ep_meta = await fetch_episode_info(series.get("tmdb_id"), s_num, e_num)
            db.upsert_episode({
                "series_id": series["id"],
                "season_number": s_num,
                "episode_number": e_num,
                "title": ep_meta.get("title", f"الحلقة {e_num}") if ep_meta else f"الحلقة {e_num}",
                "overview": ep_meta.get("overview", "") if ep_meta else "",
                "still_path": ep_meta.get("still_path", "") if ep_meta else "",
                "air_date": ep_meta.get("air_date", "") if ep_meta else "",
                "runtime": ep_meta.get("runtime", 0) if ep_meta else 0,
                "file_id": file_id,
                "file_unique_id": getattr(file_obj, "file_unique_id", None),
                "file_size": file_size,
                "duration": duration,
                "topic_id": topic_id,
                "message_id": msg_id,
            })
        elif existing.get("file_id"):
            return False
        else:
            db.update_episode_file(series["id"], s_num, e_num, file_id, file_size, duration, msg_id, topic_id)
        logger.info(f"[scanner] Episode: {series['title']} S{s_num:02d}E{e_num:02d}")
        return True
    return False


async def _get_input_channel(pyro_client):
    """
    Get InputChannel for PRIVATE_GROUP_ID.
    Uses GetChannels(access_hash=0) which Telegram allows for bots that are members.
    Falls back to get_chat() to extract the peer data.
    """
    try:
        from pyrogram.raw.functions.channels import GetChannels  # type: ignore
        from pyrogram.raw.types import InputChannel              # type: ignore
    except ImportError:
        return None, None

    # Strip -100 prefix
    raw_id = abs(PRIVATE_GROUP_ID)
    s = str(raw_id)
    if s.startswith("100"):
        raw_id = int(s[3:])

    # Try GetChannels with access_hash=0 first
    try:
        result = await asyncio.wait_for(
            pyro_client.invoke(GetChannels(id=[InputChannel(channel_id=raw_id, access_hash=0)])),
            timeout=15,
        )
        chats = getattr(result, "chats", [])
        if chats:
            ch = chats[0]
            access_hash = getattr(ch, "access_hash", 0)
            logger.info("[scanner] Got access_hash via GetChannels for channel_id=%d", raw_id)
            return raw_id, access_hash
    except Exception as e:
        logger.warning("[scanner] GetChannels(hash=0) failed: %s", e)

    # Fallback: use get_chat, then resolve_peer to get the InputPeer
    try:
        await asyncio.wait_for(pyro_client.get_chat(PRIVATE_GROUP_ID), timeout=15)
        peer = await asyncio.wait_for(pyro_client.resolve_peer(PRIVATE_GROUP_ID), timeout=10)
        ch_id   = getattr(peer, "channel_id", raw_id)
        a_hash  = getattr(peer, "access_hash", 0)
        logger.info("[scanner] Got peer via get_chat+resolve_peer: channel_id=%d", ch_id)
        return ch_id, a_hash
    except Exception as e:
        logger.error("[scanner] Could not resolve private group peer: %s", e)
        return None, None


async def _get_forum_topics_raw(pyro_client) -> list:
    """
    Fetch all forum topics via raw Pyrogram MTProto.
    Works with Pyrogram 2.0.106 which lacks the get_forum_topics() helper.
    """
    try:
        from pyrogram.raw.functions.channels import GetForumTopics  # type: ignore
        from pyrogram.raw.types import InputChannel                  # type: ignore
    except ImportError:
        logger.error("[scanner] Pyrogram raw API not available")
        return []

    channel_id, access_hash = await _get_input_channel(pyro_client)
    if not channel_id:
        logger.error("[scanner] Cannot get InputChannel for private group")
        return []

    all_topics: list = []
    offset_date  = 0
    offset_id    = 0
    offset_topic = 0
    limit        = 100

    while True:
        try:
            result = await asyncio.wait_for(
                pyro_client.invoke(
                    GetForumTopics(
                        channel=InputChannel(channel_id=channel_id, access_hash=access_hash),
                        q="",
                        offset_date=offset_date,
                        offset_id=offset_id,
                        offset_topic=offset_topic,
                        limit=limit,
                    )
                ),
                timeout=30,
            )
        except Exception as e:
            logger.error("[scanner] GetForumTopics invoke failed: %s", e)
            break

        topics = getattr(result, "topics", [])
        if not topics:
            break

        for t in topics:
            all_topics.append(type("Topic", (), {
                "id":    getattr(t, "id", 0),
                "title": getattr(t, "title", ""),
            })())

        if len(topics) < limit:
            break

        last = topics[-1]
        offset_topic = getattr(last, "id", 0)
        msgs = getattr(result, "messages", [])
        if msgs:
            last_msg = msgs[-1]
            offset_date = getattr(last_msg, "date", 0)
            offset_id   = getattr(last_msg, "id",   0)

    logger.info("[scanner] GetForumTopics raw: %d topics fetched", len(all_topics))
    return all_topics


async def run_full_scan(pyro_client) -> dict:
    """
    1. Enumerate all forum topics → register missing movies/series.
    2. Iterate ALL recent messages in the group → attach missing file_ids.
    """
    results = {"topics_scanned": 0, "registered": 0, "files_attached": 0, "errors": 0}
    changed = False

    # ── Step 1: Get all forum topics (via raw MTProto) ───────────────────────
    topics = []
    try:
        topics = await _get_forum_topics_raw(pyro_client)
        results["topics_scanned"] = len(topics)
        logger.info(f"[scanner] {len(topics)} topics found")
    except Exception as e:
        logger.error(f"[scanner] get_forum_topics_raw: {e}")
        results["errors"] += 1

    # Build map: topic_id → parsed info
    topic_map: dict[int, dict] = {}
    for topic in topics:
        parsed = _parse_topic(topic.title or "")
        if not parsed: continue
        topic_map[topic.id] = parsed
        try:
            added = await _ensure_registered(parsed, topic.id)
            if added:
                results["registered"] += 1
                changed = True
        except Exception as e:
            logger.error(f"[scanner] register {topic.title}: {e}")
            results["errors"] += 1

    # ── Step 2: Iterate recent messages, attach missing files ─────────────────
    try:
        async for message in pyro_client.get_chat_history(PRIVATE_GROUP_ID, limit=3000):
            tid = (
                getattr(message, "message_thread_id", None)
                or getattr(message, "reply_to_top_id", None)
            )
            if not tid: continue
            if not (message.video or message.document): continue
            if not (message.caption or ""): continue
            try:
                saved = await _process_file_message(message, tid)
                if saved:
                    results["files_attached"] += 1
                    changed = True
            except Exception as me:
                logger.warning(f"[scanner] msg process: {me}")
    except Exception as e:
        logger.error(f"[scanner] get_chat_history: {e}")
        results["errors"] += 1

    if changed:
        push_db_to_hf()
        cache_clear_all()
        logger.info(f"[scanner] Done: {results}")

    return results
