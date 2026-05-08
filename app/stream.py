import asyncio, logging, os, sqlite3, httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from app.config import STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN, SESSION_1_API_ID, SESSION_1_API_HASH, DB_PATH

logger = logging.getLogger(__name__)
BOT_TOKENS = [t for t in [STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN] if t]
_current_bot = 0
_pyro_clients: list = []

def _lookup_file_size(file_id: str) -> int:
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT file_size FROM movies WHERE file_id=? LIMIT 1",(file_id,)).fetchone()
        if not row: row = conn.execute("SELECT file_size FROM episodes WHERE file_id=? LIMIT 1",(file_id,)).fetchone()
        conn.close()
        return int(row[0]) if row and row[0] else 0
    except: return 0

def _get_pyro_client():
    if not _pyro_clients: return None
    return _pyro_clients[_current_bot % len(_pyro_clients)]

async def init_pyrogram():
    global _pyro_clients
    if not SESSION_1_API_ID:
        logger.warning("No Pyrogram API credentials"); return
    try:
        from pyrogram import Client
        tokens = [t for t in [STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN] if t]
        for i, token in enumerate(tokens[:2]):
            try:
                client = Client(name=f"stream_{i}", bot_token=token, api_id=SESSION_1_API_ID,
                    api_hash=SESSION_1_API_HASH, no_updates=True, workdir="/tmp")
                await client.start(); _pyro_clients.append(client)
                logger.info(f"✅ Pyrogram client {i} started")
            except Exception as e: logger.error(f"Pyrogram client {i} failed: {e}")
    except ImportError: logger.warning("Pyrogram not installed")

async def stop_pyrogram():
    for client in _pyro_clients:
        try: await client.stop()
        except: pass

async def stream_via_pyrogram(file_id: str, request: Request, file_size: int = 0) -> Response:
    pyro = _get_pyro_client()
    if not pyro: return Response(status_code=503, content="Pyrogram not available")
    try:
        range_header = request.headers.get("range","")
        start = 0; end = (file_size - 1) if file_size > 0 else None
        if range_header and range_header.lower().startswith("bytes="):
            parts = range_header[6:].split("-")
            start = int(parts[0]) if parts[0] else 0
            if len(parts) > 1 and parts[1]: end = int(parts[1])
            elif file_size > 0: end = file_size - 1
        CHUNK_SIZE = 1024 * 1024
        chunk_index = start // CHUNK_SIZE; skip_in_first = start % CHUNK_SIZE
        async def generate():
            first = True; bytes_sent = 0
            limit = (end - start + 1) if (end is not None and file_size > 0) else None
            async for chunk in pyro.stream_media(file_id, offset=chunk_index):
                if first and skip_in_first: chunk = chunk[skip_in_first:]; first = False
                if limit is not None:
                    if bytes_sent + len(chunk) >= limit: yield chunk[:limit - bytes_sent]; break
                    bytes_sent += len(chunk)
                yield chunk
        headers: dict = {"Accept-Ranges":"bytes","Content-Disposition":"inline","Cache-Control":"no-cache"}
        if file_size > 0:
            content_length = (end - start + 1) if end is not None else (file_size - start)
            end_str = str(end) if end is not None else str(file_size - 1)
            headers["Content-Length"] = str(content_length)
            if range_header: headers["Content-Range"] = f"bytes {start}-{end_str}/{file_size}"
        return StreamingResponse(generate(), status_code=206 if range_header else 200, headers=headers, media_type="video/mp4")
    except Exception as e:
        logger.error(f"Pyrogram stream error: {e}")
        return Response(status_code=500, content=f"Stream error: {e}")

async def stream_via_botapi(file_id: str, request: Request) -> Response:
    token = BOT_TOKENS[_current_bot % len(BOT_TOKENS)] if BOT_TOKENS else ""
    data: dict = {}
    for try_token in ([token] + [t for t in BOT_TOKENS if t != token]):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"https://api.telegram.org/bot{try_token}/getFile", params={"file_id":file_id})
                data = r.json()
                if data.get("ok") and data["result"].get("file_path"): token = try_token; break
        except: continue
    if not data.get("ok") or not data["result"].get("file_path"):
        return Response(status_code=404, content="File not accessible via Bot API (>20MB requires Pyrogram)")
    file_path = data["result"]["file_path"]; file_size = data["result"].get("file_size",0)
    direct_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    range_header = request.headers.get("range","")
    async def stream_gen():
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("GET", direct_url, headers={"Range":range_header} if range_header else {}) as resp:
                async for chunk in resp.aiter_bytes(65536): yield chunk
    resp_headers: dict = {"Accept-Ranges":"bytes","Content-Disposition":"inline"}
    if file_size: resp_headers["Content-Length"] = str(file_size)
    return StreamingResponse(stream_gen(), status_code=206 if range_header else 200, headers=resp_headers, media_type="video/mp4")

async def stream_file(file_id: str, request: Request, file_size: int = 0) -> Response:
    if not file_size: file_size = _lookup_file_size(file_id)
    if _pyro_clients: return await stream_via_pyrogram(file_id, request, file_size=file_size)
    return await stream_via_botapi(file_id, request)

async def get_stream_info(file_id: str) -> dict:
    file_size = _lookup_file_size(file_id)
    return {"stream_url":f"/api/stream/{file_id}","file_id":file_id,"file_size":file_size,"has_pyrogram":bool(_pyro_clients)}
