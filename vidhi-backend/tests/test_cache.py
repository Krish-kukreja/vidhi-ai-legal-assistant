"""
Tests for Response Caching Layer
"""

import pytest
import time
from utils.cache import InMemoryCache, cache_query_result, get_cached_query_result


class TestInMemoryCache:
    """Test InMemoryCache class"""
    
    def test_set_and_get(self):
        cache = InMemoryCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_miss(self):
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None
        assert cache.misses == 1
    
    def test_cache_hit(self):
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.get("key1")
        assert cache.hits == 1
    
    def test_ttl_expiration(self):
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl=1)  # 1 second TTL
        
        # Should be available immediately
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("key1") is None
    
    def test_lru_eviction(self):
        cache = InMemoryCache(max_size=3)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Cache is full, adding key4 should evict key1 (oldest)
        cache.set("key4", "value4")
        
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
        assert cache.evictions == 1
    
    def test_lru_access_order(self):
        cache = InMemoryCache(max_size=3)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to move it to end
        cache.get("key1")
        
        # Add key4, should evict key2 (now oldest)
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1"  # Still there
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_delete(self):
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None
    
    def test_clear(self):
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cleanup_expired(self):
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=10)
        
        time.sleep(1.1)
        cache.cleanup_expired()
        
        assert cache.get("key1") is None  # Expired and cleaned
        assert cache.get("key2") == "value2"  # Still valid
    
    def test_get_stats(self):
        cache = InMemoryCache(max_size=100)
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 100
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2
    
    def test_reset_stats(self):
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key2")
        
        cache.reset_stats()
        
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
    
    def test_cache_key_hashing(self):
        cache = InMemoryCache()
        
        # Same content should produce same hash
        cache.set("test query", "result1")
        assert cache.get("test query") == "result1"
        
        # Different content should produce different hash
        cache.set("different query", "result2")
        assert cache.get("different query") == "result2"
        assert cache.get("test query") == "result1"


class TestCacheHelpers:
    """Test cache helper functions"""
    
    def test_cache_query_result(self):
        cache_query_result("test query", {"result": "data"})
        result = get_cached_query_result("test query")
        assert result == {"result": "data"}
    
    def test_cache_query_miss(self):
        result = get_cached_query_result("nonexistent query")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
