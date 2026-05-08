import asyncio, logging, os, sqlite3, httpx, time
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from app.config import STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN, SESSION_1_API_ID, SESSION_1_API_HASH, SESSION_2_API_ID, SESSION_2_API_HASH, DB_PATH

logger = logging.getLogger(__name__)
BOT_TOKENS = [t for t in [STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN] if t]
_pyro_clients: list = []
_rr_index = 0

# Simple file-size cache to avoid repeated DB lookups
_size_cache: dict[str, int] = {}
_size_cache_ts: dict[str, float] = {}
_SIZE_CACHE_TTL = 300  # 5 minutes


def _lookup_file_size(file_id: str) -> int:
    now = time.time()
    if file_id in _size_cache and (now - _size_cache_ts.get(file_id, 0)) < _SIZE_CACHE_TTL:
        return _size_cache[file_id]
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT file_size FROM movies WHERE file_id=? LIMIT 1", (file_id,)).fetchone()
        if not row:
            row = conn.execute("SELECT file_size FROM episodes WHERE file_id=? LIMIT 1", (file_id,)).fetchone()
        conn.close()
        size = int(row[0]) if row and row[0] else 0
        _size_cache[file_id] = size
        _size_cache_ts[file_id] = now
        return size
    except Exception:
        return 0


def _get_next_pyro_client():
    """Round-robin between available Pyrogram clients."""
    global _rr_index
    if not _pyro_clients:
        return None
    client = _pyro_clients[_rr_index % len(_pyro_clients)]
    _rr_index += 1
    return client


async def init_pyrogram():
    global _pyro_clients
    sessions = [
        (STREAM_BOT_1, SESSION_1_API_ID, SESSION_1_API_HASH),
        (STREAM_BOT_2, SESSION_1_API_ID, SESSION_1_API_HASH),
    ]
    # Use second API credentials if available
    if SESSION_2_API_ID:
        sessions = [
            (STREAM_BOT_1, SESSION_1_API_ID, SESSION_1_API_HASH),
            (STREAM_BOT_2, SESSION_2_API_ID, SESSION_2_API_HASH),
        ]
    if not SESSION_1_API_ID:
        logger.warning("No Pyrogram API credentials — streaming limited to <20 MB files")
        return
    try:
        from pyrogram import Client
        for i, (token, api_id, api_hash) in enumerate(sessions):
            if not token or not api_id or not api_hash:
                continue
            try:
                client = Client(
                    name=f"stream_bot_{i}",
                    bot_token=token,
                    api_id=api_id,
                    api_hash=api_hash,
                    no_updates=True,
                    workdir="/tmp",
                    sleep_threshold=60,
                )
                await client.start()
                _pyro_clients.append(client)
                logger.info(f"✅ Pyrogram client {i} started (bot slot {i})")
            except Exception as e:
                logger.error(f"Pyrogram client {i} failed: {e}")
    except ImportError:
        logger.warning("Pyrogram not installed — streaming limited to <20 MB files")


async def stop_pyrogram():
    for client in _pyro_clients:
        try:
            await client.stop()
        except Exception:
            pass


def _parse_range(range_header: str, file_size: int) -> tuple[int, int | None]:
    """Parse Range header. Returns (start, end) where end may be None if file_size unknown."""
    start = 0
    end = (file_size - 1) if file_size > 0 else None
    if range_header and range_header.lower().startswith("bytes="):
        parts = range_header[6:].split("-")
        try:
            if parts[0]:
                start = int(parts[0])
            if len(parts) > 1 and parts[1]:
                end = int(parts[1])
            elif file_size > 0:
                end = file_size - 1
        except ValueError:
            pass
    return start, end


async def stream_via_pyrogram(file_id: str, request: Request, file_size: int = 0) -> Response:
    """Stream file using Pyrogram MTProto — supports large files (>20MB) with Range requests."""
    # Try each available Pyrogram client with fallback
    tried = set()
    while len(tried) < len(_pyro_clients):
        pyro = _get_next_pyro_client()
        if pyro is None or id(pyro) in tried:
            break
        tried.add(id(pyro))
        try:
            return await _do_pyro_stream(pyro, file_id, request, file_size)
        except Exception as e:
            logger.warning(f"Pyrogram stream attempt failed ({type(e).__name__}: {e}), trying next client…")
            continue

    logger.error(f"All Pyrogram clients failed for file_id={file_id[:20]}…")
    return Response(status_code=503, content="Streaming temporarily unavailable. Please retry.")


async def _do_pyro_stream(pyro, file_id: str, request: Request, file_size: int) -> Response:
    """Core streaming logic via a specific Pyrogram client."""
    range_header = request.headers.get("range", "")
    start, end = _parse_range(range_header, file_size)

    # Pyrogram streams in ~1 MB chunks internally
    CHUNK_SIZE = 1024 * 1024
    chunk_index = start // CHUNK_SIZE
    skip_bytes = start % CHUNK_SIZE

    async def generate():
        bytes_sent = 0
        limit = ((end - start + 1) if (end is not None and file_size > 0) else None)
        first_chunk = True
        async for chunk in pyro.stream_media(file_id, offset=chunk_index):
            if first_chunk and skip_bytes:
                chunk = chunk[skip_bytes:]
            first_chunk = False
            if not chunk:
                continue
            if limit is not None:
                remaining = limit - bytes_sent
                if remaining <= 0:
                    break
                if len(chunk) > remaining:
                    chunk = chunk[:remaining]
            bytes_sent += len(chunk)
            yield chunk
            if limit is not None and bytes_sent >= limit:
                break

    headers: dict = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": "inline",
        "Cache-Control": "no-cache",
        "Content-Type": "video/mp4",
    }
    status = 200
    if file_size > 0:
        content_length = (end - start + 1) if end is not None else (file_size - start)
        end_str = str(end) if end is not None else str(file_size - 1)
        headers["Content-Length"] = str(content_length)
        if range_header:
            headers["Content-Range"] = f"bytes {start}-{end_str}/{file_size}"
            status = 206
    elif range_header:
        status = 206

    return StreamingResponse(generate(), status_code=status, headers=headers, media_type="video/mp4")


async def stream_via_botapi(file_id: str, request: Request) -> Response:
    """Fallback: stream via Bot API (only works for files ≤ 20MB)."""
    token = ""
    file_path = ""
    tg_file_size = 0

    for try_token in BOT_TOKENS:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"https://api.telegram.org/bot{try_token}/getFile",
                    params={"file_id": file_id}
                )
                data = r.json()
                if data.get("ok") and data["result"].get("file_path"):
                    token = try_token
                    file_path = data["result"]["file_path"]
                    tg_file_size = data["result"].get("file_size", 0)
                    break
        except Exception:
            continue

    if not file_path:
        return Response(
            status_code=404,
            content="File not accessible (files >20 MB require Pyrogram which is currently unavailable)"
        )

    direct_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    range_header = request.headers.get("range", "")

    async def stream_gen():
        req_headers = {}
        if range_header:
            req_headers["Range"] = range_header
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("GET", direct_url, headers=req_headers) as resp:
                    async for chunk in resp.aiter_bytes(65536):
                        yield chunk
        except Exception as e:
            logger.error(f"Bot API stream error: {e}")

    resp_headers: dict = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": "inline",
        "Content-Type": "video/mp4",
    }
    if tg_file_size:
        resp_headers["Content-Length"] = str(tg_file_size)
    status = 206 if range_header else 200
    return StreamingResponse(stream_gen(), status_code=status, headers=resp_headers, media_type="video/mp4")


async def stream_file(file_id: str, request: Request, file_size: int = 0) -> Response:
    if not file_size:
        file_size = _lookup_file_size(file_id)
    if _pyro_clients:
        return await stream_via_pyrogram(file_id, request, file_size=file_size)
    return await stream_via_botapi(file_id, request)


async def get_stream_info(file_id: str) -> dict:
    file_size = _lookup_file_size(file_id)
    return {
        "stream_url": f"/api/stream/{file_id}",
        "file_id": file_id,
        "file_size": file_size,
        "has_pyrogram": bool(_pyro_clients),
        "active_clients": len(_pyro_clients),
    }
