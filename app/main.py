import asyncio, logging, os, json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app import database as db
from app.database import init_db, push_db_to_hf
from app.stream import stream_file, get_stream_info, init_pyrogram, stop_pyrogram
from app.config import MAIN_BOT_TOKEN, ADMIN_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_bot_task = _sync_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_task, _sync_task
    logger.info("🍿 PopCorn starting…")
    init_db()
    await init_pyrogram()

    if MAIN_BOT_TOKEN:
        try:
            from app.sync_bot import build_sync_app
            from app.bot_commands import cmd_start, cmd_app, cmd_admin
            from telegram.ext import CommandHandler
            bot_app = build_sync_app()
            bot_app.add_handler(CommandHandler("start", cmd_start))
            bot_app.add_handler(CommandHandler("app",   cmd_app))
            bot_app.add_handler(CommandHandler("admin", cmd_admin))
            _bot_task = asyncio.create_task(_run_bot(bot_app))
            logger.info("✅ Telegram bot started (polling)")
        except Exception as e:
            logger.error(f"Bot start error: {e}")

    _sync_task = asyncio.create_task(_periodic_sync())
    yield

    if _bot_task:   _bot_task.cancel()
    if _sync_task:  _sync_task.cancel()
    await stop_pyrogram()


async def _run_bot(bot_app):
    try:
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=False, allowed_updates=[
            "message", "edited_message", "callback_query",
        ])
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        try:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
        except Exception:
            pass


async def _periodic_sync():
    while True:
        await asyncio.sleep(600)
        try:
            push_db_to_hf()
        except Exception as e:
            logger.error(f"Periodic sync error: {e}")


app = FastAPI(title="PopCorn API 🍿", version="2.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    from app.stream import _pyro_clients
    return {"status": "ok", "service": "PopCorn API 🍿", "pyrogram": bool(_pyro_clients)}


# ── Stats ──────────────────────────────────────────────────────────────────────
@app.get("/api/stats")
async def stats():
    return db.get_stats()


# ── Featured ───────────────────────────────────────────────────────────────────
@app.get("/api/featured")
async def featured():
    conn = __import__('sqlite3').connect(__import__('app.config', fromlist=['DB_PATH']).DB_PATH)
    conn.row_factory = __import__('sqlite3').Row
    try:
        movies = [dict(r) for r in conn.execute(
            "SELECT id,'movie' as type,title,title_ar,poster_path,backdrop_path,rating,release_date as date "
            "FROM movies WHERE backdrop_path!='' AND file_id IS NOT NULL ORDER BY rating DESC LIMIT 8"
        ).fetchall()]
        series = [dict(r) for r in conn.execute(
            "SELECT id,'series' as type,title,title_ar,poster_path,backdrop_path,rating,first_air_date as date "
            "FROM series WHERE backdrop_path!='' ORDER BY rating DESC LIMIT 4"
        ).fetchall()]
        return {"items": (movies + series)[:10]}
    finally:
        conn.close()


# ── Movies ─────────────────────────────────────────────────────────────────────
@app.get("/api/movies")
async def list_movies(
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    genre: str = Query(None),
    search: str = Query(None),
    has_file: bool = Query(None),
):
    import sqlite3 as sq
    from app.config import DB_PATH
    conn = sq.connect(DB_PATH)
    conn.row_factory = sq.Row
    try:
        q = "SELECT * FROM movies WHERE 1=1"
        p: list = []
        if genre:
            q += " AND genres LIKE ?"; p.append(f"%{genre}%")
        if search:
            q += " AND (title LIKE ? OR title_ar LIKE ?)"; p += [f"%{search}%"] * 2
        if has_file is True:
            q += " AND file_id IS NOT NULL"
        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        p += [limit, offset]
        rows = [dict(r) for r in conn.execute(q, p).fetchall()]
        total = conn.execute(q.replace("SELECT *","SELECT COUNT(*)").split("LIMIT")[0], p[:-2]).fetchone()[0]
    finally:
        conn.close()
    for m in rows:
        _j(m, ["genres", "cast"])
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@app.get("/api/movies/{movie_id}")
async def get_movie(movie_id: str):
    m = db.get_movie(movie_id=movie_id)
    if not m:
        raise HTTPException(404, "Movie not found")
    _j(m, ["genres", "cast"])
    if m.get("file_id"):
        m["stream_info"] = await get_stream_info(m["file_id"])
    return m


# ── Series ─────────────────────────────────────────────────────────────────────
@app.get("/api/series")
async def list_series(
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    genre: str = Query(None),
    search: str = Query(None),
):
    import sqlite3 as sq
    from app.config import DB_PATH
    conn = sq.connect(DB_PATH)
    conn.row_factory = sq.Row
    try:
        q = "SELECT * FROM series WHERE 1=1"
        p: list = []
        if genre:
            q += " AND genres LIKE ?"; p.append(f"%{genre}%")
        if search:
            q += " AND (title LIKE ? OR title_ar LIKE ?)"; p += [f"%{search}%"] * 2
        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        p += [limit, offset]
        rows = [dict(r) for r in conn.execute(q, p).fetchall()]
        total = conn.execute(q.replace("SELECT *","SELECT COUNT(*)").split("LIMIT")[0], p[:-2]).fetchone()[0]
    finally:
        conn.close()
    for s in rows:
        _j(s, ["genres", "cast"])
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@app.get("/api/series/{series_id}")
async def get_series(series_id: str):
    s = db.get_series(series_id=series_id)
    if not s:
        raise HTTPException(404, "Series not found")
    _j(s, ["genres", "cast"])
    episodes = db.get_episodes(series_id)
    seasons: dict[int, list] = {}
    for ep in episodes:
        sn = ep["season_number"]
        seasons.setdefault(sn, []).append(ep)
    s["seasons"] = seasons
    return s


@app.get("/api/series/{series_id}/episodes")
async def series_episodes(series_id: str, season: int = Query(None)):
    return {"items": db.get_episodes(series_id, season_number=season)}


# ── Stream ─────────────────────────────────────────────────────────────────────
@app.get("/api/stream/{file_id:path}")
async def stream_video(file_id: str, request: Request):
    return await stream_file(file_id, request)


@app.get("/api/stream-info/{file_id:path}")
async def stream_info(file_id: str):
    info = await get_stream_info(file_id)
    return info


# ── Search ─────────────────────────────────────────────────────────────────────
@app.get("/api/search")
async def search(q: str = Query("", min_length=1), limit: int = Query(20)):
    movies = db.get_movies(limit=limit, search=q)
    series = db.get_series_list(limit=limit, search=q)
    for m in movies: _j(m, ["genres", "cast"])
    for s in series: _j(s, ["genres", "cast"])
    return {"movies": movies, "series": series}


# ── Admin ──────────────────────────────────────────────────────────────────────
@app.post("/api/admin/register_topic")
async def admin_register(payload: dict):
    from app.sync_bot import register_topic, parse_topic_name, _map_topic_to_series
    name = payload.get("topic_name", "")
    tid  = int(payload.get("topic_id", 0))
    ok   = await register_topic(name, tid)
    parsed = parse_topic_name(name)
    if parsed and parsed["type"] == "series":
        _map_topic_to_series(tid, parsed["internal_id"])
    return {"ok": ok}


@app.post("/api/admin/sync_db")
async def admin_sync():
    push_db_to_hf()
    return {"ok": True}


@app.post("/api/admin/bulk_register")
async def admin_bulk(payload: dict):
    """Register multiple topics at once."""
    topics = payload.get("topics", [])
    results = []
    for t in topics:
        from app.sync_bot import register_topic, parse_topic_name, _map_topic_to_series
        ok = await register_topic(t["topic_name"], t["topic_id"])
        parsed = parse_topic_name(t["topic_name"])
        if parsed and parsed["type"] == "series":
            _map_topic_to_series(t["topic_id"], parsed["internal_id"])
        results.append({"topic": t["topic_name"], "ok": ok})
    push_db_to_hf()
    return {"results": results}


# ── Frontend SPA ───────────────────────────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

if os.path.isdir(STATIC_DIR):
    _assets = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}")
    async def spa(_: str):
        idx = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(idx) if os.path.isfile(idx) else JSONResponse({"error": "Frontend not built"}, 503)
else:
    @app.get("/")
    async def root():
        return {"message": "🍿 PopCorn API v2 running"}


def _j(obj: dict, fields: list[str]):
    for f in fields:
        if isinstance(obj.get(f), str):
            try: obj[f] = json.loads(obj[f])
            except Exception: obj[f] = []
