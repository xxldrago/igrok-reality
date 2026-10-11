"""Tests for /leaderboard handler — group-scoped display."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.handlers.leaderboard import leaderboard_router
from app.shared.models.user import User


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def telegram_id() -> int:
    return 123456789


def _user(name: str, xp: int, group_id, telegram_id: int = 111) -> User:
    u = User(telegram_id=telegram_id, first_name=name, archetype="head", xp=xp, streak=1, referral_code="r")
    u.group_id = group_id
    return u


# --- /leaderboard handler tests ---


@patch("app.bot.handlers.leaderboard.get_leaderboard_limit", new_callable=AsyncMock)
@patch("app.bot.handlers.leaderboard.get_group_leaders", new_callable=AsyncMock)
@patch("app.bot.handlers.leaderboard.get_user_by_telegram_id", new_callable=AsyncMock)
async def test_leaderboard_shows_group_top(
    mock_me: MagicMock,
    mock_leaders: MagicMock,
    mock_limit: MagicMock,
    telegram_id: int,
) -> None:
    """Group members are shown with medals, outsiders are not."""
    from app.bot.handlers.leaderboard import handle_leaderboard

    group_id = uuid4()
    me = _user("Me", 50, group_id, telegram_id)
    mock_me.return_value = me
    mock_limit.return_value = 10
    mock_leaders.return_value = [
        _user("Alice", 100, group_id, 111),
        _user("Bob", 90, group_id, 222),
        _user("Charlie", 80, group_id, 333),
    ]

    message = AsyncMock()
    message.from_user.id = telegram_id
    await handle_leaderboard(message)

    message.answer.assert_called_once()
    text = message.answer.call_args[0][0]
    assert "🥇" in text and "🥈" in text and "🥉" in text
    assert "Alice" in text and "Bob" in text and "Charlie" in text
    assert "группы" in text


@patch("app.bot.handlers.leaderboard.get_user_by_telegram_id", new_callable=AsyncMock)
async def test_leaderboard_no_group_hint(
    mock_me: MagicMock,
    telegram_id: int,
) -> None:
    """User without a group gets a hint instead of a global board."""
    from app.bot.handlers.leaderboard import handle_leaderboard

    me = _user("Me", 50, None, telegram_id)
    mock_me.return_value = me

    message = AsyncMock()
    message.from_user.id = telegram_id
    await handle_leaderboard(message)

    text = message.answer.call_args[0][0]
    assert "не в группе" in text


@patch("app.bot.handlers.leaderboard.get_leaderboard_limit", new_callable=AsyncMock)
@patch("app.bot.handlers.leaderboard.get_group_leaders", new_callable=AsyncMock)
@patch("app.bot.handlers.leaderboard.get_user_by_telegram_id", new_callable=AsyncMock)
async def test_leaderboard_empty_group(
    mock_me: MagicMock,
    mock_leaders: MagicMock,
    mock_limit: MagicMock,
    telegram_id: int,
) -> None:
    """Empty group board shows the no-data hint."""
    from app.bot.handlers.leaderboard import handle_leaderboard

    mock_me.return_value = _user("Me", 0, uuid4(), telegram_id)
    mock_limit.return_value = 10
    mock_leaders.return_value = []

    message = AsyncMock()
    message.from_user.id = telegram_id
    await handle_leaderboard(message)

    text = message.answer.call_args[0][0]
    assert "нет данных" in text.lower()


@patch("app.bot.handlers.leaderboard.get_leaderboard_limit", new_callable=AsyncMock)
@patch("app.bot.handlers.leaderboard.get_group_leaders", new_callable=AsyncMock)
@patch("app.bot.handlers.leaderboard.get_user_by_telegram_id", new_callable=AsyncMock)
async def test_leaderboard_rank_outside_top(
    mock_me: MagicMock,
    mock_leaders: MagicMock,
    mock_limit: MagicMock,
    telegram_id: int,
) -> None:
    """Rank within the group is shown when the user is outside the top N."""
    from app.bot.handlers.leaderboard import handle_leaderboard

    group_id = uuid4()
    me = _user("Me", 10, group_id, telegram_id)
    me.id = uuid4()
    mock_me.return_value = me
    mock_limit.return_value = 1
    top = _user("Alice", 100, group_id, 111)
    # First call (top-1) returns only Alice; second call (top-1000) includes me at #2
    mock_leaders.side_effect = [[top], [top, me]]

    message = AsyncMock()
    message.from_user.id = telegram_id
    await handle_leaderboard(message)

    text = message.answer.call_args[0][0]
    assert "#2" in text
