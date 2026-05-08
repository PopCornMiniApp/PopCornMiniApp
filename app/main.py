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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
_bot_task = _sync_task = None

# ── Simple in-memory cache ────────────────────────────────────────────────────
_cache: dict[str, tuple[float, any]] = {}

def _cache_get(key: str) -> any:
    entry = _cache.get(key)
    if entry and time.time() < entry[0]:
        return entry[1]
    return None

def _cache_set(key: str, value: any, ttl: int):
    _cache[key] = (time.time() + ttl, value)

def _cache_clear_prefix(prefix: str):
    for k in list(_cache.keys()):
        if k.startswith(prefix):
            del _cache[k]
# ─────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_task, _sync_task
    logger.info("🍿 PopCorn v3 starting…")
    init_db()
    await init_pyrogram()
    if MAIN_BOT_TOKEN:
        try:
            from app.sync_bot import build_sync_app
            from app.bot_commands import cmd_start, cmd_app, cmd_help, cmd_new, cmd_top, cmd_stats, cmd_admin
            from telegram.ext import CommandHandler
            bot_app = build_sync_app()
            bot_app.add_handler(CommandHandler("start",    cmd_start))
            bot_app.add_handler(CommandHandler("app",      cmd_app))
            bot_app.add_handler(CommandHandler("help",     cmd_help))
            bot_app.add_handler(CommandHandler("new",      cmd_new))
            bot_app.add_handler(CommandHandler("top",      cmd_top))
            bot_app.add_handler(CommandHandler("stats",    cmd_stats))
            bot_app.add_handler(CommandHandler("admin",    cmd_admin))
            bot_app.add_handler(CommandHandler("sync_db",  _cmd_sync_db))
            _bot_task = asyncio.create_task(_run_bot(bot_app))
            logger.info("✅ Telegram bot started")
        except Exception as e:
            logger.error(f"Bot start error: {e}")
    _sync_task = asyncio.create_task(_periodic_sync())
    yield
    if _bot_task: _bot_task.cancel()
    if _sync_task: _sync_task.cancel()
    await stop_pyrogram()


async def _cmd_sync_db(update, context):
    if update.effective_user.id != ADMIN_ID: return
    push_db_to_hf()
    await update.effective_message.reply_text("✅ تمت المزامنة مع HuggingFace!")


async def _run_bot(bot_app):
    try:
        await bot_app.initialize(); await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=False,
            allowed_updates=["message", "edited_message", "callback_query"])
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
            _cache_clear_prefix("featured")
            _cache_clear_prefix("genres")
        except Exception as e:
            logger.error(f"Periodic sync error: {e}")


app = FastAPI(title="PopCorn API 🍿", version="3.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
async def health():
    from app.stream import _pyro_clients
    return {"status": "ok", "service": "PopCorn API 🍿", "pyrogram": bool(_pyro_clients),
            "pyrogram_clients": len(_pyro_clients)}


@app.get("/api/stats")
async def stats():
    cached = _cache_get("stats")
    if cached is not None:
        return cached
    result = db.get_stats()
    _cache_set("stats", result, 60)
    return result


@app.get("/api/genres")
async def genres():
    cached = _cache_get("genres")
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
    _cache_set("genres", result, 600)
    return result


@app.get("/api/featured")
async def featured():
    cached = _cache_get("featured")
    if cached is not None:
        return cached
    import sqlite3 as sq
    from app.config import DB_PATH
    conn = sq.connect(DB_PATH); conn.row_factory = sq.Row
    try:
        movies = [dict(r) for r in conn.execute(
            "SELECT id,'movie' AS type,title,title_ar,poster_path,backdrop_path,rating,release_date AS date,overview,overview_ar,genres "
            "FROM movies WHERE backdrop_path!='' AND file_id IS NOT NULL ORDER BY rating DESC LIMIT 8"
        ).fetchall()]
        series = [dict(r) for r in conn.execute(
            "SELECT id,'series' AS type,title,title_ar,poster_path,backdrop_path,rating,first_air_date AS date,overview,overview_ar,genres "
            "FROM series WHERE backdrop_path!='' ORDER BY rating DESC LIMIT 4"
        ).fetchall()]
        items = (movies + series)[:12]
        for it in items:
            _j(it, ["genres"])
    finally:
        conn.close()
    result = {"items": items}
    _cache_set("featured", result, 300)
    return result


@app.get("/api/movies")
async def list_movies(
    limit: int = Query(24, ge=1, le=100), offset: int = Query(0, ge=0),
    genre: str = Query(None), search: str = Query(None),
    has_file: bool = Query(None), sort: str = Query("newest"),
):
    cache_key = f"movies:{limit}:{offset}:{genre}:{search}:{has_file}:{sort}"
    cached = _cache_get(cache_key)
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
    for m in rows: _j(m, ["genres", "cast"])
    result = {"items": rows, "total": total, "limit": limit, "offset": offset}
    ttl = 30 if search else 60
    _cache_set(cache_key, result, ttl)
    return result


@app.get("/api/movies/{movie_id}")
async def get_movie(movie_id: str):
    cache_key = f"movie:{movie_id}"
    cached = _cache_get(cache_key)
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
    _cache_set(cache_key, m, 120)
    return m


@app.get("/api/series")
async def list_series(
    limit: int = Query(24, ge=1, le=100), offset: int = Query(0, ge=0),
    genre: str = Query(None), search: str = Query(None), sort: str = Query("newest"),
):
    cache_key = f"series_list:{limit}:{offset}:{genre}:{search}:{sort}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    import sqlite3 as sq
    from app.config import DB_PATH
    conn = sq.connect(DB_PATH); conn.row_factory = sq.Row
    try:
        q = "SELECT * FROM series WHERE 1=1"; p: list = []
        if genre: q += " AND genres LIKE ?"; p.append(f"%{genre}%")
        if search:
            term = f"%{search}%"
            q += " AND (title LIKE ? OR title_ar LIKE ? OR LOWER(title) LIKE LOWER(?) OR LOWER(title_ar) LIKE LOWER(?))"
            p += [term, term, term, term]
        order = {"newest": "created_at DESC", "rating": "rating DESC", "title": "title_ar ASC"}.get(sort, "created_at DESC")
        count_q = q.replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_q, p).fetchone()[0]
        q += f" ORDER BY {order} LIMIT ? OFFSET ?"; p += [limit, offset]
        rows = [dict(r) for r in conn.execute(q, p).fetchall()]
    finally:
        conn.close()
    for s in rows: _j(s, ["genres", "cast"])
    result = {"items": rows, "total": total, "limit": limit, "offset": offset}
    _cache_set(cache_key, result, 60)
    return result


@app.get("/api/series/{series_id}")
async def get_series(series_id: str):
    cache_key = f"series:{series_id}"
    cached = _cache_get(cache_key)
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
    _cache_set(cache_key, s, 120)
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


@app.get("/api/stream-info/{file_id:path}")
async def stream_info_ep(file_id: str):
    return await get_stream_info(file_id)


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
            "SELECT * FROM series WHERE title LIKE ? OR title_ar LIKE ? OR LOWER(title) LIKE LOWER(?) OR LOWER(title_ar) LIKE LOWER(?) ORDER BY rating DESC LIMIT ?",
            [term, term, term, term, limit]).fetchall()]
    finally:
        conn.close()
    for m in movies: _j(m, ["genres", "cast"])
    for s in series: _j(s, ["genres", "cast"])
    return {"movies": movies, "series": series, "query": q}


@app.post("/api/admin/register_topic")
async def admin_register(payload: dict):
    from app.sync_bot import register_topic, parse_topic_name, _map_topic_to_series
    name = payload.get("topic_name", ""); tid = int(payload.get("topic_id", 0))
    ok = await register_topic(name, tid)
    parsed = parse_topic_name(name)
    if parsed and parsed["type"] == "series":
        _map_topic_to_series(tid, parsed["internal_id"])
    _cache_clear_prefix("series"); _cache_clear_prefix("featured")
    return {"ok": ok}


@app.post("/api/admin/sync_db")
async def admin_sync():
    push_db_to_hf()
    _cache.clear()
    return {"ok": True}


@app.post("/api/admin/bulk_register")
async def admin_bulk(payload: dict):
    topics = payload.get("topics", []); results = []
    for t in topics:
        from app.sync_bot import register_topic, parse_topic_name, _map_topic_to_series
        ok = await register_topic(t["topic_name"], t["topic_id"])
        parsed = parse_topic_name(t["topic_name"])
        if parsed and parsed["type"] == "series":
            _map_topic_to_series(t["topic_id"], parsed["internal_id"])
        results.append({"topic": t["topic_name"], "ok": ok})
    push_db_to_hf()
    _cache.clear()
    return {"results": results}


@app.post("/api/admin/bulk_update_fileids")
async def admin_bulk_update_fileids(payload: dict):
    from app.config import DB_PATH
    import sqlite3 as sq
    movies = payload.get("movies", {}); episodes = payload.get("episodes", {})
    conn = sq.connect(DB_PATH); mu = eu = 0
    try:
        for mid, d in movies.items():
            conn.execute(
                "UPDATE movies SET file_id=?,file_size=?,duration=?,message_id=?,updated_at=datetime('now') WHERE id=?",
                (d["file_id"], d.get("file_size", 0), d.get("duration", 0), d.get("message_id", 0), mid))
            mu += 1
        for _, d in episodes.items():
            conn.execute("""INSERT INTO episodes (series_id,season_number,episode_number,file_id,file_size,duration,message_id,topic_id)
                VALUES (?,?,?,?,?,?,?,0) ON CONFLICT(series_id,season_number,episode_number) DO UPDATE SET
                file_id=excluded.file_id,file_size=excluded.file_size,duration=excluded.duration,message_id=excluded.message_id""",
                (d["series_id"], d["season"], d["ep"], d["file_id"], d.get("file_size", 0), d.get("duration", 0), d.get("message_id", 0)))
            eu += 1
        conn.commit()
    finally:
        conn.close()
    push_db_to_hf()
    _cache.clear()
    return {"ok": True, "movies_updated": mu, "episodes_updated": eu}


@app.post("/api/admin/scan_file_ids")
async def admin_scan_file_ids():
    from app.config import PRIVATE_GROUP_ID, DB_PATH
    from app.stream import _pyro_clients
    import sqlite3 as sq, asyncio as aio
    if not _pyro_clients: raise HTTPException(503, "Pyrogram not available")
    GROUP_ID = PRIVATE_GROUP_ID or -1003826837517; pyro = _pyro_clients[0]
    MOVIE_MSGS = {
        'mid00001': 4713, 'mid00002': 4715, 'mid00003': 4717, 'mid00004': 4719, 'mid00005': 4721,
        'mid00006': 4723, 'mid00007': 4726, 'mid00008': 4728, 'mid00009': 4730, 'mid00010': 4733,
        'mid00011': 4735, 'mid00012': 4737, 'mid00013': 4739, 'mid00014': 4742, 'mid00015': 4744,
        'mid00016': 4746, 'mid00017': 4748, 'mid00018': 4750, 'mid00019': 4752, 'mid00020': 4847,
        'mid00021': 4849, 'mid00022': 4852,
    }
    EPISODE_MSGS = {}
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
    all_ids = list(set(MOVIE_MSGS.values()) | set(EPISODE_MSGS.values()))
    msg_data = {}

    async def fetch_one(mid):
        try:
            msg = await pyro.get_messages(GROUP_ID, mid)
            media = msg.video or msg.document or msg.audio
            if media:
                msg_data[mid] = {
                    "file_id": media.file_id,
                    "file_size": getattr(media, "file_size", 0) or 0,
                    "duration": getattr(media, "duration", 0) or 0,
                }
        except Exception as e:
            logger.warning(f"fetch {mid}: {e}")

    for i in range(0, len(all_ids), 10):
        await aio.gather(*[fetch_one(m) for m in all_ids[i:i+10]])
        await aio.sleep(0.3)

    conn = sq.connect(DB_PATH); mu = eu = 0
    try:
        for mid, msg_id in MOVIE_MSGS.items():
            if msg_id in msg_data:
                d = msg_data[msg_id]
                conn.execute(
                    "UPDATE movies SET file_id=?,file_size=?,duration=?,message_id=?,updated_at=datetime('now') WHERE id=?",
                    (d["file_id"], d["file_size"], d["duration"], msg_id, mid))
                mu += 1
        for (sid, season, ep), msg_id in EPISODE_MSGS.items():
            if msg_id in msg_data:
                d = msg_data[msg_id]
                conn.execute("""INSERT INTO episodes (series_id,season_number,episode_number,file_id,file_size,duration,message_id,topic_id)
                    VALUES (?,?,?,?,?,?,?,0) ON CONFLICT(series_id,season_number,episode_number) DO UPDATE SET
                    file_id=excluded.file_id,file_size=excluded.file_size,duration=excluded.duration,message_id=excluded.message_id""",
                    (sid, season, ep, d["file_id"], d["file_size"], d["duration"], msg_id))
                eu += 1
        conn.commit()
    finally:
        conn.close()
    push_db_to_hf()
    _cache.clear()
    return {"ok": True, "messages_found": len(msg_data), "movies_updated": mu, "episodes_updated": eu}


STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(STATIC_DIR):
    _assets = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        idx = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(idx) if os.path.isfile(idx) else JSONResponse({"error": "Frontend not built"}, status_code=503)
else:
    @app.get("/")
    async def root():
        return {"message": "🍿 PopCorn API v3 running"}


def _j(obj: dict, fields: list):
    for f in fields:
        if isinstance(obj.get(f), str):
            try:
                obj[f] = json.loads(obj[f])
            except Exception:
                obj[f] = []
