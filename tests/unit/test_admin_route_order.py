"""Regression tests for literal-vs-UUID route shadowing.

GET /api/admin/users/archetype-stats and /api/admin/payments/export must
resolve to their literal endpoints — not to /users/{user_id} or
/payments/{payment_id} (which used to return 422 uuid_parsing).
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.api.main import app  # noqa: E402
from app.api.routes import admin as admin_mod  # noqa: E402
from app.api import dependencies as deps_mod  # noqa: E402


def _mock_session(execute=None):
    session = AsyncMock()
    session.execute = execute or AsyncMock(return_value=MagicMock())
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


async def _get(path: str, execute=None) -> tuple[int, str]:
    with (
        patch.object(
            deps_mod,
            "decode_access_token",
            return_value={"sub": "admin", "role": "master"},
        ),
        patch.object(admin_mod, "session_factory", return_value=_mock_session(execute)),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(path, headers={"Authorization": "Bearer x"})
            return r.status_code, r.text


@pytest.mark.asyncio
async def test_archetype_stats_not_shadowed_by_user_id() -> None:
    """Literal route wins over /users/{user_id} (was 422 uuid_parsing)."""

    async def fake_execute(_q):
        r = MagicMock()
        r.all.return_value = [("head", 5)]
        return r

    status, body = await _get("/api/admin/users/archetype-stats", fake_execute)
    assert status == 200, body
    assert '"total":5' in body


@pytest.mark.asyncio
async def test_payments_export_not_shadowed_by_payment_id() -> None:
    """Literal route wins over /payments/{payment_id} (was 422 uuid_parsing)."""

    async def fake_execute(_q):
        r = MagicMock()
        r.all.return_value = []
        return r

    status, body = await _get("/api/admin/payments/export", fake_execute)
    assert status == 200, body


@pytest.mark.asyncio
async def test_daily_scrolls_coverage_endpoint() -> None:
    """Coverage endpoint resolves and reports 661 expected on empty DB."""

    async def fake_execute(_q):
        r = MagicMock()
        sc = MagicMock()
        sc.all.return_value = []
        r.scalars.return_value = sc
        r.all.return_value = []
        return r

    status, body = await _get("/api/admin/daily-scrolls/coverage", fake_execute)
    assert status == 200, body
    assert '"total_expected":661' in body
    assert '"complete":false' in body
