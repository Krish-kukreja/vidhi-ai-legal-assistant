"""
Error handling middleware for VIDHI API.

Catches all exceptions and returns consistent error responses.
Integrates with Sentry for error tracking.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from utils.logging_config import generate_request_id

logger = logging.getLogger(__name__)

# Import monitoring (optional)
try:
    from utils.monitoring import monitoring

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logger.warning("Monitoring not available")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches all exceptions and returns consistent error responses.
    """

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = generate_request_id()
        request.state.request_id = request_id

        try:
            # Process request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Log the exception with full context
            logger.error(
                f"Unhandled exception in {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "user_id": getattr(request.state, "user_id", None),
                    "endpoint": request.url.path,
                    "method": request.method,
                    "extra_data": {
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                },
            )

            # Capture exception in monitoring (Sentry)
            if MONITORING_AVAILABLE:
                try:
                    monitoring.capture_exception(
                        exc,
                        context={
                            "endpoint": request.url.path,
                            "method": request.method,
                            "request_id": request_id,
                        },
                        user={
                            "user_id": getattr(request.state, "user_id", None),
                            "user_type": getattr(request.state, "user_type", None),
                        },
                        tags={
                            "endpoint": request.url.path,
                            "method": request.method,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to capture exception in monitoring: {e}")

            # Return error response
            return self._create_error_response(exc, request_id)

    def _create_error_response(self, exc: Exception, request_id: str) -> JSONResponse:
        """Create a consistent error response."""
        # Determine status code and error type
        if isinstance(exc, ValueError):
            status_code = status.HTTP_400_BAD_REQUEST
            error_type = "validation_error"
        elif isinstance(exc, PermissionError):
            status_code = status.HTTP_403_FORBIDDEN
            error_type = "permission_denied"
        elif isinstance(exc, FileNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
            error_type = "not_found"
        elif isinstance(exc, TimeoutError):
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
            error_type = "timeout"
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_type = "internal_error"

        # Create error response
        error_response = {
            "error": error_type,
            "message": str(exc),
            "request_id": request_id,
            "hint": self._get_error_hint(error_type),
        }

        # Add traceback in development mode (not in production!)
        # In production, only log traceback, don't send to client
        import os

        if os.getenv("ENVIRONMENT", "development") == "development":
            error_response["traceback"] = traceback.format_exc()

        return JSONResponse(
            status_code=status_code,
            content=error_response,
            headers={"X-Request-ID": request_id},
        )

    def _get_error_hint(self, error_type: str) -> str:
        """Get a helpful hint for the error type."""
        hints = {
            "validation_error": "Please check your input and try again",
            "permission_denied": "You don't have permission to access this resource",
            "not_found": "The requested resource was not found",
            "timeout": "The request took too long to process. Please try again",
            "internal_error": "An unexpected error occurred. Please try again later",
        }
        return hints.get(error_type, "Please contact support if the problem persists")


def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    request_id: str = None,
    details: dict = None,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        error_type: Error type identifier
        message: Human-readable error message
        request_id: Optional request ID
        details: Optional additional details

    Returns:
        JSONResponse with error details
    """
    response_data = {
        "error": error_type,
        "message": message,
    }

    if request_id:
        response_data["request_id"] = request_id

    if details:
        response_data["details"] = details

    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id

    return JSONResponse(status_code=status_code, content=response_data, headers=headers)
