"""
PopCorn Streaming Engine v5.0 — Production-Grade Telegram File Streaming
═══════════════════════════════════════════════════════════════════════════
Root cause analysis (confirmed):
  • Pyrogram stream_media(file_id) fails silently because:
    1. file_reference inside file_id expires (Telegram design)
    2. Bot may not be in the private group → cannot resolve file
  • Server sends correct headers then drops connection with 0 bytes

Fix strategy:
  1. Use MAIN_BOT_TOKEN as the PRIMARY Pyrogram client (it IS in the group)
  2. get_messages(GROUP_ID, message_id) → fresh message with fresh file_reference
  3. stream_media(message, ...) — NOT stream_media(file_id)
  4. Pre-validate BEFORE sending headers — return proper 503 if access fails
  5. Correct chunk-based offset (Pyrogram offset is in 1MB chunks, not bytes)
  6. Bot API proxy fallback for small files (≤20 MB)
"""
import asyncio
import logging
import math
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
_pyro_clients: list = []   # list of (pyrogram.Client, bot_token_label)
_rr_index: int = 0

CHUNK_SIZE = 1024 * 1024   # Pyrogram internal chunk size = 1 MiB


# ── File-info cache ───────────────────────────────────────────────────────────

_finfo: dict[str, dict] = {}
_finfo_ts: dict[str, float] = {}
_FINFO_TTL = 600


def _lookup_file_info(file_id: str) -> dict:
    """Return {'file_size': int, 'message_id': int} with in-memory TTL cache."""
    now = time.time()
    if file_id in _finfo and now - _finfo_ts.get(file_id, 0) < _FINFO_TTL:
        return _finfo[file_id]

    info = {"file_size": 0, "message_id": 0}
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            row = conn.execute(
                "SELECT COALESCE(file_size,0), COALESCE(message_id,0) "
                "FROM movies WHERE file_id=? LIMIT 1", (file_id,)
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT COALESCE(file_size,0), COALESCE(message_id,0) "
                    "FROM episodes WHERE file_id=? LIMIT 1", (file_id,)
                ).fetchone()
            if row:
                info = {"file_size": int(row[0]), "message_id": int(row[1])}
        finally:
            conn.close()
    except Exception as exc:
        logger.error("file_info DB lookup failed: %s", exc)

    _finfo[file_id] = info
    _finfo_ts[file_id] = now
    return info


# ── Pyrogram lifecycle ────────────────────────────────────────────────────────

def _next_client():
    global _rr_index
    if not _pyro_clients:
        return None
    c = _pyro_clients[_rr_index % len(_pyro_clients)]
    _rr_index += 1
    return c


def _restore_sessions():
    """Download Pyrogram session files from HF Dataset so peers are pre-cached."""
    try:
        from huggingface_hub import hf_hub_download
        from app.config import HF_TOKEN, HF_DATASET_NAME
        for name in ("main", "s1", "s2"):
            fname = f"popcorn_{name}.session"
            try:
                local = hf_hub_download(
                    repo_id=HF_DATASET_NAME,
                    filename=fname,
                    repo_type="dataset",
                    token=HF_TOKEN,
                    local_dir="/tmp",
                )
                if local != f"/tmp/{fname}":
                    import shutil
                    shutil.copy(local, f"/tmp/{fname}")
                logger.info("📥 Restored Pyrogram session: %s", fname)
            except Exception:
                pass  # File may not exist yet — that's fine
    except Exception as e:
        logger.warning("Session restore skipped: %s", e)


def _persist_sessions():
    """Upload Pyrogram session files to HF Dataset for next restart."""
    try:
        from huggingface_hub import HfApi
        from app.config import HF_TOKEN, HF_DATASET_NAME
        api = HfApi(token=HF_TOKEN)
        for name in ("main", "s1", "s2"):
            fpath = f"/tmp/popcorn_{name}.session"
            if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
                try:
                    api.upload_file(
                        path_or_fileobj=fpath,
                        path_in_repo=f"popcorn_{name}.session",
                        repo_id=HF_DATASET_NAME,
                        repo_type="dataset",
                        token=HF_TOKEN,
                    )
                    logger.info("📤 Persisted Pyrogram session: %s", name)
                except Exception as ue:
                    logger.warning("Session persist '%s' failed: %s", name, ue)
    except Exception as e:
        logger.warning("Session persist skipped: %s", e)


async def init_pyrogram():
    global _pyro_clients

    if not SESSION_1_API_ID or not SESSION_1_API_HASH:
        logger.warning("No MTProto credentials — streaming limited to ≤20 MB files")
        return

    try:
        from pyrogram import Client  # type: ignore
    except ImportError:
        logger.warning("Pyrogram not installed — streaming limited to ≤20 MB")
        return

    # Restore session files from HF Dataset (contains cached peer access_hashes)
    _restore_sessions()

    # ── Session list ────────────────────────────────────────────────────────
    # MAIN_BOT_TOKEN FIRST — it is definitely a member of PRIVATE_GROUP_ID
    # and can access all stored messages (it's the sync/receive bot).
    # STREAM_BOT_1/2 added as extra load-balancing slots if they're in the group.
    sessions = []
    if MAIN_BOT_TOKEN:
        sessions.append((MAIN_BOT_TOKEN, SESSION_1_API_ID, SESSION_1_API_HASH, "main"))
    if STREAM_BOT_1:
        sessions.append((STREAM_BOT_1, SESSION_1_API_ID, SESSION_1_API_HASH, "s1"))
    if STREAM_BOT_2:
        sessions.append((STREAM_BOT_2,
                         SESSION_2_API_ID or SESSION_1_API_ID,
                         SESSION_2_API_HASH or SESSION_1_API_HASH, "s2"))

    any_resolved = False
    for token, api_id, api_hash, name in sessions:
        try:
            client = Client(
                name=f"popcorn_{name}",
                bot_token=token,
                api_id=api_id,
                api_hash=api_hash,
                no_updates=True,
                workdir="/tmp",
                sleep_threshold=60,
            )
            await client.start()

            # Populate peer cache by fetching all dialogs (groups/chats the bot is in).
            # This is the only reliable way for a fresh session to discover group peers.
            group_found = False
            try:
                async for dialog in client.get_dialogs():
                    chat = dialog.chat
                    cid = getattr(chat, "id", None)
                    if cid and abs(cid) == abs(PRIVATE_GROUP_ID):
                        group_found = True
                        logger.info(
                            "✅ Pyrogram client '%s' found private group: %s",
                            name, getattr(chat, "title", cid)
                        )
                        break
                if not group_found:
                    logger.warning(
                        "Pyrogram client '%s': private group not found in dialogs — "
                        "is the bot a member of group %s?",
                        name, PRIVATE_GROUP_ID
                    )
            except Exception as de:
                logger.warning("Pyrogram client '%s' get_dialogs failed: %s", name, de)

            _pyro_clients.append(client)
            if group_found:
                any_resolved = True
            logger.info("✅ Pyrogram client '%s' started (group_found=%s)", name, group_found)
        except Exception as exc:
            logger.error("Pyrogram client '%s' failed: %s", name, exc)

    # Persist sessions to HF Dataset so next restart has cached peers
    if any_resolved:
        _persist_sessions()


async def stop_pyrogram():
    for c in _pyro_clients:
        try:
            await c.stop()
        except Exception:
            pass


# ── HTTP Range helpers ────────────────────────────────────────────────────────

def _parse_range(header: str, file_size: int) -> tuple[int, int | None]:
    start, end = 0, (file_size - 1) if file_size > 0 else None
    if header and header.lower().startswith("bytes="):
        parts = header[6:].split("-")
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


# ── Core Pyrogram streaming with pre-validation ───────────────────────────────

async def _get_fresh_message(pyro, message_id: int):
    """
    Fetch a fresh message object from the private group.
    This refreshes the file_reference so stream_media works reliably.
    Returns None if not accessible.
    """
    if not message_id or not PRIVATE_GROUP_ID:
        return None
    try:
        msg = await asyncio.wait_for(
            pyro.get_messages(PRIVATE_GROUP_ID, message_id),
            timeout=12,
        )
        if msg and not getattr(msg, "empty", True):
            return msg
        logger.warning("get_messages(%d) returned empty message", message_id)
        return None
    except asyncio.TimeoutError:
        logger.error("get_messages(%d) timed out", message_id)
        return None
    except Exception as exc:
        logger.error("get_messages(%d) failed: %s", message_id, exc)
        return None


async def _do_pyro_stream(pyro, file_id: str, message_id: int,
                           request: Request, file_size: int) -> Response:
    """
    Stream a Telegram file via Pyrogram MTProto.

    Critical implementation notes:
    ─────────────────────────────
    • Pyrogram stream_media offset is in 1-MiB CHUNKS (not bytes).
      offset=N means skip first N×1MiB bytes before streaming.
    • We MUST use a fresh Message object (not bare file_id) to avoid
      file_reference expiry errors (silent empty stream).
    • Pre-validate: fetch first chunk before sending response headers.
      If the generator is empty, return 503 instead of broken response.
    """
    range_header = request.headers.get("range", "")
    start, end = _parse_range(range_header, file_size)

    content_length: int | None = None
    if file_size > 0 and end is not None:
        content_length = end - start + 1

    # Chunk arithmetic (Pyrogram offset unit = 1 MiB chunk)
    chunk_offset = start // CHUNK_SIZE          # which chunk to start from
    skip_in_first = start % CHUNK_SIZE          # bytes to discard from first chunk

    chunk_count = 0  # 0 = unlimited
    if content_length is not None:
        needed_bytes = skip_in_first + content_length
        chunk_count = math.ceil(needed_bytes / CHUNK_SIZE)

    # ── Step 1: get a fresh message (refreshes file_reference) ───────────
    stream_target = await _get_fresh_message(pyro, message_id)
    if stream_target is None:
        # Could not get message — try with raw file_id as last resort
        logger.warning("Falling back to raw file_id streaming (may fail if ref expired)")
        stream_target = file_id

    # ── Step 2: pre-validate — fetch first chunk before committing headers ─
    first_chunk_raw: bytes | None = None
    try:
        async for raw in pyro.stream_media(stream_target, offset=chunk_offset, limit=1):
            if raw:
                first_chunk_raw = raw
            break
    except Exception as exc:
        logger.error("Pyrogram pre-validation failed: %s", exc)
        return Response(
            status_code=503,
            content=f"Stream pre-check failed: {type(exc).__name__}: {exc}",
            media_type="text/plain",
        )

    if not first_chunk_raw:
        logger.error(
            "Pyrogram stream_media returned empty for msg_id=%d file_id=%.20s…",
            message_id, file_id,
        )
        # Bot might not be in the group — provide clear diagnostic
        return Response(
            status_code=503,
            content=(
                "Streaming unavailable: bot cannot access this file. "
                "Ensure the streaming bot is a member of the private group "
                f"(group_id={PRIVATE_GROUP_ID}, message_id={message_id})."
            ),
            media_type="text/plain",
        )

    # Apply first-chunk byte skip
    first_chunk = first_chunk_raw[skip_in_first:]
    if content_length is not None and len(first_chunk) > content_length:
        first_chunk = first_chunk[:content_length]

    # ── Step 3: build the streaming generator ─────────────────────────────
    async def generate():
        bytes_sent = 0

        # Yield pre-fetched first chunk
        yield first_chunk
        bytes_sent += len(first_chunk)
        if content_length is not None and bytes_sent >= content_length:
            return

        # Remaining chunks (offset+1 onwards)
        remaining_count = max(0, chunk_count - 1) if chunk_count > 0 else 0
        try:
            async for chunk in pyro.stream_media(
                stream_target,
                offset=chunk_offset + 1,
                limit=remaining_count,
            ):
                if not chunk:
                    continue
                if content_length is not None:
                    remaining = content_length - bytes_sent
                    if remaining <= 0:
                        return
                    if len(chunk) > remaining:
                        chunk = chunk[:remaining]
                bytes_sent += len(chunk)
                yield chunk
                if content_length is not None and bytes_sent >= content_length:
                    return
        except asyncio.CancelledError:
            pass  # Client disconnected — normal
        except Exception as exc:
            logger.error(
                "Pyrogram generator failed after %d bytes: %s: %s",
                bytes_sent, type(exc).__name__, exc,
            )

    # ── Build response headers ────────────────────────────────────────────
    headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": "inline",
        "Cache-Control": "no-store",
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
        status = 206

    return StreamingResponse(
        generate(), status_code=status, headers=headers, media_type="video/mp4"
    )


async def stream_via_pyrogram(file_id: str, request: Request,
                               file_size: int = 0, message_id: int = 0) -> Response:
    """Try all Pyrogram clients in round-robin with pre-validation."""
    if not _pyro_clients:
        return Response(
            status_code=503,
            content="No Pyrogram clients available (check MTProto credentials)",
        )

    tried: set[int] = set()
    last_error = ""

    while len(tried) < len(_pyro_clients):
        pyro = _next_client()
        if pyro is None or id(pyro) in tried:
            break
        tried.add(id(pyro))
        try:
            resp = await _do_pyro_stream(pyro, file_id, message_id, request, file_size)
            # If we got a StreamingResponse (not an error Response), return it
            if isinstance(resp, StreamingResponse):
                return resp
            # Got a 503 error — try next client
            last_error = resp.body.decode() if hasattr(resp, "body") else "unknown"
            logger.warning("Client %d returned error, trying next: %s", id(pyro), last_error[:100])
            continue
        except Exception as exc:
            last_error = str(exc)
            logger.warning("Client %d exception: %s", id(pyro), exc)
            continue

    return Response(
        status_code=503,
        content=f"All Pyrogram clients failed. Last error: {last_error[:200]}",
        media_type="text/plain",
    )


# ── Bot API fallback (files ≤ 20 MB) ─────────────────────────────────────────

async def stream_via_botapi(file_id: str, request: Request) -> Response:
    """Proxy file through Bot API — only works for files ≤ 20 MB."""
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
            content="File not accessible via Bot API (>20 MB requires Pyrogram MTProto)",
        )

    direct_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    range_header = request.headers.get("range", "")

    async def proxy():
        headers = {"Range": range_header} if range_header else {}
        try:
            async with httpx.AsyncClient(timeout=600) as c:
                async with c.stream("GET", direct_url, headers=headers) as resp:
                    async for chunk in resp.aiter_bytes(65536):
                        yield chunk
        except Exception as exc:
            logger.error("Bot API proxy error: %s", exc)

    resp_headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": "inline",
        "Cache-Control": "no-store",
        "Content-Type": "video/mp4",
    }
    if tg_size:
        resp_headers["Content-Length"] = str(tg_size)

    return StreamingResponse(
        proxy(),
        status_code=206 if range_header else 200,
        headers=resp_headers,
        media_type="video/mp4",
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def stream_file(file_id: str, request: Request, file_size: int = 0) -> Response:
    """Main dispatcher: Pyrogram (MTProto) → Bot API fallback."""
    info = _lookup_file_info(file_id)
    if not file_size:
        file_size = info["file_size"]
    message_id = info["message_id"]

    if _pyro_clients:
        return await stream_via_pyrogram(
            file_id, request, file_size=file_size, message_id=message_id
        )
    return await stream_via_botapi(file_id, request)


def stream_head_response(file_id: str) -> Response:
    """HEAD response for browser video pre-flight (no body sent)."""
    info = _lookup_file_info(file_id)
    headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Content-Type": "video/mp4",
        "Content-Disposition": "inline",
        "Cache-Control": "no-store",
    }
    if info["file_size"]:
        headers["Content-Length"] = str(info["file_size"])
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


async def debug_stream_test(file_id: str) -> dict:
    """
    Diagnostic endpoint: test if Pyrogram can actually stream a file.
    Returns detailed debug info without sending video data.
    """
    info = _lookup_file_info(file_id)

    result: dict = {
        "file_id": file_id[:30] + "...",
        "file_size": info["file_size"],
        "message_id": info["message_id"],
        "private_group_id": PRIVATE_GROUP_ID,
        "pyro_clients": len(_pyro_clients),
        "message_fetched": False,
        "msg_error": None,
        "first_chunk_bytes": 0,
        "stream_error": None,
        "stream_ok": False,
    }

    if not _pyro_clients:
        result["stream_error"] = "No Pyrogram clients initialized"
        return result

    pyro = _pyro_clients[0]

    # Try to fetch message
    msg = await _get_fresh_message(pyro, info["message_id"])
    result["message_fetched"] = msg is not None
    if msg is None:
        result["msg_error"] = (
            f"Cannot get message {info['message_id']} from group {PRIVATE_GROUP_ID}. "
            "Bot is likely NOT a member of the private group."
        )

    # Try to get first chunk
    target = msg or file_id
    try:
        async for chunk in pyro.stream_media(target, offset=0, limit=1):
            if chunk:
                result["first_chunk_bytes"] = len(chunk)
                result["stream_ok"] = True
            break
    except Exception as exc:
        result["stream_error"] = f"{type(exc).__name__}: {exc}"

    return result
