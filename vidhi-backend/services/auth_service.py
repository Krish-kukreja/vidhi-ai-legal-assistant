"""
Authentication service for user registration and login.
"""

import hashlib
import secrets
import logging
from datetime import datetime
from typing import Optional
from middleware.auth_middleware import create_access_token

logger = logging.getLogger(__name__)

# In-memory user store (replace with database in production)
# Format: {user_id: {password_hash, email, phone, created_at, ...}}
USERS_DB = {}


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """
    Hash a password with salt.
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (password_hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Use SHA-256 with salt
    password_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return password_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Stored password hash
        salt: Salt used for hashing
        
    Returns:
        True if password matches, False otherwise
    """
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == password_hash


def register_user(
    user_id: str,
    password: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    name: Optional[str] = None,
    user_type: str = "individual"
) -> dict:
    """
    Register a new user.
    
    Args:
        user_id: Unique user identifier (Aadhaar, phone, email)
        password: User password
        email: Email address
        phone: Phone number
        name: User's name
        user_type: Type of user (individual, lawyer, organization)
        
    Returns:
        Dictionary with user info and access token
        
    Raises:
        ValueError if user already exists
    """
    # Check if user exists
    if user_id in USERS_DB:
        raise ValueError("User already exists")
    
    # Hash password
    password_hash, salt = hash_password(password)
    
    # Create user record
    user_record = {
        "user_id": user_id,
        "password_hash": password_hash,
        "salt": salt,
        "email": email,
        "phone": phone,
        "name": name,
        "user_type": user_type,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True
    }
    
    # Store user
    USERS_DB[user_id] = user_record
    
    logger.info(f"User registered: {user_id} (type: {user_type})")
    
    # Create access token
    token = create_access_token(
        user_id=user_id,
        additional_data={
            "user_type": user_type,
            "name": name
        }
    )
    
    return {
        "user_id": user_id,
        "email": email,
        "phone": phone,
        "name": name,
        "user_type": user_type,
        "access_token": token,
        "token_type": "bearer"
    }


def login_user(user_id: str, password: str) -> dict:
    """
    Authenticate a user and return access token.
    
    Args:
        user_id: User identifier
        password: User password
        
    Returns:
        Dictionary with user info and access token
        
    Raises:
        ValueError if authentication fails
    """
    # Check if user exists
    if user_id not in USERS_DB:
        raise ValueError("Invalid credentials")
    
    user_record = USERS_DB[user_id]
    
    # Check if user is active
    if not user_record.get("is_active", True):
        raise ValueError("User account is disabled")
    
    # Verify password
    if not verify_password(password, user_record["password_hash"], user_record["salt"]):
        raise ValueError("Invalid credentials")
    
    logger.info(f"User logged in: {user_id}")
    
    # Create access token
    token = create_access_token(
        user_id=user_id,
        additional_data={
            "user_type": user_record.get("user_type", "individual"),
            "name": user_record.get("name")
        }
    )
    
    return {
        "user_id": user_id,
        "email": user_record.get("email"),
        "phone": user_record.get("phone"),
        "name": user_record.get("name"),
        "user_type": user_record.get("user_type", "individual"),
        "access_token": token,
        "token_type": "bearer"
    }


def create_guest_token(session_id: str) -> str:
    """
    Create a temporary token for guest users.
    
    Args:
        session_id: Guest session identifier
        
    Returns:
        JWT token for guest access
    """
    token = create_access_token(
        user_id=f"guest_{session_id}",
        additional_data={
            "user_type": "guest",
            "is_guest": True
        }
    )
    
    return token


def get_user_info(user_id: str) -> Optional[dict]:
    """
    Get user information.
    
    Args:
        user_id: User identifier
        
    Returns:
        User info dictionary (without sensitive data) or None if not found
    """
    if user_id not in USERS_DB:
        return None
    
    user_record = USERS_DB[user_id]
    
    # Return user info without sensitive data
    return {
        "user_id": user_id,
        "email": user_record.get("email"),
        "phone": user_record.get("phone"),
        "name": user_record.get("name"),
        "user_type": user_record.get("user_type", "individual"),
        "created_at": user_record.get("created_at"),
        "is_active": user_record.get("is_active", True)
    }


def generate_api_key() -> str:
    """
    Generate a new API key for service-to-service authentication.
    
    Returns:
        API key string
    """
    return f"vidhi_{secrets.token_urlsafe(32)}"
