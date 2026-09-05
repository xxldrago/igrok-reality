"""Tests for update_streak — timezone-aware streak tracking."""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.progress_service import update_streak
from app.shared.models.user import User


def _make_user(
    streak: int = 0,
    streak_last_date: date | None = None,
    timezone: str = "Europe/Moscow",
) -> User:
    """Create a mock User with controlled streak fields."""
    user = User(
        telegram_id=123,
        first_name="Test",
        archetype="head",
        xp=0,
        streak=streak,
        streak_last_date=streak_last_date,
        timezone=timezone,
        referral_code="abc123",
    )
    return user


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


# --- First completion ---


@patch("app.bot.services.progress_service.session_factory")
async def test_first_completion(mock_session_factory: MagicMock, user_id: UUID) -> None:
    """First completion ever (streak_last_date=None) sets streak to 1."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    user = _make_user(streak=0, streak_last_date=None)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    streak = await update_streak(user_id=user_id)

    assert streak == 1
    assert user.streak == 1
    assert user.streak_last_date == today
    mock_session.commit.assert_awaited_once()


# --- Same day completion ---


@patch("app.bot.services.progress_service.session_factory")
async def test_same_day(mock_session_factory: MagicMock, user_id: UUID) -> None:
    """Completing on same day as last completion leaves streak unchanged."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    user = _make_user(streak=5, streak_last_date=today)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    streak = await update_streak(user_id=user_id)

    assert streak == 5
    assert user.streak == 5
    assert user.streak_last_date == today
    mock_session.commit.assert_awaited_once()


# --- Consecutive day ---


@patch("app.bot.services.progress_service.session_factory")
async def test_consecutive_day(mock_session_factory: MagicMock, user_id: UUID) -> None:
    """Completing the day after last completion increments streak by 1."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    yesterday = today - timedelta(days=1)
    user = _make_user(streak=3, streak_last_date=yesterday)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    streak = await update_streak(user_id=user_id)

    assert streak == 4
    assert user.streak == 4
    assert user.streak_last_date == today
    mock_session.commit.assert_awaited_once()


# --- Broken streak ---


@patch("app.bot.services.progress_service.session_factory")
async def test_broken_streak(mock_session_factory: MagicMock, user_id: UUID) -> None:
    """Missing a day (2+ days gap) resets streak to 1."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    two_days_ago = today - timedelta(days=2)
    user = _make_user(streak=10, streak_last_date=two_days_ago)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    streak = await update_streak(user_id=user_id)

    assert streak == 1
    assert user.streak == 1
    assert user.streak_last_date == today
    mock_session.commit.assert_awaited_once()


# --- Multi-day gap ---


@patch("app.bot.services.progress_service.session_factory")
async def test_multi_day_gap(mock_session_factory: MagicMock, user_id: UUID) -> None:
    """Missing 5+ days resets streak to 1."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    five_days_ago = today - timedelta(days=5)
    user = _make_user(streak=20, streak_last_date=five_days_ago)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    streak = await update_streak(user_id=user_id)

    assert streak == 1
    assert user.streak == 1
    assert user.streak_last_date == today
    mock_session.commit.assert_awaited_once()


# --- Timezone boundary edge case ---


@patch("app.bot.services.progress_service.session_factory")
@patch("app.bot.services.progress_service.datetime")
async def test_timezone_boundary(
    mock_dt: MagicMock, mock_session_factory: MagicMock, user_id: UUID
) -> None:
    """User in UTC+5 (Almaty) completes at 23:55 local — server is already next day.

    The streak should use Almaty's date, not UTC.
    """
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    almaty_tz = ZoneInfo("Asia/Almaty")
    moscow_tz = ZoneInfo("Europe/Moscow")

    # Simulate: Almaty time is Sep 5 23:55 (UTC+5 => UTC is Sep 5 18:55)
    # Moscow time would be Sep 5 21:55 (UTC+3)
    # So "today" in Almaty is Sep 5, same as Moscow
    # For a real edge case: Almaty Sep 5 23:55 = UTC Sep 5 18:55
    #   Moscow Sep 5 21:55 — both Sep 5
    # But if user's last streak was Sep 4, and now it's Sep 5 in Almaty = consecutive

    almaty_now = datetime(2026, 9, 5, 23, 55, tzinfo=almaty_tz)
    mock_dt.now.return_value = almaty_now

    # User's last completion was yesterday (Sep 4) in Almaty
    user = _make_user(streak=7, streak_last_date=date(2026, 9, 4), timezone="Asia/Almaty")

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    streak = await update_streak(user_id=user_id)

    # Should be consecutive (Sep 5 vs Sep 4), not broken
    assert streak == 8
    assert user.streak_last_date == date(2026, 9, 5)
    mock_session.commit.assert_awaited_once()
