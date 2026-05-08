"""
Full scanner — scans ALL messages in the private group to register
missing movies/series and attach missing file_ids.

Uses raw Pyrogram MTProto API because bot accounts cannot call
messages.GetHistory — but they CAN call channels.GetMessages.

Forum topics are retrieved via raw GetForumTopics. If the group is
not a Forum, we fall back to inferring topic_id from reply_to_top_id.
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
    if parsed["type"] == "movie":
        if db.get_movie(movie_id=parsed["internal_id"]): return False
        tmdb = await fetch_movie(parsed["tmdb_id"])
        if not tmdb: return False
        db.upsert_movie({
            "id": parsed["internal_id"], "topic_id": topic_id,
            "message_id": None, "file_id": None, "file_size": None, "duration": None,
            **tmdb,
        })
        logger.info("[scanner] Registered movie: %s", tmdb['title'])
        return True
    elif parsed["type"] == "series":
        already = db.get_series(series_id=parsed["internal_id"])
        set_topic_series_map(topic_id, parsed["internal_id"])
        if already: return False
        tmdb = await fetch_series(parsed["tmdb_id"])
        if not tmdb: return False
        db.upsert_series({"id": parsed["internal_id"], **tmdb})
        logger.info("[scanner] Registered series: %s", tmdb['title'])
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
    caption = message.caption or getattr(message, "text", "") or ""
    if not caption.strip(): return False
    file_obj = getattr(message, "video", None) or getattr(message, "document", None)
    if not file_obj: return False

    file_id   = file_obj.file_id
    file_size = getattr(file_obj, "file_size",  None) or 0
    duration  = getattr(file_obj, "duration",   None) or 0
    msg_id    = getattr(message, "id", 0)

    if MOVIE_CAP_RE.search(caption):
        movie = _movie_by_topic(topic_id)
        if movie and not movie.get("file_id"):
            db.update_movie_file(movie["id"], file_id, file_size, duration, msg_id)
            logger.info("[scanner] Movie file attached: %s", movie['title'])
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
        logger.info("[scanner] Episode: %s S%02dE%02d", series['title'], s_num, e_num)
        return True
    return False


async def _get_input_channel(pyro_client):
    """
    Get InputChannel for PRIVATE_GROUP_ID.
    Uses GetChannels(access_hash=0) which Telegram allows for bots that are members.
    """
    try:
        from pyrogram.raw.functions.channels import GetChannels  # type: ignore
        from pyrogram.raw.types import InputChannel              # type: ignore
    except ImportError:
        return None, None

    raw_id = abs(PRIVATE_GROUP_ID)
    s = str(raw_id)
    if s.startswith("100"):
        raw_id = int(s[3:])

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

    # Fallback: resolve peer via Pyrogram's internal cache
    try:
        peer = await asyncio.wait_for(pyro_client.resolve_peer(PRIVATE_GROUP_ID), timeout=10)
        ch_id  = getattr(peer, "channel_id", raw_id)
        a_hash = getattr(peer, "access_hash", 0)
        logger.info("[scanner] Got peer via resolve_peer: channel_id=%d", ch_id)
        return ch_id, a_hash
    except Exception as e:
        logger.error("[scanner] Could not resolve private group peer: %s", e)
        return None, None


async def _get_forum_topics_raw(pyro_client) -> list:
    """
    Fetch forum topics via raw MTProto GetForumTopics.
    Returns [] if the group is not a Forum or has no topics.
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
        logger.info("[scanner] GetForumTopics batch: %d topics, result_type=%s count=%s",
                    len(topics), type(result).__name__, getattr(result, "count", "?"))
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


async def _get_messages_batch(pyro_client, channel_id: int, access_hash: int,
                              ids: list[int]) -> list:
    """
    Fetch a batch of messages using channels.GetMessages (works for bots).
    Returns raw message objects.
    """
    try:
        from pyrogram.raw.functions.channels import GetMessages as GetChanMsgs  # type: ignore
        from pyrogram.raw.types import InputChannel, InputMessageID             # type: ignore
    except ImportError:
        return []

    try:
        result = await asyncio.wait_for(
            pyro_client.invoke(
                GetChanMsgs(
                    channel=InputChannel(channel_id=channel_id, access_hash=access_hash),
                    id=[InputMessageID(id=i) for i in ids],
                )
            ),
            timeout=30,
        )
        return getattr(result, "messages", [])
    except Exception as e:
        logger.warning("[scanner] GetMessages batch failed: %s", e)
        return []


def _extract_file_from_raw_msg(raw_msg) -> tuple | None:
    """Extract (file_id, file_size, duration) from a raw Pyrogram MTProto message."""
    from pyrogram.raw.types import Message, MessageMediaDocument, MessageMediaVideo  # type: ignore
    if not isinstance(raw_msg, Message):
        return None
    media = getattr(raw_msg, "media", None)
    if media is None:
        return None

    doc = None
    if hasattr(media, "document"):
        doc = media.document
    elif hasattr(media, "video"):
        doc = media.video

    if doc is None:
        return None

    file_id   = getattr(doc, "id",        None)
    file_size = getattr(doc, "size",      0)
    duration  = 0
    for attr in getattr(doc, "attributes", []):
        dur = getattr(attr, "duration", None)
        if dur:
            duration = int(dur)
            break

    if file_id is None:
        return None

    return file_id, file_size, duration


async def _iter_channel_messages(pyro_client, channel_id: int, access_hash: int,
                                 batch_size: int = 100, max_id: int = 10000):
    """
    Iterate all messages in a channel using channels.GetMessages in batches.
    Yields raw message objects that have media.
    Bot accounts can use this unlike messages.GetHistory.
    """
    from pyrogram.raw.functions.channels import GetMessages as GetChanMsgs  # type: ignore
    from pyrogram.raw.types import InputChannel, InputMessageID             # type: ignore

    # First, find the actual max message ID by probing high IDs
    # Use a binary-search-like approach: try the last known message
    # For simplicity, start from max_id and work down in batches
    ids_batch = list(range(max_id, max(0, max_id - batch_size), -1))
    empty_batches = 0

    start = max_id
    while start > 0:
        end = max(0, start - batch_size)
        ids = list(range(start, end, -1))
        start = end

        msgs = await _get_messages_batch(pyro_client, channel_id, access_hash, ids)
        real_msgs = [m for m in msgs if getattr(m, "id", None) and
                     not getattr(m, "empty", False) and
                     type(m).__name__ not in ("MessageEmpty",)]
        if not real_msgs:
            empty_batches += 1
            if empty_batches >= 5 and start < max_id - 2000:
                # 5 consecutive empty batches below reasonable range → stop
                break
            continue
        empty_batches = 0
        for m in real_msgs:
            yield m


async def _get_channel_max_msg_id(pyro_client, channel_id: int, access_hash: int) -> int:
    """Get the highest message ID in the channel to bound our scan."""
    try:
        from pyrogram.raw.functions.messages import GetPeerDialogs  # type: ignore
        from pyrogram.raw.types import InputDialogPeer, InputPeerChannel  # type: ignore
        result = await asyncio.wait_for(
            pyro_client.invoke(
                GetPeerDialogs(peers=[
                    InputDialogPeer(peer=InputPeerChannel(channel_id=channel_id, access_hash=access_hash))
                ])
            ),
            timeout=15,
        )
        dialogs = getattr(result, "dialogs", [])
        if dialogs:
            top_msg = getattr(dialogs[0], "top_message", 0)
            if top_msg:
                logger.info("[scanner] Channel max msg_id=%d", top_msg)
                return top_msg
    except Exception as e:
        logger.warning("[scanner] GetPeerDialogs failed: %s", e)

    return 5000  # Fallback: scan first 5000 IDs


async def run_full_scan(pyro_client) -> dict:
    """
    1. Enumerate all forum topics → register missing movies/series.
    2. Iterate ALL messages via channels.GetMessages → attach missing file_ids.
       (channels.GetMessages works for bots; messages.GetHistory does not)
    """
    results = {"topics_scanned": 0, "registered": 0, "files_attached": 0, "errors": 0}
    changed = False

    # ── Resolve the group peer ───────────────────────────────────────────────
    channel_id, access_hash = await _get_input_channel(pyro_client)
    if not channel_id:
        logger.error("[scanner] Cannot resolve private group peer — aborting scan")
        results["errors"] += 1
        return results

    # ── Step 1: Get all forum topics (via raw MTProto) ───────────────────────
    topics = []
    try:
        topics = await _get_forum_topics_raw(pyro_client)
        results["topics_scanned"] = len(topics)
        logger.info("[scanner] %d topics found", len(topics))
    except Exception as e:
        logger.error("[scanner] get_forum_topics_raw: %s", e)
        results["errors"] += 1

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
            logger.error("[scanner] register %s: %s", topic.title, e)
            results["errors"] += 1

    # ── Step 2: Iterate messages via channels.GetMessages (bot-compatible) ───
    try:
        max_id = await _get_channel_max_msg_id(pyro_client, channel_id, access_hash)
        logger.info("[scanner] Scanning messages 1..%d via channels.GetMessages", max_id)

        batch_size = 100
        start_id = max_id
        empty_runs = 0

        while start_id > 0:
            end_id = max(1, start_id - batch_size + 1)
            ids = list(range(start_id, end_id - 1, -1))
            start_id = end_id - 1

            try:
                from pyrogram.raw.functions.channels import GetMessages as GetChanMsgs  # type: ignore
                from pyrogram.raw.types import InputChannel, InputMessageID             # type: ignore
                result = await asyncio.wait_for(
                    pyro_client.invoke(
                        GetChanMsgs(
                            channel=InputChannel(channel_id=channel_id, access_hash=access_hash),
                            id=[InputMessageID(id=i) for i in ids],
                        )
                    ),
                    timeout=30,
                )
            except Exception as e:
                logger.warning("[scanner] GetMessages batch (%d..%d) failed: %s",
                               ids[-1], ids[0], e)
                results["errors"] += 1
                await asyncio.sleep(1)
                continue

            raw_msgs = getattr(result, "messages", [])
            real_msgs = [m for m in raw_msgs
                         if type(m).__name__ != "MessageEmpty"
                         and getattr(m, "id", 0) > 0
                         and getattr(m, "media", None) is not None]

            if not real_msgs:
                empty_runs += 1
                if empty_runs >= 10 and start_id < (max_id - 3000):
                    logger.info("[scanner] 10 empty batches past id %d — stopping", start_id)
                    break
                continue
            empty_runs = 0

            for raw_msg in real_msgs:
                # Determine the thread/topic id (reply_to field)
                reply_to = getattr(raw_msg, "reply_to", None)
                tid = None
                if reply_to:
                    tid = (getattr(reply_to, "reply_to_top_id", None)
                           or getattr(reply_to, "reply_to_msg_id", None))

                # Build a minimal duck-type message object for _process_file_message
                caption = getattr(raw_msg, "message", "") or ""
                msg_id  = getattr(raw_msg, "id", 0)
                media   = getattr(raw_msg, "media", None)

                # Extract media attributes (raw MTProto types)
                file_obj = None
                media_type = type(media).__name__ if media else ""

                if "Document" in media_type:
                    doc = getattr(media, "document", None)
                    if doc:
                        file_obj = _build_file_proxy(doc)
                elif "Video" in media_type:
                    vid = getattr(media, "video", None)
                    if vid:
                        file_obj = _build_file_proxy(vid)

                if not file_obj or not caption.strip():
                    continue

                # Try registering if we can infer type from caption (fallback when topics=0)
                if not topic_map and tid:
                    parsed = _parse_topic(caption)
                    if parsed and tid not in topic_map:
                        topic_map[tid] = parsed
                        try:
                            added = await _ensure_registered(parsed, tid)
                            if added:
                                results["registered"] += 1
                                changed = True
                        except Exception as e:
                            logger.warning("[scanner] caption-register: %s", e)

                if tid and (MOVIE_CAP_RE.search(caption) or EPISODE_CAP_RE.search(caption)):
                    proxy = _MsgProxy(id=msg_id, caption=caption, video=file_obj if "Video" in media_type else None,
                                      document=file_obj if "Document" in media_type else None)
                    try:
                        saved = await _process_file_message(proxy, tid)
                        if saved:
                            results["files_attached"] += 1
                            changed = True
                    except Exception as me:
                        logger.warning("[scanner] msg process id=%d: %s", msg_id, me)

            await asyncio.sleep(0.05)  # Gentle rate-limit

    except Exception as e:
        logger.error("[scanner] channels.GetMessages scan failed: %s", e)
        results["errors"] += 1

    if changed:
        push_db_to_hf()
        cache_clear_all()
        logger.info("[scanner] Done: %s", results)

    return results


def _build_file_proxy(doc):
    """Build a duck-type file object from a raw MTProto document."""
    duration = 0
    for attr in getattr(doc, "attributes", []):
        d = getattr(attr, "duration", None)
        if d:
            duration = int(d)
            break
    return type("FileProxy", (), {
        "file_id":        str(getattr(doc, "id", "")),
        "file_unique_id": str(getattr(doc, "access_hash", "")),
        "file_size":      getattr(doc, "size", 0),
        "duration":       duration,
    })()


class _MsgProxy:
    """Minimal duck-type Pyrogram Message for _process_file_message."""
    def __init__(self, id, caption, video=None, document=None):
        self.id = id
        self.caption = caption
        self.text = caption
        self.video = video
        self.document = document
