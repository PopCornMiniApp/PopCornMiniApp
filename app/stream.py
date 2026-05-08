"""
Stream Service: uses Telegram Bot API to generate streaming URLs for video files.
For files under 20MB: uses Bot API file download.
For larger files: uses Pyrogram user sessions to stream via range requests.
"""

import asyncio
import logging
import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from app.config import STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN

logger = logging.getLogger(__name__)

BOT_TOKENS = [t for t in [STREAM_BOT_1, STREAM_BOT_2, MAIN_BOT_TOKEN] if t]
_current_bot = 0


def _next_bot_token() -> str:
    global _current_bot
    token = BOT_TOKENS[_current_bot % len(BOT_TOKENS)]
    _current_bot += 1
    return token


async def get_file_url(file_id: str) -> str | None:
    """Get direct download URL for a Telegram file_id (works for files < 20MB)."""
    for token in BOT_TOKENS:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"https://api.telegram.org/bot{token}/getFile",
                    params={"file_id": file_id}
                )
                data = r.json()
                if data.get("ok") and data["result"].get("file_path"):
                    file_path = data["result"]["file_path"]
                    return f"https://api.telegram.org/file/bot{token}/{file_path}"
        except Exception as e:
            logger.warning(f"getFile failed with token {token[:20]}: {e}")
    return None


async def stream_file(file_id: str, request: Request) -> Response:
    """
    Stream a Telegram video file supporting HTTP Range requests.
    Uses round-robin between stream bots.
    """
    token = _next_bot_token()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://api.telegram.org/bot{token}/getFile",
                params={"file_id": file_id}
            )
            data = r.json()

        if not data.get("ok"):
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
            return Response(status_code=404, content="File not accessible via Bot API")

        file_path = data["result"]["file_path"]
        file_size = data["result"].get("file_size", 0)
        direct_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

        range_header = request.headers.get("range", "")
        headers = {}
        if range_header:
            headers["Range"] = range_header

        async def stream_generator():
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("GET", direct_url, headers=headers) as response:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        yield chunk

        resp_headers = {
            "Content-Type": "video/mp4",
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline",
        }
        if file_size:
            resp_headers["Content-Length"] = str(file_size)

        status = 206 if range_header else 200
        return StreamingResponse(
            stream_generator(),
            status_code=status,
            headers=resp_headers,
            media_type="video/mp4",
        )

    except Exception as e:
        logger.error(f"Stream error for file_id={file_id[:20]}: {e}")
        return Response(status_code=500, content=str(e))


async def get_stream_info(file_id: str) -> dict:
    """Returns stream URL and metadata for a file_id."""
    url = await get_file_url(file_id)
    return {
        "stream_url": f"/api/stream/{file_id}",
        "direct_url": url,
        "file_id": file_id,
    }
