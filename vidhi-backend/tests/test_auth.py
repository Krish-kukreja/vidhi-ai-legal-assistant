"""
Tests for authentication middleware and service.
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from middleware.auth_middleware import AuthMiddleware, create_access_token, verify_token
from services.auth_service import (
    hash_password,
    verify_password,
    register_user,
    login_user,
    create_guest_token,
    USERS_DB
)


# Test app
app = FastAPI()
app.add_middleware(AuthMiddleware)


@app.get("/public")
async def public_endpoint():
    return {"message": "public"}


@app.get("/protected")
async def protected_endpoint(request: Request):
    return {
        "message": "protected",
        "user_id": request.state.user_id,
        "user_type": request.state.user_type
    }


@app.get("/chat")
async def guest_allowed_endpoint(request: Request):
    return {
        "message": "guest_allowed",
        "user_id": getattr(request.state, "user_id", None),
        "is_authenticated": getattr(request.state, "is_authenticated", False)
    }


client = TestClient(app)


class TestPasswordHashing:
    def test_hash_password(self):
        password = "test_password_123"
        hash1, salt1 = hash_password(password)
        hash2, salt2 = hash_password(password)
        
        # Different salts should produce different hashes
        assert hash1 != hash2
        assert salt1 != salt2
    
    def test_verify_password_correct(self):
        password = "test_password_123"
        password_hash, salt = hash_password(password)
        
        assert verify_password(password, password_hash, salt) is True
    
    def test_verify_password_incorrect(self):
        password = "test_password_123"
        wrong_password = "wrong_password"
        password_hash, salt = hash_password(password)
        
        assert verify_password(wrong_password, password_hash, salt) is False


class TestUserRegistration:
    def setup_method(self):
        # Clear users before each test
        USERS_DB.clear()
    
    def test_register_new_user(self):
        result = register_user(
            user_id="test_user_1",
            password="password123",
            email="test@example.com",
            name="Test User"
        )
        
        assert result["user_id"] == "test_user_1"
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert "access_token" in result
        assert result["token_type"] == "bearer"
    
    def test_register_duplicate_user(self):
        register_user("test_user_1", "password123")
        
        with pytest.raises(ValueError, match="User already exists"):
            register_user("test_user_1", "password456")
    
    def test_password_not_stored_plaintext(self):
        password = "secret_password_123"
        register_user("test_user_1", password)
        
        user_record = USERS_DB["test_user_1"]
        assert user_record["password_hash"] != password
        assert "salt" in user_record


class TestUserLogin:
    def setup_method(self):
        USERS_DB.clear()
        # Register a test user
        register_user(
            user_id="test_user_1",
            password="password123",
            email="test@example.com"
        )
    
    def test_login_success(self):
        result = login_user("test_user_1", "password123")
        
        assert result["user_id"] == "test_user_1"
        assert "access_token" in result
        assert result["token_type"] == "bearer"
    
    def test_login_wrong_password(self):
        with pytest.raises(ValueError, match="Invalid credentials"):
            login_user("test_user_1", "wrong_password")
    
    def test_login_nonexistent_user(self):
        with pytest.raises(ValueError, match="Invalid credentials"):
            login_user("nonexistent_user", "password123")


class TestJWTTokens:
    def test_create_and_verify_token(self):
        user_id = "test_user_123"
        token = create_access_token(user_id)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert "exp" in payload
        assert "iat" in payload
    
    def test_verify_invalid_token(self):
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    def test_token_with_additional_data(self):
        user_id = "test_user_123"
        additional_data = {"user_type": "lawyer", "name": "John Doe"}
        
        token = create_access_token(user_id, additional_data)
        payload = verify_token(token)
        
        assert payload["user_type"] == "lawyer"
        assert payload["name"] == "John Doe"


class TestAuthMiddleware:
    def test_public_endpoint_no_auth(self):
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json()["message"] == "public"
    
    def test_protected_endpoint_no_auth(self):
        response = client.get("/protected")
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_protected_endpoint_with_valid_token(self):
        token = create_access_token("test_user_123")
        
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["user_id"] == "test_user_123"
        assert response.json()["user_type"] == "registered"
    
    def test_protected_endpoint_with_invalid_token(self):
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_guest_allowed_endpoint_no_auth(self):
        response = client.get("/chat")
        
        # Should allow access but mark as guest
        assert response.status_code == 200
        assert response.json()["user_id"] == "guest"
        assert response.json()["is_authenticated"] is False
    
    def test_guest_allowed_endpoint_with_auth(self):
        token = create_access_token("test_user_123")
        
        response = client.get(
            "/chat",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["user_id"] == "test_user_123"
        assert response.json()["is_authenticated"] is True


class TestGuestToken:
    def test_create_guest_token(self):
        session_id = "session_123"
        token = create_guest_token(session_id)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == f"guest_{session_id}"
        assert payload["user_type"] == "guest"
        assert payload["is_guest"] is True
