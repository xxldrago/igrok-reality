"""Tests for unknown-command fallback (spec 4.1: typos are not recognized)."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.handlers import daily as daily_mod
from app.shared.models.scroll_type import ScrollType


def _message(text: str):
    message = AsyncMock()
    message.text = text
    message.from_user.id = 123456
    message.answer = AsyncMock()
    return message


def _session_with_types(types):
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = types
    mock_session.execute = AsyncMock(return_value=mock_result)
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _scroll_type(code: str, command: str):
    return ScrollType(code=code, name=code, command=command, hour=5)


class _FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.started_at = datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)
        self.timezone = "Europe/Moscow"


@pytest.mark.asyncio
async def test_unknown_command_unregistered() -> None:
    """Unregistered user gets a /start hint."""
    with patch.object(daily_mod, "get_user_by_telegram_id", new_callable=AsyncMock) as m:
        m.return_value = None
        message = _message("/wakeupp")
        await daily_mod.handle_unknown_command(message)
        text = message.answer.call_args[0][0]
        assert "/wakeupp" in text
        assert "/start" in text


@pytest.mark.asyncio
async def test_unknown_command_lists_today_commands() -> None:
    """Typo on quest day 2 lists available commands."""
    types = [_scroll_type("rassvet", "/wakeup"), _scroll_type("ogne", "/cold")]
    with (
        patch.object(daily_mod, "get_user_by_telegram_id", new_callable=AsyncMock) as m_user,
        patch.object(daily_mod, "session_factory", return_value=_session_with_types(types)),
    ):
        m_user.return_value = _FakeUser()
        message = _message("/wakeupp")
        # Freeze time: 2026-01-15 noon Moscow = quest day 6... use explicit now via started math:
        # started Jan 10 -> any now works; quest_day just needs to be > 0
        await daily_mod.handle_unknown_command(message)
        text = message.answer.call_args[0][0]
        assert "не распознана" in text
        assert "/wakeup" in text
        assert "/today" in text
