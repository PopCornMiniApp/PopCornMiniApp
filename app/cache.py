"""
Shared in-memory cache module.
Used by main.py (API layer) and sync_bot.py (content ingestion layer)
so that adding new content automatically invalidates stale API responses.
"""
import time
import logging

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, object]] = {}


def cache_get(key: str) -> object | None:
    entry = _cache.get(key)
    if entry and time.time() < entry[0]:
        return entry[1]
    return None


def cache_set(key: str, value: object, ttl: int) -> None:
    _cache[key] = (time.time() + ttl, value)


def cache_clear_prefix(prefix: str) -> None:
    deleted = [k for k in list(_cache.keys()) if k.startswith(prefix)]
    for k in deleted:
        del _cache[k]
    if deleted:
        logger.debug("Cache cleared prefix=%s (%d keys)", prefix, len(deleted))


def cache_clear_all() -> None:
    count = len(_cache)
    _cache.clear()
    logger.info("Cache fully cleared (%d keys)", count)
