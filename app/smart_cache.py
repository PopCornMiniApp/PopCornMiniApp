"""
SmartCache - Advanced caching system with LRU eviction and statistics
Replaces the simple in-memory cache with a more sophisticated system
"""
import time
import logging
from collections import OrderedDict
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    sets: int = 0
    deletes: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> dict:
        """Convert stats to dictionary"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "sets": self.sets,
            "deletes": self.deletes,
            "hit_rate": round(self.hit_rate, 2),
            "total_requests": self.hits + self.misses
        }


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() >= self.expires_at

    def access(self) -> Any:
        """Record access and return value"""
        self.access_count += 1
        self.last_access = time.time()
        return self.value


class SmartCache:
    """
    Advanced LRU cache with:
    - TTL (Time To Live) support
    - LRU eviction when max_size is reached
    - Statistics tracking
    - Memory usage estimation
    - Prefix-based operations
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize SmartCache

        Args:
            max_size: Maximum number of entries (LRU eviction when exceeded)
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Clean expired entries every 60 seconds

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        # Periodic cleanup of expired entries
        self._maybe_cleanup()

        entry = self._cache.get(key)

        if entry is None:
            self._stats.misses += 1
            return None

        if entry.is_expired():
            self._stats.misses += 1
            del self._cache[key]
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._stats.hits += 1

        return entry.access()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default_ttl if None)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl

        # Estimate size (rough approximation)
        size_bytes = self._estimate_size(value)

        entry = CacheEntry(
            value=value,
            expires_at=expires_at,
            size_bytes=size_bytes
        )

        # If key exists, remove it first (will be re-added at end)
        if key in self._cache:
            del self._cache[key]

        # Add new entry
        self._cache[key] = entry
        self._stats.sets += 1

        # Evict oldest entries if max_size exceeded
        while len(self._cache) > self.max_size:
            self._evict_oldest()

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            self._stats.deletes += 1
            return True
        return False

    def clear_prefix(self, prefix: str) -> int:
        """
        Clear all entries with given prefix

        Args:
            prefix: Key prefix to match

        Returns:
            Number of entries deleted
        """
        keys_to_delete = [
            k for k in self._cache.keys() if k.startswith(prefix)]

        for key in keys_to_delete:
            del self._cache[key]
            self._stats.deletes += 1

        if keys_to_delete:
            logger.debug(
                f"Cache cleared prefix={prefix} ({len(keys_to_delete)} keys)")

        return len(keys_to_delete)

    def clear_all(self) -> int:
        """
        Clear all cache entries

        Returns:
            Number of entries deleted
        """
        count = len(self._cache)
        self._cache.clear()
        self._stats.deletes += count
        logger.info(f"Cache fully cleared ({count} keys)")
        return count

    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            **self._stats.to_dict(),
            "size": len(self._cache),
            "max_size": self.max_size,
            "memory_bytes": self._estimate_total_size(),
            "oldest_entry_age": self._get_oldest_entry_age(),
        }

    def get_keys(self, prefix: Optional[str] = None) -> list[str]:
        """
        Get all cache keys, optionally filtered by prefix

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of cache keys
        """
        if prefix:
            return [k for k in self._cache.keys() if k.startswith(prefix)]
        return list(self._cache.keys())

    def _evict_oldest(self) -> None:
        """Evict the oldest (least recently used) entry"""
        if self._cache:
            # OrderedDict maintains insertion order, first item is oldest
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._stats.evictions += 1
            logger.debug(f"Cache evicted oldest entry: {oldest_key}")

    def _maybe_cleanup(self) -> None:
        """Periodically clean up expired entries"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        expired_keys = [
            k for k, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(
                f"Cache cleanup: removed {len(expired_keys)} expired entries")

        self._last_cleanup = now

    def _estimate_size(self, value: Any) -> int:
        """Rough estimation of value size in bytes"""
        try:
            import sys
            return sys.getsizeof(value)
        except Exception:
            # Fallback estimation
            if isinstance(value, str):
                return len(value)
            elif isinstance(value, (list, dict)):
                return len(str(value))
            return 100  # Default estimate

    def _estimate_total_size(self) -> int:
        """Estimate total cache size in bytes"""
        return sum(entry.size_bytes for entry in self._cache.values())

    def _get_oldest_entry_age(self) -> float:
        """Get age of oldest entry in seconds"""
        if not self._cache:
            return 0.0

        oldest_entry = next(iter(self._cache.values()))
        return time.time() - oldest_entry.created_at


# Global cache instance
_smart_cache = SmartCache(max_size=1000, default_ttl=300)


# Backward-compatible API (matches old cache.py interface)
def cache_get(key: str) -> Optional[Any]:
    """Get value from cache"""
    return _smart_cache.get(key)


def cache_set(key: str, value: Any, ttl: int) -> None:
    """Set value in cache with TTL"""
    _smart_cache.set(key, value, ttl)


def cache_clear_prefix(prefix: str) -> None:
    """Clear all entries with given prefix"""
    _smart_cache.clear_prefix(prefix)


def cache_clear_all() -> None:
    """Clear all cache entries"""
    _smart_cache.clear_all()


# New advanced API
def cache_delete(key: str) -> bool:
    """Delete specific cache entry"""
    return _smart_cache.delete(key)


def cache_get_stats() -> dict:
    """Get cache statistics"""
    return _smart_cache.get_stats()


def cache_get_keys(prefix: Optional[str] = None) -> list[str]:
    """Get all cache keys, optionally filtered by prefix"""
    return _smart_cache.get_keys(prefix)


def get_cache_instance() -> SmartCache:
    """Get the global cache instance for advanced operations"""
    return _smart_cache

# Made with Bob
