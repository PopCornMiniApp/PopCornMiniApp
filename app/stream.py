"""
Stream Service: Uses Pyrogram (MTProto) for large files + Bot API for small files.
Supports HTTP Range requests for seeking in video player.
"""
import asyncio
import logging
import os
import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from app.config import STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN, SESSION_1_API_ID, SESSION_1_API_HASH

logger = logging.getLogger(__name__)

BOT_TOKENS = [t for t in [STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN] if t]
_current_bot = 0
_pyro_clients = []
_pyro_lock = asyncio.Lock()


def _next_bot_token() -> str:
    global _current_bot
    token = BOT_TOKENS[_current_bot % len(BOT_TOKENS)]
    _current_bot += 1
    return token


async def init_pyrogram():
    """Initialize Pyrogram clients for large file streaming."""
    global _pyro_clients
    if not SESSION_1_API_ID:
        logger.warning("No Pyrogram API credentials, large file streaming unavailable")
        return

    try:
        from pyrogram import Client
        tokens = [t for t in [STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN] if t]
        for i, token in enumerate(tokens[:2]):
            try:
                client = Client(
                    name=f"stream_{i}",
                    bot_token=token,
                    api_id=SESSION_1_API_ID,
                    api_hash=SESSION_1_API_HASH,
                    no_updates=True,
                    workdir="/tmp",
                )
                await client.start()
                _pyro_clients.append(client)
                logger.info(f"✅ Pyrogram client {i} started")
            except Exception as e:
                logger.error(f"Pyrogram client {i} failed: {e}")
    except ImportError:
        logger.warning("Pyrogram not installed, large file streaming unavailable")


async def stop_pyrogram():
    for client in _pyro_clients:
        try:
            await client.stop()
        except Exception:
            pass


def _get_pyro_client():
    if not _pyro_clients:
        return None
    return _pyro_clients[_current_bot % len(_pyro_clients)]


async def get_file_url(file_id: str) -> str | None:
    """Get direct download URL (works for files < 20MB via Bot API)."""
    for token in BOT_TOKENS:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"https://api.telegram.org/bot{token}/getFile",
                    params={"file_id": file_id}
                )
                data = r.json()
                if data.get("ok") and data["result"].get("file_path"):
                    return f"https://api.telegram.org/file/bot{token}/{data['result']['file_path']}"
        except Exception:
            pass
    return None


async def stream_via_pyrogram(file_id: str, request: Request) -> Response:
    """Stream large files via Pyrogram MTProto (no 20MB limit)."""
    pyro = _get_pyro_client()
    if not pyro:
        return Response(status_code=503, content="Pyrogram not available")

    try:
        from pyrogram.raw.functions.upload import GetFile
        from pyrogram.raw.types import InputDocumentFileLocation
        import io

        range_header = request.headers.get("range", "")
        start = 0
        end = None

        if range_header:
            parts = range_header.replace("bytes=", "").split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else None

        CHUNK_SIZE = 1024 * 1024  # 1MB chunks

        async def generate():
            async for chunk in pyro.stream_media(file_id, offset=start // CHUNK_SIZE):
                yield chunk

        headers = {
            "Content-Type": "video/mp4",
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline",
        }
        return StreamingResponse(
            generate(),
            status_code=206 if range_header else 200,
            headers=headers,
            media_type="video/mp4",
        )
    except Exception as e:
        logger.error(f"Pyrogram stream error: {e}")
        return Response(status_code=500, content=str(e))


async def stream_via_botapi(file_id: str, request: Request) -> Response:
    """Stream via Bot API proxy (files up to ~20MB)."""
    token = _next_bot_token()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://api.telegram.org/bot{token}/getFile",
                params={"file_id": file_id}
            )
            data = r.json()

        if not data.get("ok"):
            # Try other tokens
            for alt_token in BOT_TOKENS:
                if alt_token == token:
                    continue
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.get(
                        f"https://api.telegram.org/bot{alt_token}/getFile",
                        params={"file_id": file_id}
                    )
                    data = r.json()
                    if data.get("ok"):
                        token = alt_token
                        break

        if not data.get("ok") or not data["result"].get("file_path"):
            return Response(status_code=404, content="File not accessible via Bot API (file may be >20MB)")

        file_path = data["result"]["file_path"]
        file_size = data["result"].get("file_size", 0)
        direct_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

        range_header = request.headers.get("range", "")
        req_headers = {"Range": range_header} if range_header else {}

        async def stream_gen():
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("GET", direct_url, headers=req_headers) as resp:
                    async for chunk in resp.aiter_bytes(65536):
                        yield chunk

        resp_headers = {
            "Content-Type": "video/mp4",
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline",
        }
        if file_size:
            resp_headers["Content-Length"] = str(file_size)

        return StreamingResponse(
            stream_gen(),
            status_code=206 if range_header else 200,
            headers=resp_headers,
            media_type="video/mp4",
        )
    except Exception as e:
        logger.error(f"BotAPI stream error: {e}")
        return Response(status_code=500, content=str(e))


async def stream_file(file_id: str, request: Request) -> Response:
    """
    Smart streaming: tries Pyrogram first (for large files),
    falls back to Bot API proxy.
    """
    if _pyro_clients:
        return await stream_via_pyrogram(file_id, request)
    return await stream_via_botapi(file_id, request)


async def get_stream_info(file_id: str) -> dict:
    url = await get_file_url(file_id)
    return {
        "stream_url": f"/api/stream/{file_id}",
        "direct_url": url,
        "file_id": file_id,
        "has_pyrogram": bool(_pyro_clients),
    }
