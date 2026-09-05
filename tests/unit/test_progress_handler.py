"""Tests for /progress handler — user stats display."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.handlers.progress import progress_router
from app.shared.models.user import User


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def telegram_id() -> int:
    return 123456789


# --- /progress handler tests ---


@patch("app.bot.handlers.progress.get_user_stats")
@patch("app.bot.handlers.progress.get_user_by_telegram_id")
async def test_progress_shows_stats(
    mock_get_user: MagicMock,
    mock_get_stats: MagicMock,
    telegram_id: int,
) -> None:
    """Test that /progress shows XP, streak, and completions."""
    # Mock user exists
    mock_user = User(
        telegram_id=telegram_id,
        first_name="Test",
        archetype="head",
        xp=150,
        streak=5,
        referral_code="abc123",
    )
    mock_get_user.return_value = mock_user

    # Mock stats
    mock_get_stats.return_value = {"xp": 150, "streak": 5, "completions": 12}

    # Create mock message
    message = AsyncMock()
    message.from_user.id = telegram_id

    # Import and call handler directly
    from app.bot.handlers.progress import handle_progress
    await handle_progress(message)

    # Verify response
    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "150" in call_args
    assert "5" in call_args
    assert "12" in call_args


@patch("app.bot.handlers.progress.get_user_by_telegram_id")
async def test_progress_user_not_found(
    mock_get_user: MagicMock,
    telegram_id: int,
) -> None:
    """Test that /progress shows registration prompt for unregistered user."""
    mock_get_user.return_value = None

    message = AsyncMock()
    message.from_user.id = telegram_id

    from app.bot.handlers.progress import handle_progress
    await handle_progress(message)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "зарегистрируйся" in call_args.lower() or "start" in call_args.lower()


@patch("app.bot.handlers.progress.get_user_stats")
@patch("app.bot.handlers.progress.get_user_by_telegram_id")
async def test_progress_zero_completions(
    mock_get_user: MagicMock,
    mock_get_stats: MagicMock,
    telegram_id: int,
) -> None:
    """Test that /progress shows streak=0, completions=0 correctly."""
    mock_user = User(
        telegram_id=telegram_id,
        first_name="Test",
        archetype="head",
        xp=0,
        streak=0,
        referral_code="abc123",
    )
    mock_get_user.return_value = mock_user

    mock_get_stats.return_value = {"xp": 0, "streak": 0, "completions": 0}

    message = AsyncMock()
    message.from_user.id = telegram_id

    from app.bot.handlers.progress import handle_progress
    await handle_progress(message)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "0" in call_args
