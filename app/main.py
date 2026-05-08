import asyncio
import logging
import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app import database as db
from app.database import init_db, push_db_to_hf
from app.stream import stream_file, get_stream_info
from app.config import MAIN_BOT_TOKEN, ADMIN_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

_bot_task = None
_scheduler_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_task, _scheduler_task
    logger.info("🍿 Starting PopCorn API...")
    init_db()

    if MAIN_BOT_TOKEN:
        try:
            from app.sync_bot import build_sync_app
            from app.bot_commands import cmd_start, cmd_app, cmd_admin
            from telegram.ext import CommandHandler
            bot_app = build_sync_app()
            bot_app.add_handler(CommandHandler("start", cmd_start))
            bot_app.add_handler(CommandHandler("app", cmd_app))
            bot_app.add_handler(CommandHandler("admin", cmd_admin))
            _bot_task = asyncio.create_task(_run_bot(bot_app))
            logger.info("✅ Telegram bot started.")
        except Exception as e:
            logger.error(f"Bot start error: {e}")

    _scheduler_task = asyncio.create_task(_periodic_db_sync())

    yield

    if _bot_task:
        _bot_task.cancel()
    if _scheduler_task:
        _scheduler_task.cancel()
    logger.info("PopCorn API shutdown.")


async def _run_bot(bot_app):
    try:
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        try:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
        except Exception:
            pass


async def _periodic_db_sync():
    """Push DB to HF every 10 minutes."""
    while True:
        await asyncio.sleep(600)
        try:
            push_db_to_hf()
        except Exception as e:
            logger.error(f"Periodic DB sync error: {e}")


app = FastAPI(
    title="PopCorn API",
    description="🍿 Movies & Series Telegram Mini App API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "PopCorn API 🍿"}


# ─── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def stats():
    return db.get_stats()


# ─── Movies ────────────────────────────────────────────────────────────────────

@app.get("/api/movies")
async def list_movies(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    genre: str = Query(None),
    search: str = Query(None),
):
    movies = db.get_movies(limit=limit, offset=offset, genre=genre, search=search)
    for m in movies:
        _parse_json_fields(m, ["genres", "cast"])
    return {"items": movies, "limit": limit, "offset": offset}


@app.get("/api/movies/{movie_id}")
async def get_movie(movie_id: str):
    movie = db.get_movie(movie_id=movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")
    _parse_json_fields(movie, ["genres", "cast"])
    if movie.get("file_id"):
        movie["stream_info"] = await get_stream_info(movie["file_id"])
    return movie


# ─── Series ────────────────────────────────────────────────────────────────────

@app.get("/api/series")
async def list_series(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    genre: str = Query(None),
    search: str = Query(None),
):
    series = db.get_series_list(limit=limit, offset=offset, genre=genre, search=search)
    for s in series:
        _parse_json_fields(s, ["genres", "cast"])
    return {"items": series, "limit": limit, "offset": offset}


@app.get("/api/series/{series_id}")
async def get_series(series_id: str):
    series = db.get_series(series_id=series_id)
    if not series:
        raise HTTPException(404, "Series not found")
    _parse_json_fields(series, ["genres", "cast"])
    episodes = db.get_episodes(series_id)
    seasons: dict[int, list] = {}
    for ep in episodes:
        s = ep["season_number"]
        if s not in seasons:
            seasons[s] = []
        seasons[s].append(ep)
    series["seasons"] = seasons
    return series


@app.get("/api/series/{series_id}/episodes")
async def get_series_episodes(series_id: str, season: int = Query(None)):
    episodes = db.get_episodes(series_id, season_number=season)
    return {"items": episodes}


# ─── Stream ────────────────────────────────────────────────────────────────────

@app.get("/api/stream/{file_id:path}")
async def stream_video(file_id: str, request: Request):
    return await stream_file(file_id, request)


@app.get("/api/stream-info/{file_id:path}")
async def stream_info_ep(file_id: str):
    info = await get_stream_info(file_id)
    if not info.get("direct_url"):
        raise HTTPException(404, "File not accessible via Bot API")
    return info


# ─── Admin ─────────────────────────────────────────────────────────────────────

@app.post("/api/admin/register_topic")
async def api_register_topic(payload: dict):
    from app.sync_bot import register_topic
    topic_name = payload.get("topic_name", "")
    topic_id = payload.get("topic_id", 0)
    ok = await register_topic(topic_name, topic_id)
    return {"ok": ok}


@app.post("/api/admin/sync_db")
async def api_sync_db():
    push_db_to_hf()
    return {"ok": True, "message": "✅ Database synced to HuggingFace"}


# ─── Frontend SPA ──────────────────────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

if os.path.isdir(STATIC_DIR):
    _assets = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse({"error": "Frontend not built"}, status_code=503)
else:
    @app.get("/")
    async def root():
        return {"message": "🍿 PopCorn API is running!"}


def _parse_json_fields(obj: dict, fields: list[str]):
    for f in fields:
        if isinstance(obj.get(f), str):
            try:
                obj[f] = json.loads(obj[f])
            except Exception:
                obj[f] = []
