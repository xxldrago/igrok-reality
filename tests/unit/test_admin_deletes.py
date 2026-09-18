"""Tests for admin delete endpoints (all with confirmation on the frontend)."""

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


def _session_cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


async def _delete(path: str, execute, params: dict | None = None):
    with (
        patch.object(
            deps_mod, "decode_access_token", return_value={"sub": "admin", "role": "master"}
        ),
        patch.object(admin_mod, "session_factory") as mock_factory,
    ):
        mock_session = AsyncMock()
        mock_session.execute = execute
        mock_session.add = MagicMock()
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_factory.return_value = _session_cm(mock_session)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete(
                path, headers={"Authorization": "Bearer x"}, params=params
            )
            return r.status_code, r.text, mock_session


def _none_result():
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    return r


@pytest.mark.asyncio
async def test_delete_user_not_found() -> None:
    async def fake_execute(_q):
        return _none_result()

    status, body, _ = await _delete(
        f"/api/admin/users/{uuid4()}", AsyncMock(side_effect=fake_execute)
    )
    assert status == 404, body


@pytest.mark.asyncio
async def test_delete_user_master_blocked() -> None:
    user = MagicMock()
    user.role = "master"
    user.username = "boss"

    async def fake_execute(_q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = user
        return r

    status, body, session = await _delete(
        f"/api/admin/users/{uuid4()}", AsyncMock(side_effect=fake_execute)
    )
    assert status == 400, body
    assert "master" in body.lower()
    session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_user_cascade() -> None:
    user = MagicMock()
    user.id = uuid4()
    user.role = "player"
    user.username = "ivan"
    user.first_name = "Ivan"

    async def fake_execute(_q):
        r = MagicMock()
        # First call: user lookup. Owned checks: nothing. Everything else: None.
        return r

    calls = {"n": 0}

    async def counting_execute(_q):
        calls["n"] += 1
        r = MagicMock()
        if calls["n"] == 1:
            r.scalar_one_or_none.return_value = user
        else:
            r.scalar_one_or_none.return_value = None
        return r

    status, body, session = await _delete(
        f"/api/admin/users/{user.id}", AsyncMock(side_effect=counting_execute)
    )
    _ = fake_execute
    assert status == 200, body
    assert '"deleted":true' in body.replace(" ", "")
    session.delete.assert_awaited_once()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_daily_scroll_not_found() -> None:
    async def fake_execute(_q):
        return _none_result()

    status, body, _ = await _delete(
        f"/api/admin/daily-scrolls/{uuid4()}", AsyncMock(side_effect=fake_execute)
    )
    assert status == 404, body


@pytest.mark.asyncio
async def test_delete_daily_scroll_detaches_history() -> None:
    ds = MagicMock()
    ds.day_number = 5

    async def fake_execute(_q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = ds
        return r

    status, body, session = await _delete(
        f"/api/admin/daily-scrolls/{uuid4()}", AsyncMock(side_effect=fake_execute)
    )
    assert status == 200, body
    # update (detach) + select + delete + audit commit path touched execute
    assert session.execute.await_count >= 2
    session.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_report_bad_source() -> None:
    async def fake_execute(_q):
        return _none_result()

    status, body, _ = await _delete(
        f"/api/admin/reports/{uuid4()}",
        AsyncMock(side_effect=fake_execute),
        params={"source": "nope"},
    )
    assert status == 400, body


@pytest.mark.asyncio
async def test_delete_report_success() -> None:
    row = MagicMock()

    async def fake_execute(_q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = row
        return r

    status, body, session = await _delete(
        f"/api/admin/reports/{uuid4()}",
        AsyncMock(side_effect=fake_execute),
        params={"source": "daily"},
    )
    assert status == 200, body
    session.delete.assert_awaited_once_with(row)


@pytest.mark.asyncio
async def test_delete_moderation_not_found() -> None:
    async def fake_execute(_q):
        return _none_result()

    status, body, _ = await _delete(
        f"/api/admin/moderation/{uuid4()}", AsyncMock(side_effect=fake_execute)
    )
    assert status == 404, body


@pytest.mark.asyncio
async def test_delete_moderation_success() -> None:
    row = MagicMock()

    async def fake_execute(_q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = row
        return r

    status, body, session = await _delete(
        f"/api/admin/moderation/{uuid4()}", AsyncMock(side_effect=fake_execute)
    )
    assert status == 200, body
    session.delete.assert_awaited_once_with(row)
