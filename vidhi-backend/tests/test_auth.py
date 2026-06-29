"""
Tests for the unified authentication system.

The app uses ONE token scheme: a signed-HMAC token issued by
services/authentication.py and verified by both AuthMiddleware and the per-route
get_current_user dependency. (The old in-memory jose system was removed.)
"""

import os
import tempfile
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import services.database as database
import services.authentication as auth


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    """Use an isolated temp SQLite DB for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(database, "DB_PATH", path)
    database.init_db()
    yield
    try:
        os.remove(path)
    except OSError:
        pass


# ── Password hashing ──────────────────────────────────────────────
def test_hash_is_salted_and_verifies():
    h1 = auth.hash_password("pw123456")
    h2 = auth.hash_password("pw123456")
    assert h1 != h2  # random salt -> different hashes
    assert auth.verify_password("pw123456", h1)
    assert not auth.verify_password("wrong", h1)


# ── Register / login ──────────────────────────────────────────────
def test_register_and_login():
    r = auth.register_user("a@law.com", "pw123456", "Counsel")
    assert r["success"] and r["token"]

    dup = auth.register_user("a@law.com", "pw123456", "Counsel")
    assert not dup["success"]  # duplicate email rejected

    li = auth.login_user("a@law.com", "pw123456")
    assert li["success"] and li["token"]

    bad = auth.login_user("a@law.com", "nope")
    assert not bad["success"]  # wrong password rejected


# ── Token round-trip ──────────────────────────────────────────────
def test_token_roundtrip():
    tok = auth.create_jwt_like_token({"sub": 7, "email": "a@law.com"})
    payload = auth.verify_token(tok)
    assert payload and payload["sub"] == 7
    assert auth.verify_token("garbage.token.here") is None
    assert auth.verify_token(tok + "tampered") is None


# ── AuthMiddleware behaviour ──────────────────────────────────────
def _build_app():
    from middleware.auth_middleware import AuthMiddleware

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/chat")  # guest-allowed
    async def chat(request: Request):
        return {
            "user_id": getattr(request.state, "user_id", None),
            "auth": getattr(request.state, "is_authenticated", False),
        }

    @app.get("/api/v1/matters")  # protected (not guest-allowed)
    async def matters(request: Request):
        return {"user_id": request.state.user_id}

    return app


def test_guest_allowed_endpoint_open():
    client = TestClient(_build_app())
    r = client.get("/chat")
    assert r.status_code == 200
    assert r.json()["auth"] is False


def test_protected_requires_token():
    client = TestClient(_build_app())
    assert client.get("/api/v1/matters").status_code == 401


def test_protected_accepts_issued_token():
    client = TestClient(_build_app())
    tok = auth.create_jwt_like_token({"sub": 42, "email": "a@law.com"})
    r = client.get("/api/v1/matters", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["user_id"] == 42
