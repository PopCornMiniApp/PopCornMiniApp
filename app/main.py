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
        user_bot = _pyro_clients[1] if len(_pyro_clients) > 1 else _pyro_clients[0]
        results = await run_full_scan(user_bot)
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
            # Use user bot (s1) instead of bot account for smart sync
            user_bot = _pyro_clients[1] if len(_pyro_clients) > 1 else _pyro_clients[0]
            results = await run_catch_up_sync(user_bot)
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
                # Use user bot (s1) instead of bot account for smart sync
                user_bot = _pyro_clients[1] if len(_pyro_clients) > 1 else _pyro_clients[0]
                results = await run_smart_sync(user_bot)
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
                user_bot = _pyro_clients[1] if len(_pyro_clients) > 1 else _pyro_clients[0]
                results = await run_full_scan(user_bot)
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
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
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
    
    user_bot = _pyro_clients[1] if len(_pyro_clients) > 1 else _pyro_clients[0]
    results = await run_full_scan(user_bot)
    s = db.get_stats()
    return {"ok": True, "scan": results, "stats": s}


# ══════════════════════════════════════════════════════════════════════════════
# Admin Dashboard Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/stats")
@require_admin
async def admin_get_stats(request: Request):
    """Get comprehensive admin statistics."""
    from app.database import get_admin_stats
    
    client_ip = request.client.host if request.client else "unknown"
    db.log_admin_action(
        admin_id=ADMIN_ID,
        action_type="view_stats",
        ip_address=client_ip
    )
    
    return get_admin_stats()


@app.get("/api/admin/users")
@require_admin
async def admin_get_users(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str = Query(None),
    blocked_only: bool = Query(False)
):
    """Get all users with filtering."""
    from app.database import get_all_users
    
    result = get_all_users(
        limit=limit,
        offset=offset,
        search=search,
        blocked_only=blocked_only
    )
    
    return result


@app.get("/api/admin/users/{user_id}")
@require_admin
async def admin_get_user(request: Request, user_id: int):
    """Get specific user details."""
    from app.database import get_user
    
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    return user


@app.post("/api/admin/users/{user_id}/block")
@require_admin
async def admin_block_user(request: Request, user_id: int):
    """Block a user."""
    from app.database import block_user, log_admin_action
    
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        block_user(user_id, blocked=True)
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="block_user",
            target_type="user",
            target_id=str(user_id),
            ip_address=client_ip,
            status="success"
        )
        cache_clear_prefix("user_")
        return {"ok": True, "message": f"User {user_id} blocked"}
    except Exception as e:
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="block_user",
            target_type="user",
            target_id=str(user_id),
            ip_address=client_ip,
            status="failed",
            action_details=str(e)
        )
        raise HTTPException(500, f"Failed to block user: {str(e)}")


@app.post("/api/admin/users/{user_id}/unblock")
@require_admin
async def admin_unblock_user(request: Request, user_id: int):
    """Unblock a user."""
    from app.database import block_user, log_admin_action
    
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        block_user(user_id, blocked=False)
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="unblock_user",
            target_type="user",
            target_id=str(user_id),
            ip_address=client_ip,
            status="success"
        )
        cache_clear_prefix("user_")
        return {"ok": True, "message": f"User {user_id} unblocked"}
    except Exception as e:
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="unblock_user",
            target_type="user",
            target_id=str(user_id),
            ip_address=client_ip,
            status="failed",
            action_details=str(e)
        )
        raise HTTPException(500, f"Failed to unblock user: {str(e)}")


@app.delete("/api/admin/users/{user_id}")
@require_admin
async def admin_delete_user(request: Request, user_id: int):
    """Delete a user and all related data."""
    from app.database import delete_user, log_admin_action
    
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        delete_user(user_id)
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="delete_user",
            target_type="user",
            target_id=str(user_id),
            ip_address=client_ip,
            status="success"
        )
        cache_clear_prefix("user_")
        return {"ok": True, "message": f"User {user_id} deleted"}
    except Exception as e:
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="delete_user",
            target_type="user",
            target_id=str(user_id),
            ip_address=client_ip,
            status="failed",
            action_details=str(e)
        )
        raise HTTPException(500, f"Failed to delete user: {str(e)}")


@app.get("/api/admin/content")
@require_admin
async def admin_get_content(
    request: Request,
    content_type: str = Query("movie", regex="^(movie|series)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str = Query(None),
    has_file: bool = Query(None)
):
    """Get content (movies or series) for admin management."""
    if content_type == "movie":
        items = db.get_movies(limit=limit, offset=offset, search=search)
        total = db.get_connection().execute(
            "SELECT COUNT(*) FROM movies" + (" WHERE title LIKE ? OR title_ar LIKE ?" if search else ""),
            [f"%{search}%", f"%{search}%"] if search else []
        ).fetchone()[0]
    else:
        items = db.get_series_list(limit=limit, offset=offset, search=search)
        total = db.get_connection().execute(
            "SELECT COUNT(*) FROM series" + (" WHERE title LIKE ? OR title_ar LIKE ?" if search else ""),
            [f"%{search}%", f"%{search}%"] if search else []
        ).fetchone()[0]
    
    for item in items:
        _j(item, ["genres", "cast"])
        if content_type == "movie":
            item["has_file"] = bool(item.get("file_id"))
    
    return {"items": items, "total": total, "content_type": content_type}


@app.delete("/api/admin/content/{content_type}/{content_id}")
@require_admin
async def admin_delete_content(
    request: Request,
    content_type: str,
    content_id: str
):
    """Delete movie or series."""
    from app.database import delete_content, log_admin_action
    
    if content_type not in ["movie", "series"]:
        raise HTTPException(400, "Invalid content type")
    
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        delete_content(content_type, content_id)
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type=f"delete_{content_type}",
            target_type=content_type,
            target_id=content_id,
            ip_address=client_ip,
            status="success"
        )
        cache_clear_all()
        return {"ok": True, "message": f"{content_type.capitalize()} {content_id} deleted"}
    except Exception as e:
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type=f"delete_{content_type}",
            target_type=content_type,
            target_id=content_id,
            ip_address=client_ip,
            status="failed",
            action_details=str(e)
        )
        raise HTTPException(500, f"Failed to delete {content_type}: {str(e)}")


@app.get("/api/admin/audit-logs")
@require_admin
async def admin_get_audit_logs(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action_type: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    """Get audit logs with filtering."""
    from app.database import get_audit_logs
    
    result = get_audit_logs(
        limit=limit,
        offset=offset,
        admin_id=None,
        action_type=action_type,
        start_date=start_date,
        end_date=end_date
    )
    
    return result


@app.get("/api/admin/notifications")
@require_admin
async def admin_get_notifications(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query(None)
):
    """Get notifications."""
    from app.database import get_notifications
    
    result = get_notifications(limit=limit, offset=offset, status=status)
    return result


@app.post("/api/admin/notifications")
@require_admin
async def admin_create_notification(request: Request, payload: dict):
    """Create a new notification."""
    from app.database import create_notification, log_admin_action
    
    title = payload.get("title")
    message = payload.get("message")
    target_type = payload.get("target_type", "all")
    target_ids = payload.get("target_ids")
    scheduled_at = payload.get("scheduled_at")
    
    if not title or not message:
        raise HTTPException(400, "Title and message are required")
    
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        notification_id = create_notification(
            title=title,
            message=message,
            target_type=target_type,
            target_ids=target_ids,
            scheduled_at=scheduled_at,
            created_by=ADMIN_ID
        )
        
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="create_notification",
            action_details=f"Title: {title}",
            ip_address=client_ip,
            status="success"
        )
        
        return {"ok": True, "notification_id": notification_id}
    except Exception as e:
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="create_notification",
            ip_address=client_ip,
            status="failed",
            action_details=str(e)
        )
        raise HTTPException(500, f"Failed to create notification: {str(e)}")


@app.get("/api/admin/bot-status")
@require_admin
async def admin_get_bot_status(request: Request):
    """Get status of all bots."""
    from app.database import get_bot_statuses
    from app.stream import _pyro_clients
    
    # Get stored bot statuses
    statuses = get_bot_statuses()
    
    # Add current Pyrogram status
    pyrogram_status = {
        "bot_name": "Pyrogram Clients",
        "bot_type": "streaming",
        "status": "active" if _pyro_clients else "inactive",
        "clients_count": len(_pyro_clients),
        "last_check": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return {
        "pyrogram": pyrogram_status,
        "bots": statuses
    }


@app.get("/api/admin/sync-status")
@require_admin
async def admin_get_sync_status(request: Request):
    """Get current sync status."""
    from app.database import get_sync_status
    
    sync_status = get_sync_status()
    stats = db.get_stats()
    
    return {
        "sync_status": sync_status,
        "stats": stats
    }


@app.post("/api/admin/sync-db")
@require_admin
async def admin_sync_db(request: Request):
    """Manually trigger database sync to HuggingFace."""
    from app.database import push_db_to_hf, log_admin_action
    
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        push_db_to_hf()
        cache_clear_all()
        
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="sync_db",
            ip_address=client_ip,
            status="success"
        )
        
        return {"ok": True, "message": "Database synced to HuggingFace"}
    except Exception as e:
        log_admin_action(
            admin_id=ADMIN_ID,
            action_type="sync_db",
            ip_address=client_ip,
            status="failed",
            action_details=str(e)
        )
        raise HTTPException(500, f"Failed to sync database: {str(e)}")



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


# ══════════════════════════════════════════════════════════════════════════════
# Friends System API Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/friends/search")
@rate_limit(max_requests=30, window_seconds=60)
async def search_users_endpoint(
    request: Request,
    query: str = Query(..., min_length=2),
    user_id: int = Query(...),
    limit: int = Query(20, ge=1, le=50)
):
    """Search for users to add as friends."""
    from app.friends import FriendsManager
    
    results = FriendsManager.search_users(query, user_id, limit)
    return {"users": results}


@app.post("/api/friends/request")
@rate_limit(max_requests=10, window_seconds=60)
async def send_friend_request_endpoint(request: Request):
    """Send a friend request."""
    from app.friends import FriendsManager
    
    data = await request.json()
    from_user_id = data.get("from_user_id")
    to_user_id = data.get("to_user_id")
    message = data.get("message")
    
    if not from_user_id or not to_user_id:
        raise HTTPException(400, "Missing required fields")
    
    result = FriendsManager.send_friend_request(from_user_id, to_user_id, message)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to send friend request"))
    
    return result


@app.get("/api/friends/requests")
@rate_limit(max_requests=30, window_seconds=60)
async def get_friend_requests_endpoint(
    request: Request,
    user_id: int = Query(...),
    request_type: str = Query("received", regex="^(received|sent)$")
):
    """Get friend requests (received or sent)."""
    from app.friends import FriendsManager
    
    requests_list = FriendsManager.get_friend_requests(user_id, request_type)
    return {"requests": requests_list}


@app.post("/api/friends/accept/{request_id}")
@rate_limit(max_requests=20, window_seconds=60)
async def accept_friend_request_endpoint(request: Request, request_id: int):
    """Accept a friend request."""
    from app.friends import FriendsManager
    
    data = await request.json()
    user_id = data.get("user_id")
    
    if not user_id:
        raise HTTPException(400, "Missing user_id")
    
    result = FriendsManager.accept_friend_request(request_id, user_id)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to accept friend request"))
    
    cache_clear_prefix(f"friends_{user_id}")
    return result


@app.post("/api/friends/reject/{request_id}")
@rate_limit(max_requests=20, window_seconds=60)
async def reject_friend_request_endpoint(request: Request, request_id: int):
    """Reject a friend request."""
    from app.friends import FriendsManager
    
    data = await request.json()
    user_id = data.get("user_id")
    
    if not user_id:
        raise HTTPException(400, "Missing user_id")
    
    result = FriendsManager.reject_friend_request(request_id, user_id)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to reject friend request"))
    
    return result


@app.post("/api/friends/cancel/{request_id}")
@rate_limit(max_requests=20, window_seconds=60)
async def cancel_friend_request_endpoint(request: Request, request_id: int):
    """Cancel a sent friend request."""
    from app.friends import FriendsManager
    
    data = await request.json()
    user_id = data.get("user_id")
    
    if not user_id:
        raise HTTPException(400, "Missing user_id")
    
    result = FriendsManager.cancel_friend_request(request_id, user_id)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to cancel friend request"))
    
    return result


@app.get("/api/friends/list")
@rate_limit(max_requests=30, window_seconds=60)
async def get_friends_list_endpoint(
    request: Request,
    user_id: int = Query(...),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Get user's friends list."""
    from app.friends import FriendsManager
    
    cache_key = f"friends_{user_id}_{limit}_{offset}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    friends = FriendsManager.get_friends_list(user_id, limit, offset)
    result = {"friends": friends}
    
    cache_set(cache_key, result, 60)
    return result


@app.delete("/api/friends/remove/{friend_id}")
@rate_limit(max_requests=20, window_seconds=60)
async def remove_friend_endpoint(request: Request, friend_id: int):
    """Remove a friend."""
    from app.friends import FriendsManager
    
    data = await request.json()
    user_id = data.get("user_id")
    
    if not user_id:
        raise HTTPException(400, "Missing user_id")
    
    result = FriendsManager.remove_friend(user_id, friend_id)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to remove friend"))
    
    cache_clear_prefix(f"friends_{user_id}")
    return result


@app.post("/api/friends/block/{blocked_user_id}")
@rate_limit(max_requests=10, window_seconds=60)
async def block_user_endpoint(request: Request, blocked_user_id: int):
    """Block a user."""
    from app.friends import FriendsManager
    
    data = await request.json()
    user_id = data.get("user_id")
    reason = data.get("reason")
    
    if not user_id:
        raise HTTPException(400, "Missing user_id")
    
    result = FriendsManager.block_user(user_id, blocked_user_id, reason)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to block user"))
    
    cache_clear_prefix(f"friends_{user_id}")
    return result


@app.post("/api/friends/unblock/{blocked_user_id}")
@rate_limit(max_requests=10, window_seconds=60)
async def unblock_user_endpoint(request: Request, blocked_user_id: int):
    """Unblock a user."""
    from app.friends import FriendsManager
    
    data = await request.json()
    user_id = data.get("user_id")
    
    if not user_id:
        raise HTTPException(400, "Missing user_id")
    
    result = FriendsManager.unblock_user(user_id, blocked_user_id)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to unblock user"))
    
    return result


@app.get("/api/friends/blocked")
@rate_limit(max_requests=20, window_seconds=60)
async def get_blocked_users_endpoint(request: Request, user_id: int = Query(...)):
    """Get list of blocked users."""
    from app.friends import FriendsManager
    
    blocked = FriendsManager.get_blocked_users(user_id)
    return {"blocked_users": blocked}


@app.get("/api/friends/status/{other_user_id}")
@rate_limit(max_requests=30, window_seconds=60)
async def get_friendship_status_endpoint(
    request: Request,
    other_user_id: int,
    user_id: int = Query(...)
):
    """Get friendship status with another user."""
    from app.friends import FriendsManager
    
    status = FriendsManager.get_friendship_status(user_id, other_user_id)
    return {"status": status}


# ══════════════════════════════════════════════════════════════════════════════
# Messaging System API Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/messages/conversations")
@rate_limit(max_requests=20, window_seconds=60)
async def create_conversation_endpoint(request: Request):
    """Create a new conversation."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    user_ids = data.get("user_ids", [])
    conversation_type = data.get("type", "direct")
    name = data.get("name")
    created_by = data.get("created_by")
    
    if not user_ids or len(user_ids) < 2:
        raise HTTPException(400, "At least 2 users required")
    
    result = MessagingManager.create_conversation(user_ids, conversation_type, name, created_by)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to create conversation"))
    
    return result


@app.get("/api/messages/conversations")
@rate_limit(max_requests=30, window_seconds=60)
async def get_conversations_endpoint(
    request: Request,
    user_id: int = Query(...),
    include_archived: bool = Query(False)
):
    """Get user's conversations."""
    from app.messaging import MessagingManager
    
    cache_key = f"conversations_{user_id}_{include_archived}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    conversations = MessagingManager.get_conversations(user_id, include_archived)
    result = {"conversations": conversations}
    
    cache_set(cache_key, result, 30)
    return result


@app.post("/api/messages/send")
@rate_limit(max_requests=60, window_seconds=60)
async def send_message_endpoint(request: Request):
    """Send a message."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    conversation_id = data.get("conversation_id")
    sender_id = data.get("sender_id")
    content = data.get("content")
    media_type = data.get("media_type", "text")
    media_file_id = data.get("media_file_id")
    media_metadata = data.get("media_metadata")
    reply_to_message_id = data.get("reply_to_message_id")
    
    if not conversation_id or not sender_id:
        raise HTTPException(400, "Missing required fields")
    
    if media_type == "text" and not content:
        raise HTTPException(400, "Text messages require content")
    
    result = MessagingManager.send_message(
        conversation_id, sender_id, content, media_type,
        media_file_id, media_metadata, reply_to_message_id
    )
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to send message"))
    
    cache_clear_prefix(f"conversations_{sender_id}")
    cache_clear_prefix(f"messages_{conversation_id}")
    return result


@app.get("/api/messages/{conversation_id}")
@rate_limit(max_requests=60, window_seconds=60)
async def get_messages_endpoint(
    request: Request,
    conversation_id: int,
    user_id: int = Query(...),
    limit: int = Query(50, ge=1, le=100),
    before_message_id: int = Query(None)
):
    """Get messages from a conversation."""
    from app.messaging import MessagingManager
    
    messages = MessagingManager.get_messages(conversation_id, user_id, limit, before_message_id)
    return {"messages": messages}


@app.put("/api/messages/edit/{message_id}")
@rate_limit(max_requests=30, window_seconds=60)
async def edit_message_endpoint(request: Request, message_id: int):
    """Edit a message."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    user_id = data.get("user_id")
    new_content = data.get("content")
    
    if not user_id or not new_content:
        raise HTTPException(400, "Missing required fields")
    
    result = MessagingManager.edit_message(message_id, user_id, new_content)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to edit message"))
    
    return result


@app.delete("/api/messages/delete/{message_id}")
@rate_limit(max_requests=30, window_seconds=60)
async def delete_message_endpoint(request: Request, message_id: int):
    """Delete a message."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    user_id = data.get("user_id")
    
    if not user_id:
        raise HTTPException(400, "Missing user_id")
    
    result = MessagingManager.delete_message(message_id, user_id)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to delete message"))
    
    return result


@app.post("/api/messages/read")
@rate_limit(max_requests=60, window_seconds=60)
async def mark_as_read_endpoint(request: Request):
    """Mark messages as read."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")
    message_id = data.get("message_id")
    
    if not conversation_id or not user_id:
        raise HTTPException(400, "Missing required fields")
    
    result = MessagingManager.mark_as_read(conversation_id, user_id, message_id)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to mark as read"))
    
    cache_clear_prefix(f"conversations_{user_id}")
    return result


@app.post("/api/messages/reaction")
@rate_limit(max_requests=60, window_seconds=60)
async def add_reaction_endpoint(request: Request):
    """Add a reaction to a message."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    message_id = data.get("message_id")
    user_id = data.get("user_id")
    reaction = data.get("reaction")
    
    if not message_id or not user_id or not reaction:
        raise HTTPException(400, "Missing required fields")
    
    result = MessagingManager.add_reaction(message_id, user_id, reaction)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to add reaction"))
    
    return result


@app.delete("/api/messages/reaction")
@rate_limit(max_requests=60, window_seconds=60)
async def remove_reaction_endpoint(request: Request):
    """Remove a reaction from a message."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    message_id = data.get("message_id")
    user_id = data.get("user_id")
    reaction = data.get("reaction")
    
    if not message_id or not user_id or not reaction:
        raise HTTPException(400, "Missing required fields")
    
    result = MessagingManager.remove_reaction(message_id, user_id, reaction)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to remove reaction"))
    
    return result


@app.get("/api/messages/unread")
@rate_limit(max_requests=30, window_seconds=60)
async def get_unread_count_endpoint(request: Request, user_id: int = Query(...)):
    """Get total unread message count."""
    from app.messaging import MessagingManager
    
    count = MessagingManager.get_unread_count(user_id)
    return {"unread_count": count}


@app.post("/api/messages/typing")
@rate_limit(max_requests=120, window_seconds=60)
async def set_typing_indicator_endpoint(request: Request):
    """Set typing indicator."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")
    is_typing = data.get("is_typing", True)
    
    if not conversation_id or not user_id:
        raise HTTPException(400, "Missing required fields")
    
    result = MessagingManager.set_typing_indicator(conversation_id, user_id, is_typing)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to set typing indicator"))
    
    return result


@app.get("/api/messages/typing/{conversation_id}")
@rate_limit(max_requests=60, window_seconds=60)
async def get_typing_users_endpoint(
    request: Request,
    conversation_id: int,
    user_id: int = Query(...)
):
    """Get users currently typing in a conversation."""
    from app.messaging import MessagingManager
    
    typing_users = MessagingManager.get_typing_users(conversation_id, user_id)
    return {"typing_users": typing_users}


@app.post("/api/messages/online")
@rate_limit(max_requests=60, window_seconds=60)
async def update_online_status_endpoint(request: Request):
    """Update user's online status."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    user_id = data.get("user_id")
    is_online = data.get("is_online", True)
    status_text = data.get("status_text")
    
    if not user_id:
        raise HTTPException(400, "Missing user_id")
    
    result = MessagingManager.update_online_status(user_id, is_online, status_text)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to update online status"))
    
    return result


@app.post("/api/messages/conversation/settings")
@rate_limit(max_requests=30, window_seconds=60)
async def toggle_conversation_setting_endpoint(request: Request):
    """Toggle conversation settings (pin, mute, archive)."""
    from app.messaging import MessagingManager
    
    data = await request.json()
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")
    setting = data.get("setting")
    value = data.get("value", True)
    
    if not conversation_id or not user_id or not setting:
        raise HTTPException(400, "Missing required fields")
    
    result = MessagingManager.toggle_conversation_setting(conversation_id, user_id, setting, value)
    
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to update setting"))
    
    cache_clear_prefix(f"conversations_{user_id}")
    return result


@app.get("/api/messages/search/{conversation_id}")
@rate_limit(max_requests=30, window_seconds=60)
async def search_messages_endpoint(
    request: Request,
    conversation_id: int,
    user_id: int = Query(...),
    query: str = Query(..., min_length=2),
    limit: int = Query(50, ge=1, le=100)
):
    """Search messages in a conversation."""
    from app.messaging import MessagingManager
    
    messages = MessagingManager.search_messages(conversation_id, user_id, query, limit)
    return {"messages": messages}


# ══════════════════════════════════════════════════════════════════════════════
# Watch Rooms API Endpoints
# ══════════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel
from typing import Optional as Opt


class CreateRoomRequest(BaseModel):
    host_user_id: int
    content_type: str
    content_id: str
    name: str
    description: str = ""
    episode_id: Opt[int] = None
    is_public: bool = True
    password: Opt[str] = None
    max_participants: int = 50
    sync_mode: str = "host_control"
    voice_chat_enabled: bool = False


class JoinRoomRequest(BaseModel):
    user_id: int
    password: Opt[str] = None


class UpdateRoomRequest(BaseModel):
    user_id: int
    name: Opt[str] = None
    description: Opt[str] = None
    is_public: Opt[bool] = None
    password: Opt[str] = None
    max_participants: Opt[int] = None
    sync_mode: Opt[str] = None
    voice_chat_enabled: Opt[bool] = None


class SyncPlaybackRequest(BaseModel):
    user_id: int
    action: str
    timestamp: float
    playback_speed: float = 1.0


class SendMessageRequest(BaseModel):
    user_id: int
    content: str
    message_type: str = "text"
    reply_to: Opt[int] = None


@app.post("/api/rooms/create")
@rate_limit(max_requests=10, window_seconds=60)
async def create_room_endpoint(request: Request, data: CreateRoomRequest):
    """Create a new watch room."""
    from app import watch_rooms
    
    try:
        room = watch_rooms.create_room(
            host_user_id=data.host_user_id,
            content_type=data.content_type,
            content_id=data.content_id,
            name=data.name,
            description=data.description,
            episode_id=data.episode_id,
            is_public=data.is_public,
            password=data.password,
            max_participants=data.max_participants,
            sync_mode=data.sync_mode,
            voice_chat_enabled=data.voice_chat_enabled
        )
        return {"success": True, "room": room}
    except Exception as e:
        logger.error(f"Error creating room: {e}")
        raise HTTPException(500, str(e))


@app.get("/api/rooms/active")
async def get_active_rooms_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    content_type: Opt[str] = Query(None),
    is_public: bool = Query(True)
):
    """Get list of active watch rooms."""
    from app import watch_rooms
    
    cached_key = f"active_rooms_{content_type}_{is_public}_{limit}_{offset}"
    cached = cache_get(cached_key)
    if cached:
        return cached
    
    rooms = watch_rooms.get_active_rooms(
        limit=limit,
        offset=offset,
        content_type=content_type,
        is_public=is_public
    )
    
    result = {"rooms": rooms, "count": len(rooms)}
    cache_set(cached_key, result, 10)  # Cache for 10 seconds
    return result


@app.get("/api/rooms/{room_id}")
async def get_room_details_endpoint(room_id: str):
    """Get detailed information about a room."""
    from app import watch_rooms
    
    try:
        room = watch_rooms.get_room_details(room_id)
        return {"success": True, "room": room}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error getting room details: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/rooms/{room_id}/join")
@rate_limit(max_requests=20, window_seconds=60)
async def join_room_endpoint(request: Request, room_id: str, data: JoinRoomRequest):
    """Join a watch room."""
    from app import watch_rooms
    
    try:
        room = watch_rooms.join_room(
            room_id=room_id,
            user_id=data.user_id,
            password=data.password
        )
        return {"success": True, "room": room}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error joining room: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/rooms/{room_id}/leave")
@rate_limit(max_requests=20, window_seconds=60)
async def leave_room_endpoint(request: Request, room_id: str, user_id: int = Query(...)):
    """Leave a watch room."""
    from app import watch_rooms
    
    try:
        success = watch_rooms.leave_room(room_id, user_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error leaving room: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/rooms/{room_id}/kick")
@rate_limit(max_requests=10, window_seconds=60)
async def kick_participant_endpoint(
    request: Request,
    room_id: str,
    user_id: int = Query(...),
    target_id: int = Query(...)
):
    """Kick a participant from the room."""
    from app import watch_rooms
    from app.websocket_manager import notify_participant_kicked
    
    try:
        success = watch_rooms.kick_participant(room_id, user_id, target_id)
        if success:
            await notify_participant_kicked(room_id, target_id)
        return {"success": success}
    except ValueError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error(f"Error kicking participant: {e}")
        raise HTTPException(500, str(e))


@app.put("/api/rooms/{room_id}/settings")
@rate_limit(max_requests=10, window_seconds=60)
async def update_room_settings_endpoint(
    request: Request,
    room_id: str,
    data: UpdateRoomRequest
):
    """Update room settings."""
    from app import watch_rooms
    from app.websocket_manager import notify_room_update
    
    try:
        room = watch_rooms.update_room_settings(
            room_id=room_id,
            user_id=data.user_id,
            name=data.name,
            description=data.description,
            is_public=data.is_public,
            password=data.password,
            max_participants=data.max_participants,
            sync_mode=data.sync_mode,
            voice_chat_enabled=data.voice_chat_enabled
        )
        await notify_room_update(room_id, "settings", room)
        return {"success": True, "room": room}
    except ValueError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error(f"Error updating room settings: {e}")
        raise HTTPException(500, str(e))


@app.delete("/api/rooms/{room_id}")
@rate_limit(max_requests=10, window_seconds=60)
async def delete_room_endpoint(request: Request, room_id: str, user_id: int = Query(...)):
    """Delete a watch room."""
    from app import watch_rooms
    from app.websocket_manager import notify_room_ended
    
    try:
        success = watch_rooms.delete_room(room_id, user_id)
        if success:
            await notify_room_ended(room_id)
        return {"success": success}
    except ValueError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error(f"Error deleting room: {e}")
        raise HTTPException(500, str(e))


@app.get("/api/rooms/search")
async def search_rooms_endpoint(query: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=50)):
    """Search for watch rooms."""
    from app import watch_rooms
    
    rooms = watch_rooms.search_rooms(query, limit)
    return {"rooms": rooms, "count": len(rooms)}


# ── Room Sync Endpoints ──────────────────────────────────────────────────────

@app.post("/api/rooms/{room_id}/sync")
@rate_limit(max_requests=100, window_seconds=60)
async def sync_playback_endpoint(request: Request, room_id: str, data: SyncPlaybackRequest):
    """Synchronize playback action."""
    from app import room_sync
    
    try:
        sync_state = room_sync.sync_playback(
            room_id=room_id,
            user_id=data.user_id,
            action=data.action,
            timestamp=data.timestamp,
            playback_speed=data.playback_speed
        )
        return {"success": True, "sync_state": sync_state}
    except ValueError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error(f"Error syncing playback: {e}")
        raise HTTPException(500, str(e))


@app.get("/api/rooms/{room_id}/sync")
async def get_sync_state_endpoint(room_id: str):
    """Get current synchronization state."""
    from app import room_sync
    
    try:
        sync_state = room_sync.get_sync_state(room_id)
        return {"success": True, "sync_state": sync_state}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error getting sync state: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/rooms/{room_id}/resync")
@rate_limit(max_requests=20, window_seconds=60)
async def resync_participant_endpoint(request: Request, room_id: str, user_id: int = Query(...)):
    """Resynchronize a participant."""
    from app import room_sync
    
    try:
        sync_state = room_sync.resync_participant(room_id, user_id)
        return {"success": True, "sync_state": sync_state}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error resyncing participant: {e}")
        raise HTTPException(500, str(e))


# ── Room Chat Endpoints ──────────────────────────────────────────────────────

@app.post("/api/rooms/{room_id}/chat")
@rate_limit(max_requests=60, window_seconds=60)
async def send_room_message_endpoint(request: Request, room_id: str, data: SendMessageRequest):
    """Send a message in room chat."""
    from app import watch_rooms
    
    try:
        message = watch_rooms.send_room_message(
            room_id=room_id,
            user_id=data.user_id,
            content=data.content,
            message_type=data.message_type,
            reply_to=data.reply_to
        )
        return {"success": True, "message": message}
    except ValueError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(500, str(e))


@app.get("/api/rooms/{room_id}/chat")
async def get_room_messages_endpoint(
    room_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    before_id: Opt[int] = Query(None)
):
    """Get chat messages from a room."""
    from app import watch_rooms
    
    messages = watch_rooms.get_room_messages(room_id, limit, offset, before_id)
    return {"messages": messages, "count": len(messages)}


@app.delete("/api/rooms/{room_id}/chat/{message_id}")
@rate_limit(max_requests=20, window_seconds=60)
async def delete_room_message_endpoint(
    request: Request,
    room_id: str,
    message_id: int,
    user_id: int = Query(...)
):
    """Delete a chat message."""
    from app import watch_rooms
    
    try:
        success = watch_rooms.delete_room_message(message_id, user_id)
        return {"success": success}
    except ValueError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise HTTPException(500, str(e))


@app.get("/api/rooms/{room_id}/participants")
async def get_room_participants_endpoint(room_id: str):
    """Get all participants in a room."""
    from app import watch_rooms
    
    participants = watch_rooms.get_room_participants(room_id)
    return {"participants": participants, "count": len(participants)}


# ── WebSocket Endpoint ───────────────────────────────────────────────────────

@app.websocket("/ws/rooms/{room_id}")
async def websocket_room_endpoint(websocket: WebSocket, room_id: str, user_id: int = Query(...)):
    """WebSocket endpoint for real-time room communication."""
    from app.websocket_manager import manager, handle_websocket_message
    from app import watch_rooms
    
    # Verify user is in room
    try:
        room = watch_rooms.get_room_details(room_id)
        user_in_room = any(p['user_id'] == user_id for p in room.get('participants', []))
        
        if not user_in_room:
            await websocket.close(code=1008, reason="Not in room")
            return
    except Exception as e:
        logger.error(f"Error verifying room access: {e}")
        await websocket.close(code=1011, reason="Server error")
        return
    
    # Connect to room
    await manager.connect(websocket, room_id, user_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            # Handle message
            await handle_websocket_message(websocket, room_id, user_id, data)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user {user_id} from room {room_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        await manager.disconnect(websocket)


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
