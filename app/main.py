import asyncio, logging, os, json, time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app import database as db
from app.database import init_db, push_db_to_hf
from app.stream import stream_file, get_stream_info, init_pyrogram, stop_pyrogram
from app.config import MAIN_BOT_TOKEN, ADMIN_ID
from app.smart_cache import cache_get, cache_set, cache_clear_prefix, cache_clear_all, cache_get_stats
from app.security import require_admin, rate_limit, validate_request_security, security_logger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
_bot_task = _sync_task = _autoscan_task = _smart_sync_task = None


# ── Backward-compat shims ────────────────────────────────────────────────────
def _cache_get(key: str): return cache_get(key)
def _cache_set(key: str, value, ttl: int): return cache_set(key, value, ttl)
def _cache_clear_prefix(prefix: str): return cache_clear_prefix(prefix)
# ─────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_task, _sync_task, _autoscan_task, _smart_sync_task
    logger.info("🍿 PopCorn v4.2 starting…")
    init_db()
    await init_pyrogram()

    if MAIN_BOT_TOKEN:
        try:
            from app.sync_bot import build_sync_app
            from app.bot_commands import (
                cmd_start, cmd_app, cmd_help, cmd_new, cmd_top, cmd_stats, cmd_admin,
                get_callback_handlers,
            )
            from app.register_topic_handler import handle_new_topic, handle_edited_topic
            from telegram.ext import CommandHandler, MessageHandler, filters

            bot_app = build_sync_app()
            bot_app.add_handler(CommandHandler("start",    cmd_start))
            bot_app.add_handler(CommandHandler("app",      cmd_app))
            bot_app.add_handler(CommandHandler("help",     cmd_help))
            bot_app.add_handler(CommandHandler("new",      cmd_new))
            bot_app.add_handler(CommandHandler("top",      cmd_top))
            bot_app.add_handler(CommandHandler("stats",    cmd_stats))
            bot_app.add_handler(CommandHandler("admin",    cmd_admin))
            bot_app.add_handler(CommandHandler("sync_db",  _cmd_sync_db))
            bot_app.add_handler(CommandHandler("fullscan", _cmd_fullscan))

            # Forum topic event handlers (new/renamed topics → auto-register)
            bot_app.add_handler(
                MessageHandler(filters.StatusUpdate.FORUM_TOPIC_CREATED, handle_new_topic)
            )
            bot_app.add_handler(
                MessageHandler(filters.StatusUpdate.FORUM_TOPIC_EDITED, handle_edited_topic)
            )

            for _h in get_callback_handlers():
                bot_app.add_handler(_h)

            _bot_task = asyncio.create_task(_run_bot(bot_app))
            logger.info("✅ Telegram bot started")
        except Exception as e:
            logger.error(f"Bot start error: {e}", exc_info=True)

    _sync_task       = asyncio.create_task(_periodic_db_push())
    _smart_sync_task = asyncio.create_task(_periodic_smart_sync())
    _autoscan_task   = asyncio.create_task(_periodic_autoscan())
    
    # Run catch-up sync on startup
    asyncio.create_task(_startup_catch_up())
    
    yield

    if _bot_task:         _bot_task.cancel()
    if _sync_task:        _sync_task.cancel()
    if _smart_sync_task:  _smart_sync_task.cancel()
    if _autoscan_task:    _autoscan_task.cancel()
    await stop_pyrogram()


async def _cmd_sync_db(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    push_db_to_hf()
    cache_clear_all()
    await update.effective_message.reply_text("✅ تمت المزامنة مع HuggingFace وتم تحديث الكاش!")


async def _cmd_fullscan(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    from app.stream import _pyro_clients
    from app.scanner import run_full_scan
    if not _pyro_clients:
        await update.effective_message.reply_text("❌ لا يوجد عميل Pyrogram متاح.")
        return
    msg = await update.effective_message.reply_text("🔍 جارٍ مسح المجموعة الخاصة... قد يستغرق دقائق.")
    try:
        results = await run_full_scan(_pyro_clients[0])
        s = db.get_stats()
        await msg.edit_text(
            f"✅ اكتمل المسح!\n\n"
            f"📋 مواضيع: {results['topics_scanned']} | ➕ جديد: {results['registered']} | "
            f"🎬 ملفات: {results['files_attached']} | ⚠️ أخطاء: {results['errors']}\n\n"
            f"📊 المكتبة: {s['movies_count']} فيلم | {s['series_count']} مسلسل | {s['episodes_count']} حلقة"
        )
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {str(e)[:300]}")


async def _run_bot(bot_app):
    """Run the bot with polling — deletes any stale webhook first."""
    try:
        await bot_app.initialize()
        # Delete webhook to avoid conflict with polling
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted — starting polling")
        await bot_app.start()
        await bot_app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "edited_message", "callback_query",
                             "channel_post", "edited_channel_post"],
        )
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        try:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
        except Exception:
            pass


async def _periodic_db_push():
    """Every 10 minutes: push DB to HF and clear cache."""
    while True:
        await asyncio.sleep(600)
        try:
            push_db_to_hf()
            cache_clear_all()
            logger.info("Periodic DB push complete — cache cleared")
        except Exception as e:
            logger.error(f"Periodic DB push error: {e}")


async def _startup_catch_up():
    """Run catch-up sync on startup to get any missed messages."""
    await asyncio.sleep(30)  # Wait 30 seconds for Pyrogram to be ready
    try:
        from app.stream import _pyro_clients
        from app.smart_sync import run_catch_up_sync
        if _pyro_clients:
            logger.info("🔄 Running startup catch-up sync...")
            results = await run_catch_up_sync(_pyro_clients[0])
            logger.info(
                f"✅ Catch-up complete: scanned={results['messages_scanned']} "
                f"registered={results['registered']} files={results['files_attached']}"
            )
        else:
            logger.warning("Catch-up skipped: no Pyrogram clients available")
    except Exception as e:
        logger.error(f"Catch-up sync error: {e}", exc_info=True)


async def _periodic_smart_sync():
    """Every 5 minutes: smart sync to catch new content quickly."""
    await asyncio.sleep(60)  # Wait 1 minute after startup
    while True:
        try:
            from app.stream import _pyro_clients
            from app.smart_sync import run_smart_sync
            if _pyro_clients:
                logger.info("🔄 Smart sync: checking for new content...")
                results = await run_smart_sync(_pyro_clients[0])
                if results['registered'] > 0 or results['files_attached'] > 0:
                    logger.info(
                        f"✅ Smart sync found updates: registered={results['registered']} "
                        f"files={results['files_attached']}"
                    )
                else:
                    logger.debug("Smart sync: no new content")
            else:
                logger.warning("Smart sync skipped: no Pyrogram clients available")
        except Exception as e:
            logger.error(f"Smart sync error: {e}", exc_info=True)
        await asyncio.sleep(300)  # 5 minutes


async def _periodic_autoscan():
    """Every 1 hour: run a full scan to ensure nothing was missed."""
    await asyncio.sleep(180)  # Wait 3 minutes after startup before first scan
    while True:
        try:
            from app.stream import _pyro_clients
            from app.scanner import run_full_scan
            if _pyro_clients:
                logger.info("🔍 Full scan: starting comprehensive group scan...")
                results = await run_full_scan(_pyro_clients[0])
                logger.info(
                    f"✅ Full scan complete: topics={results['topics_scanned']} "
                    f"new={results['registered']} files={results['files_attached']} "
                    f"errors={results['errors']}"
                )
            else:
                logger.warning("Full scan skipped: no Pyrogram clients available")
        except Exception as e:
            logger.error(f"Full scan error: {e}", exc_info=True)
        await asyncio.sleep(3600)  # 1 hour (changed from 2 hours)


app = FastAPI(title="PopCorn API 🍿", version="4.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Security middleware - validate all requests
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Security validation middleware"""
    await validate_request_security(request)
    response = await call_next(request)
    return response


def _j(obj: dict, fields: list[str]):
    """Parse JSON string fields in-place."""
    for f in fields:
        v = obj.get(f)
        if isinstance(v, str):
            try:
                obj[f] = json.loads(v)
            except Exception:
                obj[f] = []
        elif v is None:
            obj[f] = []


@app.get("/api/health")
async def health():
    from app.stream import _pyro_clients
    return {"status": "ok", "service": "PopCorn API 🍿", "pyrogram": bool(_pyro_clients),
            "pyrogram_clients": len(_pyro_clients)}


@app.get("/api/stats")
async def stats():
    cached = cache_get("stats")
    if cached is not None:
        return cached
    result = db.get_stats()
    cache_set("stats", result, 30)
    return result


@app.get("/api/genres")
async def genres():
    cached = cache_get("genres")
    if cached is not None:
        return cached
    import sqlite3 as sq, json as js
    from app.config import DB_PATH
    conn = sq.connect(DB_PATH)
    try:
        raw = [r[0] for r in conn.execute(
            "SELECT genres FROM movies WHERE genres IS NOT NULL AND genres!='' "
            "UNION ALL SELECT genres FROM series WHERE genres IS NOT NULL AND genres!=''"
        ).fetchall()]
    finally:
        conn.close()
    all_genres: set = set()
    for row in raw:
        try:
            gs = js.loads(row) if isinstance(row, str) else row
            if isinstance(gs, list):
                all_genres.update(g for g in gs if g)
        except Exception:
            pass
    result = {"genres": sorted(all_genres)}
    cache_set("genres", result, 600)
    return result


@app.get("/api/featured")
async def featured():
    cached = cache_get("featured")
    if cached is not None:
        return cached
    import sqlite3 as sq
    from app.config import DB_PATH
    conn = sq.connect(DB_PATH); conn.row_factory = sq.Row
    try:
        movies = [dict(r) for r in conn.execute(
            "SELECT id,'movie' AS type,title,title_ar,poster_path,backdrop_path,rating,"
            "release_date AS date,overview,overview_ar,genres,1 AS has_file "
            "FROM movies WHERE backdrop_path!='' AND file_id IS NOT NULL ORDER BY rating DESC LIMIT 8"
        ).fetchall()]
        series = [dict(r) for r in conn.execute(
            "SELECT s.id,'series' AS type,s.title,s.title_ar,s.poster_path,s.backdrop_path,"
            "s.rating,s.first_air_date AS date,s.overview,s.overview_ar,s.genres,"
            "CASE WHEN EXISTS(SELECT 1 FROM episodes e WHERE e.series_id=s.id AND e.file_id IS NOT NULL) "
            "     THEN 1 ELSE 0 END AS has_file "
            "FROM series s WHERE s.backdrop_path!='' ORDER BY s.rating DESC LIMIT 4"
        ).fetchall()]
        items = (movies + series)[:12]
        for it in items:
            _j(it, ["genres"])
            it["has_file"] = bool(it.get("has_file"))
    finally:
        conn.close()
    result = {"items": items}
    cache_set("featured", result, 120)
    return result


@app.get("/api/movies")
async def list_movies(
    limit: int = Query(24, ge=1, le=100), offset: int = Query(0, ge=0),
    genre: str = Query(None), search: str = Query(None),
    has_file: bool = Query(None), sort: str = Query("newest"),
):
    cache_key = f"movies:{limit}:{offset}:{genre}:{search}:{has_file}:{sort}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    import sqlite3 as sq
    from app.config import DB_PATH
    conn = sq.connect(DB_PATH); conn.row_factory = sq.Row
    try:
        q = "SELECT * FROM movies WHERE 1=1"; p: list = []
        if genre: q += " AND genres LIKE ?"; p.append(f"%{genre}%")
        if search:
            term = f"%{search}%"
            q += " AND (title LIKE ? OR title_ar LIKE ? OR LOWER(title) LIKE LOWER(?) OR LOWER(title_ar) LIKE LOWER(?))"
            p += [term, term, term, term]
        if has_file is True: q += " AND file_id IS NOT NULL"
        elif has_file is False: q += " AND file_id IS NULL"
        order = {"newest": "created_at DESC", "rating": "rating DESC", "title": "title_ar ASC"}.get(sort, "created_at DESC")
        count_q = q.replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_q, p).fetchone()[0]
        q += f" ORDER BY {order} LIMIT ? OFFSET ?"; p += [limit, offset]
        rows = [dict(r) for r in conn.execute(q, p).fetchall()]
    finally:
        conn.close()
    for m in rows:
        _j(m, ["genres", "cast"])
        m["has_file"] = bool(m.get("file_id"))
    result = {"items": rows, "total": total, "limit": limit, "offset": offset}
    ttl = 20 if search else 30
    cache_set(cache_key, result, ttl)
    return result


@app.get("/api/movies/{movie_id}")
async def get_movie(movie_id: str):
    cache_key = f"movie:{movie_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    m = db.get_movie(movie_id=movie_id)
    if not m: raise HTTPException(404, "Movie not found")
    _j(m, ["genres", "cast"])
    if m.get("file_id"):
        m["stream_url"] = f"/api/stream/{m['file_id']}"
        m["has_file"] = True
        m["file_size"] = m.get("file_size") or 0
    else:
        m["has_file"] = False
        m["stream_url"] = None
    cache_set(cache_key, m, 60)
    return m


@app.get("/api/series")
async def list_series(
    limit: int = Query(24, ge=1, le=100), offset: int = Query(0, ge=0),
    genre: str = Query(None), search: str = Query(None), sort: str = Query("newest"),
):
    cache_key = f"series_list:{limit}:{offset}:{genre}:{search}:{sort}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    import sqlite3 as sq
    from app.config import DB_PATH
    conn = sq.connect(DB_PATH); conn.row_factory = sq.Row
    try:
        where = "1=1"; p: list = []
        if genre: where += " AND s.genres LIKE ?"; p.append(f"%{genre}%")
        if search:
            term = f"%{search}%"
            where += " AND (s.title LIKE ? OR s.title_ar LIKE ? OR LOWER(s.title) LIKE LOWER(?) OR LOWER(s.title_ar) LIKE LOWER(?))"
            p += [term, term, term, term]
        order = {"newest": "s.created_at DESC", "rating": "s.rating DESC", "title": "s.title_ar ASC"}.get(sort, "s.created_at DESC")
        count_q = f"SELECT COUNT(*) FROM series s WHERE {where}"
        total = conn.execute(count_q, p).fetchone()[0]
        q = (
            f"SELECT s.*, "
            f"CASE WHEN EXISTS(SELECT 1 FROM episodes e WHERE e.series_id=s.id AND e.file_id IS NOT NULL) "
            f"     THEN 1 ELSE 0 END AS has_file "
            f"FROM series s WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?"
        )
        p_full = p + [limit, offset]
        rows = [dict(r) for r in conn.execute(q, p_full).fetchall()]
    finally:
        conn.close()
    for s in rows:
        _j(s, ["genres", "cast"])
        s["has_file"] = bool(s.get("has_file"))
    result = {"items": rows, "total": total, "limit": limit, "offset": offset}
    ttl = 20 if search else 30
    cache_set(cache_key, result, ttl)
    return result


@app.get("/api/series/{series_id}")
async def get_series(series_id: str):
    cache_key = f"series:{series_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    s = db.get_series(series_id=series_id)
    if not s: raise HTTPException(404, "Series not found")
    _j(s, ["genres", "cast"])
    episodes = db.get_episodes(series_id)
    seasons: dict[int, list] = {}
    for ep in episodes:
        ep["stream_url"] = f"/api/stream/{ep['file_id']}" if ep.get("file_id") else None
        ep["has_file"] = bool(ep.get("file_id"))
        seasons.setdefault(ep["season_number"], []).append(ep)
    s["seasons"] = {str(k): v for k, v in sorted(seasons.items())}
    s["total_seasons_available"] = len(seasons)
    s["has_file"] = any(ep.get("has_file") for eps in seasons.values() for ep in eps)
    cache_set(cache_key, s, 60)
    return s


@app.get("/api/series/{series_id}/episodes")
async def series_episodes(series_id: str, season: int = Query(None)):
    eps = db.get_episodes(series_id, season_number=season)
    for ep in eps:
        ep["stream_url"] = f"/api/stream/{ep['file_id']}" if ep.get("file_id") else None
        ep["has_file"] = bool(ep.get("file_id"))
    return {"items": eps}


@app.get("/api/stream/{file_id:path}")
async def stream_video(file_id: str, request: Request):
    return await stream_file(file_id, request)


@app.head("/api/stream/{file_id:path}")
async def stream_video_head(file_id: str):
    from app.stream import stream_head_response
    return stream_head_response(file_id)


@app.get("/api/stream-info/{file_id:path}")
async def stream_info_ep(file_id: str):
    return await get_stream_info(file_id)


@app.get("/api/debug/stream-test/{file_id:path}")
@require_admin
async def debug_stream_test_ep(request: Request, file_id: str):
    from app.stream import debug_stream_test
    return await debug_stream_test(file_id)


@app.get("/api/debug/bot-membership")
@require_admin
async def debug_bot_membership(request: Request):
    from app.stream import _pyro_clients
    from app.config import PRIVATE_GROUP_ID
    results = []
    for i, pyro in enumerate(_pyro_clients):
        info: dict = {"client": i, "can_get_chat": False, "chat_error": None,
                      "is_member": False, "member_error": None}
        try:
            chat = await asyncio.wait_for(pyro.get_chat(PRIVATE_GROUP_ID), timeout=10)
            info["can_get_chat"] = True
            info["chat_title"] = getattr(chat, "title", str(chat))
            info["is_member"] = True
        except asyncio.TimeoutError:
            info["chat_error"] = "Timeout"
        except Exception as exc:
            info["chat_error"] = f"{type(exc).__name__}: {exc}"
        results.append(info)
    return {"private_group_id": PRIVATE_GROUP_ID, "clients": results}


@app.get("/api/debug/dialogs")
@require_admin
async def debug_dialogs(request: Request):
    """List first 20 dialogs from each Pyrogram client — for peer cache diagnostics."""
    from app.stream import _pyro_clients
    from app.config import PRIVATE_GROUP_ID
    results = []
    for i, pyro in enumerate(_pyro_clients):
        dialogs = []
        error = None
        try:
            async for dlg in pyro.get_dialogs():
                chat = dlg.chat
                cid = getattr(chat, "id", None)
                title = getattr(chat, "title", getattr(chat, "first_name", str(cid)))
                dialogs.append({"id": cid, "title": title, "is_target": abs(cid or 0) == abs(PRIVATE_GROUP_ID)})
                if len(dialogs) >= 20:
                    break
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
        results.append({"client": i, "dialogs": dialogs, "error": error})
    return {"private_group_id": PRIVATE_GROUP_ID, "clients": results}


@app.get("/api/debug/forum-topics")
@require_admin
async def debug_forum_topics(request: Request):
    """Test raw MTProto GetForumTopics on the private group."""
    from app.stream import _pyro_clients
    from app.config import PRIVATE_GROUP_ID
    from app.scanner import _get_forum_topics_raw
    results = []
    for i, pyro in enumerate(_pyro_clients[:1]):  # Only test client 0
        info: dict = {"client": i, "topics": [], "error": None, "count": 0,
                      "peer_resolved": False, "peer_error": None,
                      "history_test": None, "history_error": None}
        # Test 1: resolve_peer
        try:
            peer = await asyncio.wait_for(pyro.resolve_peer(PRIVATE_GROUP_ID), timeout=15)
            info["peer_resolved"] = True
            info["peer_info"] = {"channel_id": getattr(peer,"channel_id",None), "access_hash": bool(getattr(peer,"access_hash",None))}
        except Exception as e:
            info["peer_error"] = f"{type(e).__name__}: {e}"
        # Test 2: raw GetForumTopics
        try:
            topics = await _get_forum_topics_raw(pyro)
            info["count"] = len(topics)
            info["topics"] = [{"id": t.id, "title": t.title} for t in topics[:5]]
        except Exception as e:
            info["error"] = f"{type(e).__name__}: {e}"
        # Test 3: get_chat_history (limit=2)
        try:
            msgs = []
            async for m in pyro.get_chat_history(PRIVATE_GROUP_ID, limit=2):
                msgs.append({"id": m.id, "type": str(type(m.media).__name__ if m.media else "text")})
            info["history_test"] = msgs
        except Exception as e:
            info["history_error"] = f"{type(e).__name__}: {e}"
        results.append(info)
    return {"private_group_id": PRIVATE_GROUP_ID, "clients": results}


@app.get("/api/debug/pyro-errors")
@require_admin
async def debug_pyro_errors(request: Request):
    """Show Pyrogram startup errors for diagnostics."""
    from app.stream import _pyro_start_errors, _pyro_clients
    return {
        "clients_running": len(_pyro_clients),
        "startup_errors": _pyro_start_errors,
    }


@app.get("/api/debug/config")
@require_admin
async def debug_config(request: Request):
    """Show non-sensitive config values for diagnostics."""
    from app.config import PRIVATE_GROUP_ID, PUBLIC_CHANNEL_ID, ADMIN_ID, SESSION_1_API_ID, SESSION_2_API_ID
    from app.config import MAIN_BOT_TOKEN, STREAM_BOT_1, STREAM_BOT_2
    import re

@app.get("/api/cache/stats")
@require_admin
async def cache_stats(request: Request):
    """Get cache statistics (Admin only)."""
    return cache_get_stats()
    def mask(v: str) -> str:
        if not v: return "(not set)"
        if re.match(r'^\d+:[A-Za-z0-9_-]{30,}$', v.strip()): return f"bot_token:{v[:10]}..."
        if len(v) > 50: return f"session_string:{len(v)}chars"
        return f"value:{v[:8]}..."
    return {
        "PRIVATE_GROUP_ID": PRIVATE_GROUP_ID,
        "PUBLIC_CHANNEL_ID": PUBLIC_CHANNEL_ID,
        "ADMIN_ID": ADMIN_ID,
        "SESSION_1_API_ID": SESSION_1_API_ID,
        "SESSION_2_API_ID": SESSION_2_API_ID,
        "MAIN_BOT_TOKEN": mask(MAIN_BOT_TOKEN),
        "STREAM_BOT_1": mask(STREAM_BOT_1),
        "STREAM_BOT_2": mask(STREAM_BOT_2),
    }


@app.get("/api/search")
@rate_limit(max_requests=30, window_seconds=60)
async def search(request: Request, q: str = Query("", min_length=1), limit: int = Query(20)):
    import sqlite3 as sq
    from app.config import DB_PATH
    conn = sq.connect(DB_PATH); conn.row_factory = sq.Row; term = f"%{q}%"
    try:
        movies = [dict(r) for r in conn.execute(
            "SELECT * FROM movies WHERE title LIKE ? OR title_ar LIKE ? OR LOWER(title) LIKE LOWER(?) OR LOWER(title_ar) LIKE LOWER(?) ORDER BY rating DESC LIMIT ?",
            [term, term, term, term, limit]).fetchall()]
        series = [dict(r) for r in conn.execute(
            "SELECT s.*, "
            "CASE WHEN EXISTS(SELECT 1 FROM episodes e WHERE e.series_id=s.id AND e.file_id IS NOT NULL) "
            "     THEN 1 ELSE 0 END AS has_file "
            "FROM series s WHERE s.title LIKE ? OR s.title_ar LIKE ? OR LOWER(s.title) LIKE LOWER(?) OR LOWER(s.title_ar) LIKE LOWER(?) ORDER BY s.rating DESC LIMIT ?",
            [term, term, term, term, limit]).fetchall()]
    finally:
        conn.close()
    for m in movies:
        _j(m, ["genres", "cast"])
        m["has_file"] = bool(m.get("file_id"))
    for s in series:
        _j(s, ["genres", "cast"])
        s["has_file"] = bool(s.get("has_file"))
    return {"movies": movies, "series": series, "query": q}


@app.post("/api/admin/register_topic")
@require_admin
async def admin_register(request: Request, payload: dict):
    from app.sync_bot import register_topic, parse_topic_name
    name = payload.get("topic_name", "")
    topic_id = payload.get("topic_id", 0)
    parsed = parse_topic_name(name)
    if not parsed:
        raise HTTPException(400, "Cannot parse topic name")
    ok = await register_topic(name, topic_id)
    if not ok:
        raise HTTPException(500, "Registration failed")
    cache_clear_all()
    return {"ok": True, "parsed": parsed}


@app.post("/api/admin/cache_clear")
@require_admin
async def admin_cache_clear(request: Request):
    """Admin endpoint to manually clear all API cache."""
    cache_clear_all()
    return {"ok": True, "message": "Cache cleared"}


@app.post("/api/admin/fullscan")
@require_admin
async def admin_fullscan(request: Request):
    """Admin endpoint to trigger a full group scan."""
    from app.stream import _pyro_clients
    from app.scanner import run_full_scan
    from app import database as db
    
    if not _pyro_clients:
        raise HTTPException(503, "No Pyrogram clients available")
    
    results = await run_full_scan(_pyro_clients[0])
    s = db.get_stats()
    return {"ok": True, "scan": results, "stats": s}


# ══════════════════════════════════════════════════════════════════════════════
# Ads System Endpoints (UI only - disabled by default)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/ads/config")
async def get_ads_config():
    """Get ads system configuration."""
    from app.database import get_ads_config
    return get_ads_config()


@app.get("/api/ads/banners")
async def get_banners(limit: int = Query(5, ge=1, le=20)):
    """Get active banner ads."""
    from app.database import get_ads_config, get_active_banners
    
    config = get_ads_config()
    if not config.get("enabled") or not config.get("banner_enabled"):
        return {"banners": [], "enabled": False}
    
    banners = get_active_banners(limit=limit)
    return {"banners": banners, "enabled": True}


@app.post("/api/ads/impression/{ad_id}")
async def log_banner_impression(ad_id: int, request: Request):
    """Log banner ad impression."""
    from app.database import log_ad_impression
    
    client_ip = request.client.host if request.client else "unknown"
    page_url = request.headers.get("referer", "")
    
    log_ad_impression(
        ad_id=ad_id,
        ip_address=client_ip,
        page_url=page_url
    )
    
    return {"ok": True}


@app.post("/api/ads/click/{ad_id}")
async def log_banner_click(ad_id: int, request: Request):
    """Log banner ad click."""
    from app.database import log_ad_click
    
    client_ip = request.client.host if request.client else "unknown"
    
    log_ad_click(
        ad_id=ad_id,
        ip_address=client_ip
    )
    
    return {"ok": True}


@app.post("/api/admin/ads/config")
@require_admin
async def update_ads_config_endpoint(request: Request):
    """Update ads configuration (Admin only)."""
    from app.database import update_ads_config
    
    body = await request.json()
    
    update_ads_config(
        enabled=body.get("enabled"),
        banner_enabled=body.get("banner_enabled"),
        banner_interval=body.get("banner_interval"),
        banner_duration=body.get("banner_duration")
    )
    
    return {"ok": True, "message": "Ads config updated"}


@app.get("/api/admin/ads/banners")
@require_admin
async def list_all_banners(request: Request):
    """List all banner ads (Admin only)."""
    import sqlite3
    from app.config import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT * FROM ads_banners 
            ORDER BY priority DESC, created_at DESC
        """).fetchall()
        return {"banners": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.post("/api/admin/ads/banner")
@require_admin
async def create_banner(request: Request):
    """Create new banner ad (Admin only)."""
    import sqlite3
    from app.config import DB_PATH
    
    body = await request.json()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute("""
            INSERT INTO ads_banners 
            (title, description, image_url, link_url, position, priority, active, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            body.get("title"),
            body.get("description"),
            body.get("image_url"),
            body.get("link_url"),
            body.get("position", "bottom"),
            body.get("priority", 0),
            body.get("active", 1),
            body.get("start_date"),
            body.get("end_date")
        ))
        conn.commit()
        return {"ok": True, "id": cursor.lastrowid}
    finally:
        conn.close()


@app.put("/api/admin/ads/banner/{banner_id}")
@require_admin
async def update_banner(banner_id: int, request: Request):
    """Update banner ad (Admin only)."""
    import sqlite3
    from app.config import DB_PATH
    
    body = await request.json()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        updates = []
        params = []
        
        for field in ["title", "description", "image_url", "link_url", "position", 
                      "priority", "active", "start_date", "end_date"]:
            if field in body:
                updates.append(f"{field}=?")
                params.append(body[field])
        
        if updates:
            updates.append("updated_at=datetime('now')")
            query = f"UPDATE ads_banners SET {', '.join(updates)} WHERE id=?"
            params.append(banner_id)
            conn.execute(query, params)
            conn.commit()
        
        return {"ok": True}
    finally:
        conn.close()


@app.delete("/api/admin/ads/banner/{banner_id}")
@require_admin
async def delete_banner(banner_id: int, request: Request):
    """Delete banner ad (Admin only)."""
    import sqlite3
    from app.config import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM ads_banners WHERE id=?", (banner_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/admin/ads/stats")
@require_admin
async def get_ads_stats(request: Request, days: int = Query(7, ge=1, le=90)):
    """Get ads statistics (Admin only)."""
    import sqlite3
    from app.config import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cutoff = f"datetime('now', '-{days} days')"
        
        # Banner performance
        banners = conn.execute(f"""
            SELECT
                b.id, b.title, b.impressions, b.clicks,
                CASE WHEN b.impressions > 0
                     THEN ROUND(CAST(b.clicks AS FLOAT) / b.impressions * 100, 2)
                     ELSE 0 END AS ctr,
                COUNT(DISTINCT i.id) AS recent_impressions,
                COUNT(DISTINCT c.id) AS recent_clicks
            FROM ads_banners b
            LEFT JOIN ads_impressions i ON b.id = i.ad_id AND i.created_at >= {cutoff}
            LEFT JOIN ads_clicks c ON b.id = c.ad_id AND c.created_at >= {cutoff}
            GROUP BY b.id
            ORDER BY b.impressions DESC
        """).fetchall()
        
        return {
            "banners": [dict(b) for b in banners],
            "period_days": days
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Subscription System Endpoints (UI only - disabled by default)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/subscriptions/config")
async def get_subscription_config():
    """Get subscription system configuration."""
    from app.database import get_subscription_config
    return get_subscription_config()


@app.get("/api/subscriptions/plans")
async def get_plans():
    """Get available subscription plans."""
    from app.database import get_subscription_config, get_subscription_plans
    
    config = get_subscription_config()
    if not config.get("enabled"):
        return {"plans": [], "enabled": False}
    
    plans = get_subscription_plans(active_only=True)
    return {"plans": plans, "enabled": True}


@app.get("/api/subscriptions/user/{user_id}")
async def get_user_subscription_endpoint(user_id: int):
    """Get user's active subscription."""
    from app.database import get_user_subscription
    
    subscription = get_user_subscription(user_id)
    return {"subscription": subscription}


@app.get("/api/subscriptions/check/{user_id}")
async def check_premium_status(user_id: int):
    """Check if user has premium subscription."""
    from app.database import is_user_premium
    
    is_premium = is_user_premium(user_id)
    return {"user_id": user_id, "is_premium": is_premium}


@app.post("/api/admin/subscriptions/config")
@require_admin
async def update_subscription_config_endpoint(request: Request):
    """Update subscription configuration (Admin only)."""
    from app.database import update_subscription_config
    
    body = await request.json()
    
    update_subscription_config(
        enabled=body.get("enabled"),
        trial_enabled=body.get("trial_enabled"),
        trial_days=body.get("trial_days")
    )
    
    return {"ok": True, "message": "Subscription config updated"}


@app.get("/api/admin/subscriptions/plans")
@require_admin
async def list_all_plans(request: Request):
    """List all subscription plans (Admin only)."""
    from app.database import get_subscription_plans
    
    plans = get_subscription_plans(active_only=False)
    return {"plans": plans}


@app.post("/api/admin/subscriptions/plan")
@require_admin
async def create_plan(request: Request):
    """Create new subscription plan (Admin only)."""
    import sqlite3, json
    from app.config import DB_PATH
    
    body = await request.json()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        features = json.dumps(body.get("features", []))
        
        cursor = conn.execute("""
            INSERT INTO subscription_plans 
            (name, name_ar, description, description_ar, price, currency, 
             duration_days, features, active, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            body.get("name"),
            body.get("name_ar"),
            body.get("description"),
            body.get("description_ar"),
            body.get("price"),
            body.get("currency", "USD"),
            body.get("duration_days"),
            features,
            body.get("active", 1),
            body.get("priority", 0)
        ))
        conn.commit()
        return {"ok": True, "id": cursor.lastrowid}
    finally:
        conn.close()


@app.put("/api/admin/subscriptions/plan/{plan_id}")
@require_admin
async def update_plan(plan_id: int, request: Request):
    """Update subscription plan (Admin only)."""
    import sqlite3, json
    from app.config import DB_PATH
    
    body = await request.json()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        updates = []
        params = []
        
        for field in ["name", "name_ar", "description", "description_ar", 
                      "price", "currency", "duration_days", "active", "priority"]:
            if field in body:
                updates.append(f"{field}=?")
                params.append(body[field])
        
        if "features" in body:
            updates.append("features=?")
            params.append(json.dumps(body["features"]))
        
        if updates:
            updates.append("updated_at=datetime('now')")
            query = f"UPDATE subscription_plans SET {', '.join(updates)} WHERE id=?"
            params.append(plan_id)
            conn.execute(query, params)
            conn.commit()
        
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/admin/subscriptions/users")
@require_admin
async def list_user_subscriptions(request: Request, 
                                   status: str = Query(None),
                                   limit: int = Query(50, ge=1, le=200)):
    """List user subscriptions (Admin only)."""
    import sqlite3
    from app.config import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        query = """
            SELECT us.*, sp.name, sp.name_ar, sp.price, sp.currency
            FROM user_subscriptions us
            JOIN subscription_plans sp ON us.plan_id = sp.id
        """
        params = []
        
        if status:
            query += " WHERE us.status=?"
            params.append(status)
        
        query += " ORDER BY us.created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        return {"subscriptions": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.get("/api/admin/subscriptions/stats")
@require_admin
async def get_subscription_stats(request: Request):
    """Get subscription statistics (Admin only)."""
    import sqlite3
    from app.config import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Count by status
        stats = conn.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                SUM(CASE WHEN plan_id > 1 THEN 1 ELSE 0 END) as premium_count
            FROM user_subscriptions
            GROUP BY status
        """).fetchall()
        
        # Revenue (last 30 days)
        revenue = conn.execute("""
            SELECT 
                SUM(amount) as total_revenue,
                COUNT(*) as transaction_count
            FROM subscription_transactions
            WHERE status='completed' 
            AND created_at >= datetime('now', '-30 days')
        """).fetchone()
        
        # Plan distribution
        plans = conn.execute("""
            SELECT 
                sp.name, sp.name_ar, sp.price,
                COUNT(us.id) as subscriber_count
            FROM subscription_plans sp
            LEFT JOIN user_subscriptions us ON sp.id = us.plan_id AND us.status='active'
            GROUP BY sp.id
            ORDER BY subscriber_count DESC
        """).fetchall()
        
        return {
            "status_breakdown": [dict(r) for r in stats],
            "revenue_30d": dict(revenue) if revenue else {"total_revenue": 0, "transaction_count": 0},
            "plan_distribution": [dict(r) for r in plans]
        }
    finally:
        conn.close()


# ── Static frontend ─────────────────────────────────────────────────────────
import os as _os
_static_dir = _os.path.join(_os.path.dirname(__file__), "..", "static")
if _os.path.isdir(_static_dir):
    app.mount("/assets", StaticFiles(directory=_os.path.join(_static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't serve SPA for API routes
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(404, "Not Found")
        index = _os.path.join(_static_dir, "index.html")
        return FileResponse(index)
