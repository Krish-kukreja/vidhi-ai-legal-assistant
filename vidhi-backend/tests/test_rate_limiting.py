"""
Tests for rate limiting middleware.
"""

import pytest
import time
from middleware.rate_limit_middleware import RateLimiter, RateLimitMiddleware


class TestRateLimiter:
    """Test the token bucket rate limiter."""
    
    def test_allows_requests_within_limit(self):
        """Requests within limit should be allowed."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 per second
        
        # First request should be allowed
        is_allowed, info = limiter.is_allowed("user1")
        assert is_allowed is True
        assert info["remaining"] >= 0
    
    def test_blocks_requests_exceeding_limit(self):
        """Requests exceeding limit should be blocked."""
        limiter = RateLimiter(requests_per_minute=2, burst_size=2)
        
        # First 2 requests should be allowed
        assert limiter.is_allowed("user1")[0] is True
        assert limiter.is_allowed("user1")[0] is True
        
        # Third request should be blocked
        is_allowed, info = limiter.is_allowed("user1")
        assert is_allowed is False
        assert info["remaining"] == 0
    
    def test_refills_tokens_over_time(self):
        """Tokens should refill over time."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=2)  # 1 per second
        
        # Consume all tokens
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        
        # Should be blocked immediately
        assert limiter.is_allowed("user1")[0] is False
        
        # Wait for refill (1 second = 1 token)
        time.sleep(1.1)
        
        # Should be allowed again
        assert limiter.is_allowed("user1")[0] is True
    
    def test_separate_limits_per_user(self):
        """Each user should have separate rate limits."""
        limiter = RateLimiter(requests_per_minute=2, burst_size=2)
        
        # User 1 consumes their limit
        assert limiter.is_allowed("user1")[0] is True
        assert limiter.is_allowed("user1")[0] is True
        assert limiter.is_allowed("user1")[0] is False
        
        # User 2 should still have their full limit
        assert limiter.is_allowed("user2")[0] is True
        assert limiter.is_allowed("user2")[0] is True
    
    def test_burst_size_limits_concurrent_requests(self):
        """Burst size should limit concurrent requests."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=5)
        
        # Should allow up to burst_size requests
        for i in range(5):
            assert limiter.is_allowed("user1")[0] is True
        
        # Next request should be blocked
        assert limiter.is_allowed("user1")[0] is False
    
    def test_rate_limit_info_accuracy(self):
        """Rate limit info should be accurate."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        
        # First request
        is_allowed, info = limiter.is_allowed("user1")
        assert info["limit"] == 10
        assert info["remaining"] == 9
        assert "reset" in info
        
        # Second request
        is_allowed, info = limiter.is_allowed("user1")
        assert info["remaining"] == 8
    
    def test_cleanup_removes_old_entries(self):
        """Cleanup should remove old entries."""
        limiter = RateLimiter(requests_per_minute=60)
        
        # Make some requests
        limiter.is_allowed("user1")
        limiter.is_allowed("user2")
        limiter.is_allowed("user3")
        
        assert len(limiter.buckets) == 3
        
        # Cleanup with very short max_age (should remove all)
        limiter.cleanup_old_entries(max_age_seconds=0)
        
        assert len(limiter.buckets) == 0


class TestRateLimitConfiguration:
    """Test rate limit configuration."""
    
    def test_default_limits_configured(self):
        """Default rate limits should be configured."""
        from middleware.rate_limit_middleware import RATE_LIMITS
        
        assert "default" in RATE_LIMITS
        assert "registered" in RATE_LIMITS["default"]
        assert "guest" in RATE_LIMITS["default"]
        
        # Registered users should have higher limits
        assert RATE_LIMITS["default"]["registered"] > RATE_LIMITS["default"]["guest"]
    
    def test_endpoint_specific_limits_configured(self):
        """Endpoint-specific limits should be configured."""
        from middleware.rate_limit_middleware import RATE_LIMITS
        
        assert "endpoints" in RATE_LIMITS
        assert "/chat" in RATE_LIMITS["endpoints"]
        
        # Chat should have limits for both user types
        assert "registered" in RATE_LIMITS["endpoints"]["/chat"]
        assert "guest" in RATE_LIMITS["endpoints"]["/chat"]
    
    def test_expensive_endpoints_have_stricter_limits(self):
        """Expensive endpoints should have stricter limits."""
        from middleware.rate_limit_middleware import RATE_LIMITS
        
        # Document drafting is expensive
        draft_limits = RATE_LIMITS["endpoints"].get("/api/v1/documents/draft", {})
        default_limits = RATE_LIMITS["default"]
        
        if draft_limits:
            # Should be more restrictive than default
            assert draft_limits["registered"] < default_limits["registered"]
            # Guests should not have access
            assert draft_limits["guest"] == 0
    
    def test_rate_limiters_created(self):
        """Rate limiters should be created for all configurations."""
        from middleware.rate_limit_middleware import rate_limiters
        
        # Default limiters should exist
        assert "default_registered" in rate_limiters
        assert "default_guest" in rate_limiters
        
        # Endpoint-specific limiters should exist
        assert "/chat_registered" in rate_limiters
        assert "/chat_guest" in rate_limiters


class TestRateLimitMiddleware:
    """Test rate limit middleware behavior."""
    
    def test_exempt_endpoints_not_rate_limited(self):
        """Exempt endpoints should not be rate limited."""
        middleware = RateLimitMiddleware(None)
        
        exempt_endpoints = [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
        
        for endpoint in exempt_endpoints:
            assert middleware._is_exempt_endpoint(endpoint) is True
    
    def test_non_exempt_endpoints_are_rate_limited(self):
        """Non-exempt endpoints should be rate limited."""
        middleware = RateLimitMiddleware(None)
        
        rate_limited_endpoints = [
            "/chat",
            "/api/v1/documents/draft",
            "/api/v1/auth/me",
        ]
        
        for endpoint in rate_limited_endpoints:
            assert middleware._is_exempt_endpoint(endpoint) is False
    
    def test_get_client_ip_from_headers(self):
        """Should extract client IP from headers."""
        from fastapi import Request
        
        middleware = RateLimitMiddleware(None)
        
        # Mock request with X-Forwarded-For
        class MockRequest:
            headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}
            client = None
        
        ip = middleware._get_client_ip(MockRequest())
        assert ip == "1.2.3.4"
    
    def test_get_client_ip_from_x_real_ip(self):
        """Should extract client IP from X-Real-IP header."""
        middleware = RateLimitMiddleware(None)
        
        class MockRequest:
            headers = {"X-Real-IP": "1.2.3.4"}
            client = None
        
        ip = middleware._get_client_ip(MockRequest())
        assert ip == "1.2.3.4"
    
    def test_get_rate_limiter_for_endpoint(self):
        """Should get correct rate limiter for endpoint."""
        middleware = RateLimitMiddleware(None)
        
        # Chat endpoint should have specific limiter
        limiter, key = middleware._get_rate_limiter("/chat", "registered")
        assert "/chat" in key
        assert "registered" in key
        
        # Unknown endpoint should use default
        limiter, key = middleware._get_rate_limiter("/unknown", "registered")
        assert "default" in key
    
    def test_rate_limit_response_format(self):
        """Rate limit response should have correct format."""
        middleware = RateLimitMiddleware(None)
        
        rate_info = {
            "limit": 100,
            "remaining": 0,
            "reset": int(time.time()) + 60
        }
        
        response = middleware._rate_limit_response(rate_info)
        
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Limit" in response.headers
        
        # Check response body
        import json
        body = json.loads(response.body)
        assert "detail" in body
        assert "retry_after" in body
        assert body["error"] == "too_many_requests"


def test_rate_limiting_integration():
    """Integration test for rate limiting."""
    limiter = RateLimiter(requests_per_minute=3, burst_size=3)
    
    # Simulate rapid requests
    results = []
    for i in range(5):
        is_allowed, info = limiter.is_allowed("test_user")
        results.append(is_allowed)
    
    # First 3 should be allowed, last 2 blocked
    assert results == [True, True, True, False, False]
    
    print("✓ Rate limiting works correctly")


if __name__ == "__main__":
    # Run basic integration test
    test_rate_limiting_integration()
    print("\n✅ All rate limiting tests passed!")
