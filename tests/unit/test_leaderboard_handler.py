"""Tests for /leaderboard handler — top users display."""

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


# --- /leaderboard handler tests ---


@patch("app.bot.handlers.leaderboard.get_user_rank")
@patch("app.bot.handlers.leaderboard.get_leaderboard")
@patch("app.bot.handlers.leaderboard.get_user_by_id")
@patch("app.bot.handlers.leaderboard.get_user_by_telegram_id")
async def test_leaderboard_shows_top_users(
    mock_get_telegram_user: MagicMock,
    mock_get_user: MagicMock,
    mock_get_leaderboard: MagicMock,
    mock_get_rank: MagicMock,
    telegram_id: int,
) -> None:
    """Test that /leaderboard shows top 10 users with medals."""
    # Mock current user
    current_user = User(
        telegram_id=telegram_id,
        first_name="CurrentUser",
        archetype="head",
        xp=50,
        streak=2,
        referral_code="abc123",
    )
    mock_get_telegram_user.return_value = current_user

    # Create user IDs for leaderboard entries
    user_id_1 = uuid4()
    user_id_2 = uuid4()
    user_id_3 = uuid4()

    # Mock leaderboard data
    leaderboard = [
        {"user_id": str(user_id_1), "xp": 100},
        {"user_id": str(user_id_2), "xp": 90},
        {"user_id": str(user_id_3), "xp": 80},
    ]
    mock_get_leaderboard.return_value = leaderboard

    # Mock user lookups
    users = {
        user_id_1: User(telegram_id=111, first_name="Alice", archetype="head", xp=100, streak=5, referral_code="a1"),
        user_id_2: User(telegram_id=222, first_name="Bob", archetype="shell", xp=90, streak=3, referral_code="b2"),
        user_id_3: User(telegram_id=333, first_name="Charlie", archetype="whirlwind", xp=80, streak=1, referral_code="c3"),
    }
    mock_get_user.side_effect = lambda uid: users.get(uid)

    # Mock rank (user not in top 3)
    mock_get_rank.return_value = 15

    message = AsyncMock()
    message.from_user.id = telegram_id

    from app.bot.handlers.leaderboard import handle_leaderboard
    await handle_leaderboard(message)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "🥇" in call_args
    assert "🥈" in call_args
    assert "🥉" in call_args
    assert "Alice" in call_args
    assert "Bob" in call_args
    assert "Charlie" in call_args


@patch("app.bot.handlers.leaderboard.get_leaderboard")
async def test_leaderboard_empty(
    mock_get_leaderboard: MagicMock,
    telegram_id: int,
) -> None:
    """Test that /leaderboard shows hint when empty."""
    mock_get_leaderboard.return_value = []

    message = AsyncMock()
    message.from_user.id = telegram_id

    from app.bot.handlers.leaderboard import handle_leaderboard
    await handle_leaderboard(message)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "нет данных" in call_args.lower() or "свитков" in call_args.lower()


@patch("app.bot.handlers.leaderboard.get_user_rank")
@patch("app.bot.handlers.leaderboard.get_leaderboard")
@patch("app.bot.handlers.leaderboard.get_user_by_id")
@patch("app.bot.handlers.leaderboard.get_user_by_telegram_id")
async def test_leaderboard_shows_user_rank_if_outside_top10(
    mock_get_telegram_user: MagicMock,
    mock_get_user: MagicMock,
    mock_get_leaderboard: MagicMock,
    mock_get_rank: MagicMock,
    telegram_id: int,
) -> None:
    """Test that user's rank is shown if not in top 10."""
    current_user = User(
        telegram_id=telegram_id,
        first_name="CurrentUser",
        archetype="head",
        xp=50,
        streak=2,
        referral_code="abc123",
    )
    mock_get_telegram_user.return_value = current_user

    # Mock leaderboard with 3 users
    leaderboard = [
        {"user_id": str(uuid4()), "xp": 100},
        {"user_id": str(uuid4()), "xp": 90},
        {"user_id": str(uuid4()), "xp": 80},
    ]
    mock_get_leaderboard.return_value = leaderboard

    # Mock user lookups
    users = [
        User(telegram_id=111, first_name="Alice", archetype="head", xp=100, streak=5, referral_code="a1"),
        User(telegram_id=222, first_name="Bob", archetype="shell", xp=90, streak=3, referral_code="b2"),
        User(telegram_id=333, first_name="Charlie", archetype="whirlwind", xp=80, streak=1, referral_code="c3"),
    ]
    mock_get_user.side_effect = lambda uid: next((u for u in users if str(u.id) == str(uid)), None)

    # User is at rank 25 (outside top 10)
    mock_get_rank.return_value = 24

    message = AsyncMock()
    message.from_user.id = telegram_id

    from app.bot.handlers.leaderboard import handle_leaderboard
    await handle_leaderboard(message)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "25" in call_args  # rank + 1


@patch("app.bot.handlers.leaderboard.get_user_rank")
@patch("app.bot.handlers.leaderboard.get_leaderboard")
@patch("app.bot.handlers.leaderboard.get_user_by_id")
@patch("app.bot.handlers.leaderboard.get_user_by_telegram_id")
async def test_leaderboard_user_in_top10_no_extra_rank(
    mock_get_telegram_user: MagicMock,
    mock_get_user: MagicMock,
    mock_get_leaderboard: MagicMock,
    mock_get_rank: MagicMock,
    telegram_id: int,
) -> None:
    """Test that user's rank is NOT shown if already in top 10."""
    # Create user IDs for leaderboard entries
    current_user_id = uuid4()
    user_id_2 = uuid4()
    user_id_3 = uuid4()

    current_user = User(
        telegram_id=telegram_id,
        first_name="CurrentUser",
        archetype="head",
        xp=100,
        streak=5,
        referral_code="abc123",
    )
    # Set the id manually for the test
    current_user.id = current_user_id
    mock_get_telegram_user.return_value = current_user

    # Mock leaderboard with current user at #1
    leaderboard = [
        {"user_id": str(current_user_id), "xp": 100},
        {"user_id": str(user_id_2), "xp": 90},
        {"user_id": str(user_id_3), "xp": 80},
    ]
    mock_get_leaderboard.return_value = leaderboard

    # Mock user lookups
    users = {
        current_user_id: current_user,
        user_id_2: User(telegram_id=222, first_name="Bob", archetype="shell", xp=90, streak=3, referral_code="b2"),
        user_id_3: User(telegram_id=333, first_name="Charlie", archetype="whirlwind", xp=80, streak=1, referral_code="c3"),
    }
    mock_get_user.side_effect = lambda uid: users.get(uid)

    # User is at rank 0 (in top 10)
    mock_get_rank.return_value = 0

    message = AsyncMock()
    message.from_user.id = telegram_id

    from app.bot.handlers.leaderboard import handle_leaderboard
    await handle_leaderboard(message)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    # Should NOT contain "позиции" since user is in top 10
    assert "позиции" not in call_args.lower()
