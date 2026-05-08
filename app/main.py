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
from app.cache import cache_get, cache_set, cache_clear_prefix, cache_clear_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
_bot_task = _sync_task = _autoscan_task = None


# ── Backward-compat shims ────────────────────────────────────────────────────
def _cache_get(key: str): return cache_get(key)
def _cache_set(key: str, value, ttl: int): return cache_set(key, value, ttl)
def _cache_clear_prefix(prefix: str): return cache_clear_prefix(prefix)
# ─────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_task, _sync_task, _autoscan_task
    logger.info("🍿 PopCorn v3 starting…")
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

    _sync_task    = asyncio.create_task(_periodic_db_push())
    _autoscan_task = asyncio.create_task(_periodic_autoscan())
    yield

    if _bot_task:      _bot_task.cancel()
    if _sync_task:     _sync_task.cancel()
    if _autoscan_task: _autoscan_task.cancel()
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


async def _periodic_autoscan():
    """Every 2 hours: run a full scan to pick up any new content added to the group."""
    await asyncio.sleep(120)  # Wait 2 minutes after startup before first scan
    while True:
        try:
            from app.stream import _pyro_clients
            from app.scanner import run_full_scan
            if _pyro_clients:
                logger.info("Auto-scan: starting periodic group scan…")
                results = await run_full_scan(_pyro_clients[0])
                logger.info(
                    f"Auto-scan done: topics={results['topics_scanned']} "
                    f"new={results['registered']} files={results['files_attached']} "
                    f"errors={results['errors']}"
                )
            else:
                logger.warning("Auto-scan skipped: no Pyrogram clients available")
        except Exception as e:
            logger.error(f"Auto-scan error: {e}", exc_info=True)
        await asyncio.sleep(7200)  # 2 hours


app = FastAPI(title="PopCorn API 🍿", version="3.3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


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
async def debug_stream_test_ep(file_id: str):
    from app.stream import debug_stream_test
    return await debug_stream_test(file_id)


@app.get("/api/debug/bot-membership")
async def debug_bot_membership():
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


@app.get("/api/search")
async def search(q: str = Query("", min_length=1), limit: int = Query(20)):
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
async def admin_register(payload: dict):
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
async def admin_cache_clear(request: Request):
    """Admin endpoint to manually clear all API cache."""
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    if body.get("admin_id") != ADMIN_ID and str(body.get("admin_id")) != str(ADMIN_ID):
        raise HTTPException(403, "Forbidden")
    cache_clear_all()
    return {"ok": True, "message": "Cache cleared"}


@app.post("/api/admin/fullscan")
async def admin_fullscan(request: Request):
    """Admin endpoint to trigger a full group scan."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    if str(body.get("admin_id", "")) != str(ADMIN_ID):
        raise HTTPException(403, "Forbidden")
    from app.stream import _pyro_clients
    from app.scanner import run_full_scan
    if not _pyro_clients:
        raise HTTPException(503, "No Pyrogram clients available")
    results = await run_full_scan(_pyro_clients[0])
    s = db.get_stats()
    return {"ok": True, "scan": results, "stats": s}


# ── Static frontend ─────────────────────────────────────────────────────────
import os as _os
_static_dir = _os.path.join(_os.path.dirname(__file__), "..", "static")
if _os.path.isdir(_static_dir):
    app.mount("/assets", StaticFiles(directory=_os.path.join(_static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index = _os.path.join(_static_dir, "index.html")
        return FileResponse(index)
