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


@app.post("/api/admin/scan_file_ids")
async def admin_scan_file_ids():
    """Use Bot API forward_message to extract file_ids from all known historical messages.
    forward_message returns a full Message object including video.file_id.
    """
    from telegram import Bot
    from app.config import MAIN_BOT_TOKEN, ADMIN_ID, PRIVATE_GROUP_ID, DB_PATH
    import sqlite3 as sq
    import asyncio as aio

    GROUP_ID = PRIVATE_GROUP_ID or -1003826837517

    MOVIE_MSGS: dict[str, int] = {
        'mid00001': 4713, 'mid00002': 4715, 'mid00003': 4717,
        'mid00004': 4719, 'mid00005': 4721, 'mid00006': 4723,
        'mid00007': 4726, 'mid00008': 4728, 'mid00009': 4730,
        'mid00010': 4733, 'mid00011': 4735, 'mid00012': 4737,
        'mid00013': 4739, 'mid00014': 4742, 'mid00015': 4744,
        'mid00016': 4746, 'mid00017': 4748, 'mid00018': 4750,
        'mid00019': 4752, 'mid00020': 4847, 'mid00021': 4849,
        'mid00022': 4852,
    }

    EPISODE_MSGS: dict[tuple, int] = {}
    for msg_id, ep_num, season, series_id in [
        (4660,1,1,'sid00001'),(4661,2,1,'sid00001'),(4662,3,1,'sid00001'),(4663,4,1,'sid00001'),(4664,5,1,'sid00001'),
        (4675,1,2,'sid00001'),(4676,2,2,'sid00001'),(4677,3,2,'sid00001'),(4678,4,2,'sid00001'),(4679,5,2,'sid00001'),
        (4680,6,2,'sid00001'),(4681,7,2,'sid00001'),(4682,8,2,'sid00001'),(4683,9,2,'sid00001'),
        (4685,1,3,'sid00001'),(4686,2,3,'sid00001'),(4687,3,3,'sid00001'),(4688,4,3,'sid00001'),(4689,5,3,'sid00001'),
        (4690,6,3,'sid00001'),(4691,7,3,'sid00001'),(4692,8,3,'sid00001'),
        (4694,1,4,'sid00001'),(4695,2,4,'sid00001'),(4696,3,4,'sid00001'),(4697,4,4,'sid00001'),(4698,5,4,'sid00001'),
        (4699,6,4,'sid00001'),(4700,7,4,'sid00001'),(4701,8,4,'sid00001'),(4702,9,4,'sid00001'),
        (4704,1,5,'sid00001'),(4705,2,5,'sid00001'),(4706,3,5,'sid00001'),(4707,4,5,'sid00001'),(4708,5,5,'sid00001'),
        (4709,6,5,'sid00001'),(4710,7,5,'sid00001'),(4711,8,5,'sid00001'),
        (4802,1,1,'sid00002'),(4803,2,1,'sid00002'),(4804,3,1,'sid00002'),(4805,4,1,'sid00002'),(4806,5,1,'sid00002'),
        (4808,1,1,'sid00003'),(4809,2,1,'sid00003'),(4810,3,1,'sid00003'),(4811,4,1,'sid00003'),
        (4812,5,1,'sid00003'),(4813,6,1,'sid00003'),(4814,7,1,'sid00003'),(4815,8,1,'sid00003'),
        (4817,1,2,'sid00003'),(4818,2,2,'sid00003'),(4819,3,2,'sid00003'),(4820,4,2,'sid00003'),
        (4821,5,2,'sid00003'),(4822,6,2,'sid00003'),(4823,7,2,'sid00003'),(4824,8,2,'sid00003'),
        (4827,1,3,'sid00003'),(4828,2,3,'sid00003'),(4829,3,3,'sid00003'),(4830,4,3,'sid00003'),
        (4831,5,3,'sid00003'),(4832,6,3,'sid00003'),(4833,7,3,'sid00003'),(4834,8,3,'sid00003'),
        (4836,1,4,'sid00003'),(4837,2,4,'sid00003'),(4838,3,4,'sid00003'),(4839,4,4,'sid00003'),
        (4840,5,4,'sid00003'),(4841,6,4,'sid00003'),(4842,7,4,'sid00003'),(4843,8,4,'sid00003'),
        (4844,9,4,'sid00003'),(4845,10,4,'sid00003'),
    ]:
        EPISODE_MSGS[(series_id, season, ep_num)] = msg_id

    bot = Bot(token=MAIN_BOT_TOKEN)
    # Use ADMIN_ID as dump destination — forward returns full Message with file_id
    DUMP_CHAT = ADMIN_ID if ADMIN_ID else GROUP_ID

    msg_data: dict[int, dict] = {}

    async def forward_one(msg_id: int):
        try:
            m = await bot.forward_message(
                chat_id=DUMP_CHAT,
                from_chat_id=GROUP_ID,
                message_id=msg_id,
                protect_content=False,
            )
            media = m.video or m.document or m.audio
            if media:
                msg_data[msg_id] = {
                    "file_id": media.file_id,
                    "file_size": getattr(media, "file_size", 0) or 0,
                    "duration": getattr(media, "duration", 0) or 0,
                }
                logger.info(f"Got file_id for msg {msg_id}: {media.file_id[:20]}...")
        except Exception as e:
            logger.warning(f"forward msg {msg_id} failed: {e}")

    all_movie_ids  = list(MOVIE_MSGS.values())
    all_episode_ids = list(EPISODE_MSGS.values())

    # Forward movies in chunks (respect rate limit)
    for i in range(0, len(all_movie_ids), 5):
        chunk = all_movie_ids[i:i+5]
        await aio.gather(*[forward_one(mid) for mid in chunk])
        await aio.sleep(0.5)

    for i in range(0, len(all_episode_ids), 5):
        chunk = all_episode_ids[i:i+5]
        await aio.gather(*[forward_one(mid) for mid in chunk])
        await aio.sleep(0.5)

    conn = sq.connect(DB_PATH)
    movies_updated = episodes_updated = 0
    try:
        for movie_id, msg_id in MOVIE_MSGS.items():
            if msg_id in msg_data:
                d = msg_data[msg_id]
                conn.execute(
                    "UPDATE movies SET file_id=?, file_size=?, duration=?, message_id=?, updated_at=datetime('now') WHERE id=?",
                    (d["file_id"], d["file_size"], d["duration"], msg_id, movie_id)
                )
                movies_updated += 1

        for (series_id, season, ep_num), msg_id in EPISODE_MSGS.items():
            if msg_id in msg_data:
                d = msg_data[msg_id]
                conn.execute("""
                    INSERT INTO episodes (series_id, season_number, episode_number, file_id, file_size, duration, message_id, topic_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    ON CONFLICT(series_id, season_number, episode_number) DO UPDATE SET
                        file_id=excluded.file_id, file_size=excluded.file_size,
                        duration=excluded.duration, message_id=excluded.message_id
                """, (series_id, season, ep_num, d["file_id"], d["file_size"], d["duration"], msg_id))
                episodes_updated += 1
        conn.commit()
    finally:
        conn.close()

    push_db_to_hf()
    return {
        "ok": True,
        "messages_found": len(msg_data),
        "movies_updated": movies_updated,
        "episodes_updated": episodes_updated,
    }


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
