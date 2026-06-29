"""
Response Caching Layer for VIDHI
In-memory cache with TTL for common queries and LLM responses.

Features:
- In-memory cache (no Redis dependency)
- TTL-based expiration
- LRU eviction when cache is full
- Cache hit/miss metrics
- Thread-safe operations
"""

import time
import hashlib
import logging
from typing import Any, Optional, Dict
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)


class CacheEntry:
    """Single cache entry with TTL"""

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class InMemoryCache:
    """Thread-safe in-memory cache with TTL and LRU eviction"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Args:
            max_size: Maximum number of entries (LRU eviction when full)
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = Lock()

        # Metrics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _compute_key(self, key: str) -> str:
        """Compute cache key hash"""
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._compute_key(key)

        with self.lock:
            if cache_key not in self.cache:
                self.misses += 1
                logger.debug(f"Cache MISS: {key[:50]}...")
                return None

            entry = self.cache[cache_key]

            # Check if expired
            if entry.is_expired():
                del self.cache[cache_key]
                self.misses += 1
                logger.debug(f"Cache EXPIRED: {key[:50]}...")
                return None

            # Move to end (LRU)
            self.cache.move_to_end(cache_key)
            self.hits += 1
            logger.debug(f"Cache HIT: {key[:50]}...")
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        cache_key = self._compute_key(key)
        ttl = ttl or self.default_ttl

        with self.lock:
            # Evict oldest if cache is full
            if len(self.cache) >= self.max_size and cache_key not in self.cache:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.evictions += 1
                logger.debug(f"Cache EVICTION (LRU)")

            self.cache[cache_key] = CacheEntry(value, ttl)
            self.cache.move_to_end(cache_key)
            logger.debug(f"Cache SET: {key[:50]}... (TTL: {ttl}s)")

    def delete(self, key: str):
        """Delete value from cache"""
        cache_key = self._compute_key(key)

        with self.lock:
            if cache_key in self.cache:
                del self.cache[cache_key]
                logger.debug(f"Cache DELETE: {key[:50]}...")

    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            logger.info("Cache CLEARED")

    def cleanup_expired(self):
        """Remove all expired entries"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.info(
                    f"Cache cleanup: removed {len(expired_keys)} expired entries"
                )

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": f"{hit_rate:.1f}%",
                "total_requests": total_requests,
            }

    def reset_stats(self):
        """Reset cache statistics"""
        with self.lock:
            self.hits = 0
            self.misses = 0
            self.evictions = 0


# Global cache instances
query_cache = InMemoryCache(max_size=500, default_ttl=3600)  # 1 hour for queries
llm_cache = InMemoryCache(
    max_size=1000, default_ttl=86400
)  # 24 hours for LLM responses


def cache_query_result(query: str, result: Any, ttl: int = 3600):
    """Cache a query result"""
    query_cache.set(query, result, ttl)


def get_cached_query_result(query: str) -> Optional[Any]:
    """Get cached query result"""
    return query_cache.get(query)


def cache_llm_response(prompt: str, response: str, ttl: int = 86400):
    """Cache an LLM response"""
    llm_cache.set(prompt, response, ttl)


def get_cached_llm_response(prompt: str) -> Optional[str]:
    """Get cached LLM response"""
    return llm_cache.get(prompt)


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches"""
    return {"query_cache": query_cache.get_stats(), "llm_cache": llm_cache.get_stats()}


def clear_all_caches():
    """Clear all caches"""
    query_cache.clear()
    llm_cache.clear()


# Periodic cleanup (call this from a background task)
def cleanup_all_caches():
    """Cleanup expired entries from all caches"""
    query_cache.cleanup_expired()
    llm_cache.cleanup_expired()
