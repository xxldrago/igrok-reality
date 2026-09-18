"""Tests for Telegram file proxy (report attachment previews)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.api import dependencies as deps_mod  # noqa: E402
from app.api.main import app  # noqa: E402
from app.api.routes import media as media_mod  # noqa: E402


def _client():
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    )


@pytest.mark.asyncio
async def test_proxy_rejects_bad_file_id() -> None:
    """Path traversal / garbage file_id is rejected before any calls."""
    with patch.object(
        deps_mod, "decode_access_token", return_value={"sub": "admin", "role": "master"}
    ):
        async with _client() as client:
            r = await client.get(
                "/api/admin/media/telegram/!!!not-a-file-id!!!",
                headers={"Authorization": "Bearer x"},
            )
            assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_proxy_streams_bytes() -> None:
    """Happy path: getFile + download mocked, bytes streamed back."""
    mock_file = MagicMock()
    mock_file.file_path = "photos/abc.jpg"
    mock_bot = AsyncMock()
    mock_bot.get_file = AsyncMock(return_value=mock_file)
    mock_bot.token = "tok123"
    mock_bot_cls = MagicMock(return_value=mock_bot)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"\xff\xd8\xfffake"
    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.get = AsyncMock(return_value=mock_resp)

    from app.bot.services import settings_service as settings_mod

    with (
        patch.object(
            deps_mod, "decode_access_token", return_value={"sub": "admin", "role": "master"}
        ),
        patch.object(media_mod, "Bot", mock_bot_cls),
        patch("httpx.AsyncClient", return_value=mock_http),
        patch.object(
            settings_mod, "get_bot_token", new_callable=AsyncMock, return_value="tok123"
        ),
    ):
        async with _client() as client:
            r = await client.get(
                "/api/admin/media/telegram/AgACAgIAAxk",
                headers={"Authorization": "Bearer x"},
            )
    assert r.status_code == 200, r.text
    assert r.content == b"\xff\xd8\xfffake"
    assert "image" in r.headers["content-type"]
    mock_bot.get_file.assert_awaited_once_with("AgACAgIAAxk")


@pytest.mark.asyncio
async def test_proxy_getfile_failure_is_502() -> None:
    """Telegram getFile error surfaces as 502, not 500."""
    mock_bot = AsyncMock()
    mock_bot.get_file = AsyncMock(side_effect=Exception("gone"))
    mock_bot_cls = MagicMock(return_value=mock_bot)

    from app.bot.services import settings_service as settings_mod

    with (
        patch.object(
            deps_mod, "decode_access_token", return_value={"sub": "admin", "role": "master"}
        ),
        patch.object(media_mod, "Bot", mock_bot_cls),
        patch.object(
            settings_mod, "get_bot_token", new_callable=AsyncMock, return_value="tok123"
        ),
    ):
        async with _client() as client:
            r = await client.get(
                "/api/admin/media/telegram/AgACAgIAAxk",
                headers={"Authorization": "Bearer x"},
            )
    assert r.status_code == 502, r.text
