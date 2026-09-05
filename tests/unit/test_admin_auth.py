"""Tests for admin auth — login, token validation, /me endpoint."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.api.auth import create_access_token, decode_access_token
from app.api.main import app
from app.shared.config import settings


@pytest.fixture(autouse=True)
def _mock_admin_credentials():
    """Ensure test admin credentials are set."""
    with patch.object(settings, "ADMIN_USERNAME", "testadmin"), patch.object(
        settings, "ADMIN_PASSWORD", "testpass123"
    ):
        yield


# --- Test 1: Login success ---
@pytest.mark.asyncio
async def test_login_success():
    """POST /api/admin/auth/login with valid credentials returns 200 + access_token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/auth/login",
            json={"username": "testadmin", "password": "testpass123"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# --- Test 2: Login failure ---
@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """POST /api/admin/auth/login with invalid credentials returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/auth/login",
            json={"username": "wrong", "password": "wrong"},
        )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


# --- Test 3: /me with valid token ---
@pytest.mark.asyncio
async def test_me_valid_token():
    """GET /api/admin/auth/me with valid JWT returns 200 + user info."""
    token = create_access_token(data={"sub": "testadmin", "role": "admin"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/admin/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"


# --- Test 4: /me without token ---
@pytest.mark.asyncio
async def test_me_no_token():
    """GET /api/admin/auth/me without token returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/admin/auth/me")
    assert response.status_code == 401


# --- Test 5: /me with expired token ---
@pytest.mark.asyncio
async def test_me_expired_token():
    """GET /api/admin/auth/me with expired token returns 401."""
    expired_token = jwt.encode(
        {
            "sub": "testadmin",
            "role": "admin",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/admin/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
    assert response.status_code == 401


# --- Test 6: Token creation/decoding ---
def test_create_and_decode_token():
    """create_access_token produces a decodable token with correct payload."""
    payload = {"sub": "testuser", "role": "admin"}
    token = create_access_token(data=payload)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "testuser"
    assert decoded["role"] == "admin"
    assert "exp" in decoded
