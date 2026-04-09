import hashlib
import hmac
import json
import base64
import time
import secrets
from typing import Dict, Any, Optional
from services.database import get_db

SECRET_KEY = b"hackathon_vidhi_super_secret_key_2026"

def hash_password(password: str, salt: str = None) -> str:
    """Hashes a password with a random salt."""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${pwd_hash.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored hash."""
    if "$" not in hashed_password:
        return False
    salt, hash_val = hashed_password.split("$", 1)
    return hash_password(plain_password, salt) == hashed_password

def create_jwt_like_token(payload: dict, expires_in_sec: int = 86400) -> str:
    """Creates a basic HMAC token carrying a JSON payload (simulating JWT for MVP)."""
    payload['exp'] = int(time.time()) + expires_in_sec
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    msg = f"{header}.{payload_b64}"
    signature = hmac.new(SECRET_KEY, msg.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{msg}.{sig_b64}"

def verify_token(token: str) -> Optional[dict]:
    """Verifies the HMAC token and returns the payload if valid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload_b64, sig_b64 = parts
        msg = f"{header}.{payload_b64}"
        signature = hmac.new(SECRET_KEY, msg.encode(), hashlib.sha256).digest()
        expected_sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        
        if not hmac.compare_digest(sig_b64, expected_sig):
            return None
            
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "==").decode())
        if payload.get('exp', 0) < time.time():
            return None # Expired
        return payload
    except Exception:
        return None

def register_user(email: str, password: str, name: str) -> Dict[str, Any]:
    with get_db() as db:
        # Check if exists
        user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            return {"success": False, "error": "Email already registered"}
        
        hashed = hash_password(password)
        cursor = db.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email, hashed, name)
        )
        db.commit()
        
        # Auto-create a default matter
        user_id = cursor.lastrowid
        db.execute(
            "INSERT INTO matters (user_id, name, description) VALUES (?, ?, ?)",
            (user_id, "General Legal Queries", "Default workspace for generic questions")
        )
        db.commit()
        
        token = create_jwt_like_token({"sub": user_id, "email": email, "name": name})
        return {"success": True, "token": token, "user_id": user_id, "name": name}

def login_user(email: str, password: str) -> Dict[str, Any]:
    with get_db() as db:
        user = db.execute("SELECT id, email, password_hash, name FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not verify_password(password, user['password_hash']):
            return {"success": False, "error": "Invalid email or password"}
        
        token = create_jwt_like_token({"sub": user['id'], "email": user['email'], "name": user['name']})
        return {"success": True, "token": token, "user_id": user['id'], "name": user['name']}
