"""
Authentication API routes.
"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
from services.auth_service import register_user, login_user, create_guest_token, get_user_info
from middleware.auth_middleware import require_auth
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# Request/Response models

class RegisterRequest(BaseModel):
    user_id: str  # Aadhaar, phone, or email
    password: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    user_type: str = "individual"  # individual, lawyer, organization


class LoginRequest(BaseModel):
    user_id: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    email: Optional[str]
    phone: Optional[str]
    name: Optional[str]
    user_type: str
    access_token: str
    token_type: str


class GuestRequest(BaseModel):
    session_id: str


class GuestResponse(BaseModel):
    session_id: str
    access_token: str
    token_type: str
    message: str


# Routes

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    Register a new user.
    
    Supports multiple user types:
    - individual: Regular citizen
    - lawyer: Legal professional
    - organization: NGO, legal aid organization
    """
    try:
        result = register_user(
            user_id=request.user_id,
            password=request.password,
            email=request.email,
            phone=request.phone,
            name=request.name,
            user_type=request.user_type
        )
        
        return AuthResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate a user and return access token.
    """
    try:
        result = login_user(
            user_id=request.user_id,
            password=request.password
        )
        
        return AuthResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/guest", response_model=GuestResponse)
async def guest_access(request: GuestRequest):
    """
    Create a temporary guest token for anonymous users.
    
    Guest users have limited access and are subject to stricter rate limits.
    """
    try:
        token = create_guest_token(request.session_id)
        
        return GuestResponse(
            session_id=request.session_id,
            access_token=token,
            token_type="bearer",
            message="Guest access granted. Register for full features."
        )
    
    except Exception as e:
        logger.error(f"Guest token error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create guest token"
        )


@router.get("/me")
async def get_current_user_info(request: Request):
    """
    Get current authenticated user's information.
    
    Requires authentication.
    """
    try:
        # Get user from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        
        if not user_id or not getattr(request.state, "is_authenticated", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        # Get user info
        user_info = get_user_info(user_id)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user_info
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user info"
        )


@router.post("/logout")
async def logout(request: Request):
    """
    Logout current user.
    
    Note: JWT tokens are stateless, so logout is handled client-side
    by discarding the token. This endpoint is provided for consistency.
    """
    return {
        "message": "Logged out successfully",
        "hint": "Please discard your access token on the client side"
    }
