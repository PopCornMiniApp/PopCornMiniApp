"""
PopCorn Streaming Engine v4.0
─────────────────────────────
• Pyrogram MTProto streaming with correct byte-level offsets
• Round-robin load balancing across multiple Pyrogram clients
• Proper HTTP Range request handling (206 Partial Content)
• HEAD request support for browser video preflight
• Bot API fallback for small files (≤ 20 MB)
• In-memory file-info cache to avoid repeated DB hits
"""
import asyncio
import logging
import os
import sqlite3
import time

import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from app.config import (
    DB_PATH,
    MAIN_BOT_TOKEN,
    PRIVATE_GROUP_ID,
    SESSION_1_API_HASH,
    SESSION_1_API_ID,
    SESSION_2_API_HASH,
    SESSION_2_API_ID,
    STREAM_BOT_1,
    STREAM_BOT_2,
)

logger = logging.getLogger(__name__)

BOT_TOKENS = [t for t in [STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN] if t]
_pyro_clients: list = []
_rr_index: int = 0

# ── File-info cache ───────────────────────────────────────────────────────────
_finfo_cache: dict[str, dict] = {}
_finfo_ts: dict[str, float] = {}
_FINFO_TTL = 600  # 10 minutes


def _lookup_file_info(file_id: str) -> dict:
    """Return {file_size, message_id} from DB with in-memory TTL cache."""
    now = time.time()
    if file_id in _finfo_cache and (now - _finfo_ts.get(file_id, 0)) < _FINFO_TTL:
        return _finfo_cache[file_id]

    info: dict = {"file_size": 0, "message_id": 0}
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            row = conn.execute(
                "SELECT COALESCE(file_size,0), COALESCE(message_id,0) "
                "FROM movies WHERE file_id=? LIMIT 1",
                (file_id,),
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT COALESCE(file_size,0), COALESCE(message_id,0) "
                    "FROM episodes WHERE file_id=? LIMIT 1",
                    (file_id,),
                ).fetchone()
            if row:
                info = {"file_size": int(row[0]), "message_id": int(row[1])}
        finally:
            conn.close()
    except Exception as exc:
        logger.error("file_info DB lookup failed: %s", exc)

    _finfo_cache[file_id] = info
    _finfo_ts[file_id] = now
    return info


# ── Pyrogram lifecycle ────────────────────────────────────────────────────────

def _next_pyro_client():
    """Round-robin selection among available Pyrogram clients."""
    global _rr_index
    if not _pyro_clients:
        return None
    client = _pyro_clients[_rr_index % len(_pyro_clients)]
    _rr_index += 1
    return client


async def init_pyrogram():
    global _pyro_clients
    if not SESSION_1_API_ID or not SESSION_1_API_HASH:
        logger.warning("No Pyrogram API credentials — only Bot API (≤20 MB) streaming available")
        return

    sessions = [
        (STREAM_BOT_1, SESSION_1_API_ID, SESSION_1_API_HASH, "slot_0"),
        (STREAM_BOT_2, SESSION_2_API_ID or SESSION_1_API_ID,
                       SESSION_2_API_HASH or SESSION_1_API_HASH, "slot_1"),
    ]

    try:
        from pyrogram import Client  # type: ignore
    except ImportError:
        logger.warning("Pyrogram not installed — streaming limited to ≤20 MB files")
        return

    for token, api_id, api_hash, name in sessions:
        if not token or not api_id or not api_hash:
            continue
        try:
            client = Client(
                name=name,
                bot_token=token,
                api_id=api_id,
                api_hash=api_hash,
                no_updates=True,
                workdir="/tmp",
                sleep_threshold=60,
            )
            await client.start()
            _pyro_clients.append(client)
            logger.info("✅ Pyrogram client '%s' ready", name)
        except Exception as exc:
            logger.error("Pyrogram client '%s' failed to start: %s", name, exc)


async def stop_pyrogram():
    for client in _pyro_clients:
        try:
            await client.stop()
        except Exception:
            pass


# ── HTTP Range parser ─────────────────────────────────────────────────────────

def _parse_range(range_header: str, file_size: int) -> tuple[int, int | None]:
    """Parse 'Range: bytes=X-Y' → (start, end). end=None if file_size unknown."""
    start = 0
    end: int | None = (file_size - 1) if file_size > 0 else None

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


# ── Core Pyrogram streaming ───────────────────────────────────────────────────

async def _do_pyro_stream(pyro, file_id: str, request: Request, file_size: int) -> Response:
    """
    Stream a Telegram file via Pyrogram MTProto.

    Key fix: stream_media(file_id, offset=<bytes>, limit=<bytes>)
    offset is in BYTES (not chunk index). limit=0 means no limit.
    """
    range_header = request.headers.get("range", "")
    start, end = _parse_range(range_header, file_size)

    # Bytes to deliver for this request
    if file_size > 0 and end is not None:
        content_length = end - start + 1
    elif file_size > 0:
        content_length = file_size - start
    else:
        content_length = None  # unknown; stream until done

    async def generate():
        sent = 0
        try:
            # ── FIX: offset=start (bytes), limit=content_length (bytes) ──────
            # Pyrogram 2.x: offset and limit are both in BYTES
            async for chunk in pyro.stream_media(
                file_id,
                offset=start,
                limit=content_length if content_length else 0,
            ):
                if not chunk:
                    continue
                # Trim last chunk if it overshoots our range
                if content_length is not None:
                    remaining = content_length - sent
                    if remaining <= 0:
                        return
                    if len(chunk) > remaining:
                        chunk = chunk[:remaining]
                sent += len(chunk)
                yield chunk
                if content_length is not None and sent >= content_length:
                    return
        except asyncio.CancelledError:
            pass  # Client disconnected — normal
        except Exception as exc:
            logger.error("Pyrogram generate() error after %d bytes: %s", sent, exc)

    headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": "inline",
        "Cache-Control": "no-store, no-cache",
        "Content-Type": "video/mp4",
    }
    status = 200

    if file_size > 0:
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
        if range_header:
            end_val = end if end is not None else file_size - 1
            headers["Content-Range"] = f"bytes {start}-{end_val}/{file_size}"
            status = 206
    elif range_header:
        status = 206  # Optimistically; we don't know total size

    return StreamingResponse(
        generate(), status_code=status, headers=headers, media_type="video/mp4"
    )


async def stream_via_pyrogram(file_id: str, request: Request, file_size: int = 0) -> Response:
    """Try each Pyrogram client in round-robin; return 503 if all fail."""
    if not _pyro_clients:
        return Response(
            status_code=503,
            content="Streaming engine unavailable — Pyrogram not initialised",
        )

    tried: set[int] = set()
    while len(tried) < len(_pyro_clients):
        pyro = _next_pyro_client()
        if pyro is None or id(pyro) in tried:
            break
        tried.add(id(pyro))
        try:
            return await _do_pyro_stream(pyro, file_id, request, file_size)
        except Exception as exc:
            logger.warning(
                "Pyrogram client %d failed (%s: %s), trying next…",
                id(pyro), type(exc).__name__, exc,
            )
            continue

    logger.error("All Pyrogram clients failed for file_id=%.20s…", file_id)
    return Response(
        status_code=503,
        content="Streaming temporarily unavailable — please retry in a moment.",
    )


# ── Bot API fallback (files ≤ 20 MB) ─────────────────────────────────────────

async def stream_via_botapi(file_id: str, request: Request) -> Response:
    """Proxy the file through Telegram's Bot API (20 MB max)."""
    token = ""
    file_path = ""
    tg_size = 0

    for try_token in BOT_TOKENS:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(
                    f"https://api.telegram.org/bot{try_token}/getFile",
                    params={"file_id": file_id},
                )
                data = r.json()
                if data.get("ok") and data["result"].get("file_path"):
                    token = try_token
                    file_path = data["result"]["file_path"]
                    tg_size = data["result"].get("file_size", 0)
                    break
        except Exception:
            continue

    if not file_path:
        return Response(
            status_code=404,
            content="File not accessible via Bot API (file may exceed 20 MB — Pyrogram required)",
        )

    direct_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    range_header = request.headers.get("range", "")

    async def proxy_stream():
        req_headers = {"Range": range_header} if range_header else {}
        try:
            async with httpx.AsyncClient(timeout=600) as c:
                async with c.stream("GET", direct_url, headers=req_headers) as resp:
                    async for chunk in resp.aiter_bytes(65536):
                        yield chunk
        except Exception as exc:
            logger.error("Bot API proxy stream error: %s", exc)

    resp_headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": "inline",
        "Cache-Control": "no-store",
        "Content-Type": "video/mp4",
    }
    if tg_size:
        resp_headers["Content-Length"] = str(tg_size)

    status = 206 if range_header else 200
    return StreamingResponse(
        proxy_stream(), status_code=status, headers=resp_headers, media_type="video/mp4"
    )


# ── Public entry points ───────────────────────────────────────────────────────

async def stream_file(file_id: str, request: Request, file_size: int = 0) -> Response:
    """Main streaming dispatcher. Pyrogram → Bot API fallback."""
    info = _lookup_file_info(file_id)
    if not file_size:
        file_size = info["file_size"]

    if _pyro_clients:
        return await stream_via_pyrogram(file_id, request, file_size=file_size)
    return await stream_via_botapi(file_id, request)


def stream_head_response(file_id: str) -> Response:
    """Return headers-only response for HEAD /api/stream/{file_id}."""
    info = _lookup_file_info(file_id)
    file_size = info["file_size"]
    headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Content-Type": "video/mp4",
        "Content-Disposition": "inline",
        "Cache-Control": "no-store",
    }
    if file_size:
        headers["Content-Length"] = str(file_size)
    return Response(status_code=200, headers=headers)


async def get_stream_info(file_id: str) -> dict:
    info = _lookup_file_info(file_id)
    return {
        "stream_url": f"/api/stream/{file_id}",
        "file_id": file_id,
        "file_size": info["file_size"],
        "message_id": info["message_id"],
        "has_pyrogram": bool(_pyro_clients),
        "active_clients": len(_pyro_clients),
    }
