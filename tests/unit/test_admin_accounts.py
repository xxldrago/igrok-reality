"""Tests for multi-admin accounts: login, provisioning, CRUD guards."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.api import dependencies as deps_mod  # noqa: E402
from app.api.main import app  # noqa: E402
from app.api.routes import admin as admin_mod  # noqa: E402
from app.bot.services.settings_service import hash_admin_password  # noqa: E402


def _session_cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _admin_row(username="boss", role="master", password="secret123"):
    row = MagicMock()
    row.id = uuid4()
    row.username = username
    row.role = role
    row.telegram = ""
    row.is_active = True
    row.password_hash = hash_admin_password(password)
    from datetime import datetime, timezone

    row.created_at = datetime(2026, 9, 22, tzinfo=timezone.utc)
    return row


async def _post(path, body, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(path, headers=headers, json=body)
        return r.status_code, r.text


async def _login_token(username, password):
    status, body = await _post(
        "/api/admin/auth/login", {"username": username, "password": password}
    )
    assert status == 200, body
    import json

    return json.loads(body)["access_token"]


@pytest.mark.asyncio
async def test_login_with_admin_row() -> None:
    """Row-based login returns the row role."""
    row = _admin_row(username="xxldragon", role="master", password="123456")
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = row
    mock_session.execute = AsyncMock(return_value=res)

    import app.shared.database as db_mod

    with patch.object(
        db_mod, "session_factory", return_value=_session_cm(mock_session)
    ):
            status, body = await _post(
                "/api/admin/auth/login",
                {"username": "xxldragon", "password": "123456"},
            )
    assert status == 200, body
    import json

    payload = json.loads(body)
    assert "access_token" in payload


@pytest.mark.asyncio
async def test_login_wrong_password_rejected() -> None:
    row = _admin_row(password="right-one")
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = row
    mock_session.execute = AsyncMock(return_value=res)

    import app.shared.database as db_mod

    with patch.object(
        db_mod, "session_factory", return_value=_session_cm(mock_session)
    ):
        status, _ = await _post(
            "/api/admin/auth/login", {"username": "boss", "password": "wrong"}
        )
    assert status == 401


@pytest.mark.asyncio
async def test_legacy_login_provisions_row() -> None:
    """Env-password login creates its admin_users row on first success."""
    import app.api.auth as auth_mod
    from app.shared import config as config_mod

    mock_session = AsyncMock()
    res_empty = MagicMock()
    res_empty.scalar_one_or_none.return_value = None
    added = []
    mock_session.execute = AsyncMock(return_value=res_empty)
    mock_session.add = MagicMock(side_effect=lambda o: added.append(o))
    mock_session.commit = AsyncMock()

    import app.shared.database as db_mod

    with (
        patch.object(
            db_mod, "session_factory", return_value=_session_cm(mock_session)
        ),
        patch.object(config_mod.settings, "ADMIN_USERNAME", "legacy"),
        patch.object(config_mod.settings, "ADMIN_PASSWORD", "legacy-pass"),
        patch(
            "app.bot.services.settings_service.get_admin_credentials",
            new_callable=AsyncMock,
            return_value=("legacy", None),
        ),
    ):
        status, body = await _post(
            "/api/admin/auth/login",
            {"username": "legacy", "password": "legacy-pass"},
        )
    assert status == 200, body
    assert any(type(o).__name__ == "AdminUser" for o in added)


@pytest.mark.asyncio
async def test_admins_list_hides_hashes() -> None:
    rows = [_admin_row("a", "master"), _admin_row("b", "leader")]
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalars.return_value.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=res)

    with (
        patch.object(
            deps_mod, "decode_access_token", return_value={"sub": "a", "role": "master"}
        ),
        patch.object(admin_mod, "session_factory", return_value=_session_cm(mock_session)),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(
                "/api/admin/admins", headers={"Authorization": "Bearer x"}
            )
    assert r.status_code == 200, r.text
    assert "password_hash" not in r.text
    assert r.json()[0]["username"] == "a"


@pytest.mark.asyncio
async def test_create_admin_duplicate_409() -> None:
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = _admin_row("taken")
    mock_session.execute = AsyncMock(return_value=res)

    with (
        patch.object(
            deps_mod, "decode_access_token", return_value={"sub": "a", "role": "master"}
        ),
        patch.object(admin_mod, "session_factory", return_value=_session_cm(mock_session)),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/admin/admins",
                headers={"Authorization": "Bearer x"},
                json={"username": "taken", "password": "123456", "role": "master"},
            )
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_cannot_delete_last_master() -> None:
    """Deleting the only active master is blocked."""
    only = _admin_row("solo", "master")
    mock_session = AsyncMock()

    async def fake_execute(_q):
        calls = fake_execute.calls
        calls.append(1)
        r = MagicMock()
        if len(calls) == 1:
            r.scalar_one_or_none.return_value = only
        else:
            # _active_master_count excluding self → none left
            rr = MagicMock()
            rr.scalars.return_value.all.return_value = []
            return rr
        return r

    fake_execute.calls = []
    mock_session.execute = AsyncMock(side_effect=fake_execute)

    with (
        patch.object(
            deps_mod, "decode_access_token", return_value={"sub": "other", "role": "master"}
        ),
        patch.object(admin_mod, "session_factory", return_value=_session_cm(mock_session)),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(
                f"/api/admin/admins/{only.id}", headers={"Authorization": "Bearer x"}
            )
    assert r.status_code == 400, r.text
    assert "last active master" in r.text


@pytest.mark.asyncio
async def test_cannot_delete_self() -> None:
    me = _admin_row("me", "master")
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = me
    mock_session.execute = AsyncMock(return_value=res)

    with (
        patch.object(
            deps_mod, "decode_access_token", return_value={"sub": "me", "role": "master"}
        ),
        patch.object(admin_mod, "session_factory", return_value=_session_cm(mock_session)),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(
                f"/api/admin/admins/{me.id}", headers={"Authorization": "Bearer x"}
            )
    assert r.status_code == 400, r.text
