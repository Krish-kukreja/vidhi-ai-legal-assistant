"""
Authentication middleware for VIDHI API.

Supports multiple authentication methods:
1. JWT tokens for registered users
2. API keys for service-to-service calls
3. Guest mode for anonymous users (rate-limited)

Integrates with monitoring for user context tracking.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Import monitoring (optional)
try:
    from utils.monitoring import monitoring

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Token issuing + verification lives in services/authentication.py (single source
# of truth). This middleware only *verifies* tokens, via _verify_jwt below.

# API Key Configuration
VALID_API_KEYS = (
    set(os.getenv("API_KEYS", "").split(",")) if os.getenv("API_KEYS") else set()
)

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/guest",
    "/languages",
    "/api/v1/languages/supported",
}

# Endpoints that allow guest access (but track for rate limiting)
GUEST_ALLOWED_ENDPOINTS = {
    "/chat",
    "/clear-session",
    "/emergency",
}

# Path prefixes open to guests. These cover the public-facing product features
# (document education, drafting, contract review, live research, SSE streaming,
# and chat history). NOTE: "/api/v1/matters" is deliberately NOT here — matter
# workspaces require an authenticated (logged-in) user.
GUEST_ALLOWED_PREFIXES = (
    "/api/v1/documents/",
    "/api/v1/history/",
    "/api/v1/research/",
    "/api/v1/contracts/",
    "/api/v1/stream/",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces authentication on protected endpoints.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        # Try to authenticate
        auth_result = await self._authenticate(request)

        if not auth_result["authenticated"]:
            # Check if guest access is allowed
            if self._allows_guest_access(request.url.path):
                # Mark as guest user for rate limiting
                request.state.user_id = "guest"
                request.state.user_type = "guest"
                request.state.is_authenticated = False

                # Set guest user context in monitoring
                if MONITORING_AVAILABLE:
                    try:
                        monitoring.set_user({"user_id": "guest", "user_type": "guest"})
                    except:
                        pass
            else:
                # Reject request
                return self._unauthorized_response(
                    auth_result.get("error", "Authentication required")
                )
        else:
            # Set user info in request state
            request.state.user_id = auth_result["user_id"]
            request.state.user_type = auth_result["user_type"]
            request.state.is_authenticated = True
            request.state.user_data = auth_result.get("user_data", {})

            # Set user context in monitoring
            if MONITORING_AVAILABLE:
                try:
                    monitoring.set_user(
                        {
                            "user_id": auth_result["user_id"],
                            "user_type": auth_result["user_type"],
                        }
                    )
                except:
                    pass

        response = await call_next(request)
        return response

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public."""
        # Exact match
        if path in PUBLIC_ENDPOINTS:
            return True

        # Prefix match for docs
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True

        return False

    def _allows_guest_access(self, path: str) -> bool:
        """Check if endpoint allows guest access (exact match or allowed prefix)."""
        if path in GUEST_ALLOWED_ENDPOINTS:
            return True
        return any(path.startswith(prefix) for prefix in GUEST_ALLOWED_PREFIXES)

    async def _authenticate(self, request: Request) -> dict:
        """
        Try multiple authentication methods in order:
        1. JWT token (Authorization: Bearer <token>)
        2. API key (X-API-Key header)
        3. Guest mode (if allowed)
        """
        # Try JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            jwt_result = self._verify_jwt(token)
            if jwt_result["valid"]:
                return {
                    "authenticated": True,
                    "user_id": jwt_result["user_id"],
                    "user_type": "registered",
                    "user_data": jwt_result.get("data", {}),
                }

        # Try API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            if self._verify_api_key(api_key):
                return {
                    "authenticated": True,
                    "user_id": f"api_key_{api_key[:8]}",
                    "user_type": "service",
                    "user_data": {"api_key": api_key[:8]},
                }

        # No valid authentication
        return {
            "authenticated": False,
            "error": "Invalid or missing authentication credentials",
        }

    def _verify_jwt(self, token: str) -> dict:
        """
        Verify the access token.

        The login/register endpoints (app.py -> services/authentication.py) issue a
        signed HMAC token, so we validate against the SAME implementation here.
        This keeps the middleware, the login route, and the per-route
        get_current_user dependency all using one signing key + format.
        """
        try:
            from services.authentication import verify_token as verify_hmac_token

            payload = verify_hmac_token(token)
            if not payload:
                return {"valid": False, "error": "Invalid or expired token"}

            user_id = payload.get("sub")
            if user_id is None:
                return {"valid": False, "error": "Invalid token payload"}

            return {"valid": True, "user_id": user_id, "data": payload}

        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return {"valid": False, "error": "Invalid token"}

    def _verify_api_key(self, api_key: str) -> bool:
        """Verify API key."""
        if not VALID_API_KEYS:
            # No API keys configured, reject
            return False

        return api_key in VALID_API_KEYS

    def _unauthorized_response(self, message: str):
        """Return 401 Unauthorized response."""
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": message,
                "error": "unauthorized",
                "hint": "Please provide valid authentication credentials (JWT token or API key)",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


# Utility functions for reading the authenticated user off the request state.
# (Token creation/verification intentionally lives only in services/authentication.py.)


def get_current_user(request: Request) -> dict:
    """
    Get current user from request state.

    Args:
        request: FastAPI request object

    Returns:
        User info dictionary

    Raises:
        HTTPException if not authenticated
    """
    if not getattr(request.state, "is_authenticated", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return {
        "user_id": request.state.user_id,
        "user_type": request.state.user_type,
        "user_data": getattr(request.state, "user_data", {}),
    }


def require_auth(request: Request):
    """
    Dependency that requires authentication.
    Use in endpoint: def my_endpoint(user: dict = Depends(require_auth))
    """
    return get_current_user(request)


def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Get current user from request state (optional - returns None if not authenticated).

    This is useful for endpoints that work for both authenticated and guest users.

    Args:
        request: FastAPI request object

    Returns:
        User info dictionary if authenticated, None otherwise
    """
    if not getattr(request.state, "is_authenticated", False):
        return None

    return {
        "user_id": request.state.user_id,
        "user_type": request.state.user_type,
        "user_data": getattr(request.state, "user_data", {}),
    }
