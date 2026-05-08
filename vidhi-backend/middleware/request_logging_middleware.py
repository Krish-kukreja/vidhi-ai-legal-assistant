"""
Request logging middleware for VIDHI API.

Logs all incoming requests and outgoing responses with timing information.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from utils.logging_config import get_logger

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests and responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()
        
        # Get request info
        request_id = getattr(request.state, "request_id", "unknown")
        user_id = getattr(request.state, "user_id", None)
        method = request.method
        path = request.url.path
        
        # Log incoming request
        logger.info(
            f"Incoming request: {method} {path}",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "endpoint": path,
                "extra_data": {
                    "method": method,
                    "query_params": dict(request.query_params),
                    "client_ip": self._get_client_ip(request),
                }
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(
            log_level,
            f"Response: {method} {path} - {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "endpoint": path,
                "extra_data": {
                    "method": method,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            }
        )
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response
    
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
