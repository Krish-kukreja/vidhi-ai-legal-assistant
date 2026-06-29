"""
Rate limiting middleware to prevent API abuse and DoS attacks.

Implements token bucket algorithm with per-user and per-endpoint limits.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
import threading

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.

    Each user gets a bucket of tokens that refills over time.
    Each request consumes one token.
    """

    def __init__(self, requests_per_minute: int, burst_size: int = None):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Number of requests allowed per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)
        """
        self.rate = requests_per_minute / 60.0  # Tokens per second
        self.burst_size = burst_size or requests_per_minute
        self.buckets: Dict[str, Tuple[float, float]] = (
            {}
        )  # {key: (tokens, last_update)}
        self.lock = threading.Lock()

    def is_allowed(self, key: str) -> Tuple[bool, dict]:
        """
        Check if request is allowed.

        Args:
            key: Unique identifier (user_id, IP, etc.)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        with self.lock:
            now = time.time()

            if key not in self.buckets:
                # First request - initialize bucket
                self.buckets[key] = (self.burst_size - 1, now)
                return True, self._get_rate_limit_info(self.burst_size - 1, now)

            tokens, last_update = self.buckets[key]

            # Refill tokens based on time elapsed
            time_passed = now - last_update
            tokens = min(self.burst_size, tokens + time_passed * self.rate)

            if tokens >= 1:
                # Allow request and consume token
                self.buckets[key] = (tokens - 1, now)
                return True, self._get_rate_limit_info(tokens - 1, now)
            else:
                # Rate limit exceeded
                self.buckets[key] = (tokens, now)
                return False, self._get_rate_limit_info(tokens, now)

    def _get_rate_limit_info(self, tokens: float, last_update: float) -> dict:
        """Get rate limit information for headers."""
        return {
            "limit": int(self.burst_size),
            "remaining": int(tokens),
            "reset": int(last_update + (self.burst_size - tokens) / self.rate),
        }

    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        """Remove entries older than max_age_seconds."""
        with self.lock:
            now = time.time()
            keys_to_remove = [
                key
                for key, (_, last_update) in self.buckets.items()
                if now - last_update > max_age_seconds
            ]
            for key in keys_to_remove:
                del self.buckets[key]


# Rate limit configurations
RATE_LIMITS = {
    # Default limits
    "default": {
        "registered": 100,  # 100 requests per minute
        "guest": 20,  # 20 requests per minute
    },
    # Per-endpoint limits (more restrictive)
    "endpoints": {
        "/chat": {
            "registered": 60,  # 60 chat messages per minute
            "guest": 10,  # 10 chat messages per minute for guests
        },
        "/emergency": {
            "registered": 30,
            "guest": 10,
        },
        "/api/v1/documents/draft": {
            "registered": 20,  # Document generation is expensive
            "guest": 0,  # No guest access
        },
        "/api/v1/contracts/review": {
            "registered": 20,
            "guest": 0,
        },
    },
}

# Create rate limiters
rate_limiters = {
    "default_registered": RateLimiter(RATE_LIMITS["default"]["registered"]),
    "default_guest": RateLimiter(RATE_LIMITS["default"]["guest"]),
}

# Create per-endpoint rate limiters
for endpoint, limits in RATE_LIMITS["endpoints"].items():
    rate_limiters[f"{endpoint}_registered"] = RateLimiter(limits["registered"])
    rate_limiters[f"{endpoint}_guest"] = RateLimiter(limits["guest"])


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces rate limits on API endpoints.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for public endpoints
        if self._is_exempt_endpoint(request.url.path):
            return await call_next(request)

        # Get user identifier
        user_id = getattr(request.state, "user_id", None)
        user_type = getattr(request.state, "user_type", "guest")

        # Use IP as fallback if no user_id
        if not user_id:
            user_id = self._get_client_ip(request)
            user_type = "guest"

        # Get appropriate rate limiter
        limiter, limiter_key = self._get_rate_limiter(request.url.path, user_type)

        # Check rate limit
        is_allowed, rate_info = limiter.is_allowed(f"{limiter_key}:{user_id}")

        if not is_allowed:
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for {user_id} on {request.url.path}")
            return self._rate_limit_response(rate_info)

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

        return response

    def _is_exempt_endpoint(self, path: str) -> bool:
        """Check if endpoint is exempt from rate limiting."""
        exempt_endpoints = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

        # Exact match
        if path in exempt_endpoints:
            return True

        # Prefix match
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True

        return False

    def _get_rate_limiter(self, path: str, user_type: str) -> Tuple[RateLimiter, str]:
        """Get appropriate rate limiter for endpoint and user type."""
        # Check for endpoint-specific limiter
        if path in RATE_LIMITS["endpoints"]:
            limiter_key = f"{path}_{user_type}"
            if limiter_key in rate_limiters:
                return rate_limiters[limiter_key], limiter_key

        # Use default limiter
        limiter_key = f"default_{user_type}"
        return rate_limiters[limiter_key], limiter_key

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check X-Forwarded-For header (for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Use direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _rate_limit_response(self, rate_info: dict):
        """Return 429 Too Many Requests response."""
        retry_after = rate_info["reset"] - int(time.time())

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded",
                "error": "too_many_requests",
                "limit": rate_info["limit"],
                "retry_after": max(1, retry_after),
                "hint": "Please wait before making more requests",
            },
            headers={
                "Retry-After": str(max(1, retry_after)),
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_info["reset"]),
            },
        )


# Cleanup task (run periodically to remove old entries)
def cleanup_rate_limiters():
    """Clean up old rate limiter entries."""
    for limiter in rate_limiters.values():
        limiter.cleanup_old_entries()


# Optional: Schedule cleanup task
try:
    import threading
    import time as time_module

    def cleanup_loop():
        while True:
            time_module.sleep(3600)  # Run every hour
            cleanup_rate_limiters()

    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
except Exception as e:
    logger.warning(f"Could not start rate limiter cleanup thread: {e}")
