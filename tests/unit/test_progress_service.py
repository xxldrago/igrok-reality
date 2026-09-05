"""Tests for progress_service — completion idempotency, XP award, leaderboard write."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.progress_service import add_xp, create_completion, update_leaderboard
from app.shared.models.completion import UserCompletion
from app.shared.models.user import User


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def scroll_id() -> UUID:
    return uuid4()


# --- create_completion ---


@patch("app.bot.services.progress_service.session_factory")
async def test_create_completion_new(
    mock_session_factory: MagicMock, user_id: UUID, scroll_id: UUID
) -> None:
    """create_completion returns UserCompletion when none exists."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # session.add is synchronous
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # No existing completion
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    completion = await create_completion(user_id=user_id, scroll_id=scroll_id)

    assert completion is not None
    assert isinstance(completion, UserCompletion)
    assert completion.xp_awarded == 10
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@patch("app.bot.services.progress_service.session_factory")
async def test_create_completion_idempotent(
    mock_session_factory: MagicMock, user_id: UUID, scroll_id: UUID
) -> None:
    """create_completion returns None when completion already exists."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # session.add is synchronous
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    existing = UserCompletion(user_id=user_id, scroll_id=scroll_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await create_completion(user_id=user_id, scroll_id=scroll_id)

    assert result is None
    mock_session.add.assert_not_called()


# --- add_xp ---


@patch("app.bot.services.progress_service.session_factory")
async def test_add_xp(mock_session_factory: MagicMock, user_id: UUID) -> None:
    """add_xp increments user.xp and returns new total."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    user = User(
        telegram_id=123,
        first_name="Test",
        archetype="head",
        xp=0,
        streak=0,
        referral_code="abc123",
    )
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    new_xp = await add_xp(user_id=user_id, xp=10)

    assert new_xp == 10
    assert user.xp == 10
    mock_session.commit.assert_awaited_once()


# --- update_leaderboard ---


@patch("app.bot.services.progress_service.aioredis")
async def test_update_leaderboard(
    mock_aioredis: MagicMock, user_id: UUID
) -> None:
    """update_leaderboard calls Redis zadd with correct key and score."""
    mock_redis = AsyncMock()
    mock_aioredis.from_url.return_value = mock_redis
    mock_redis.aclose = AsyncMock()

    await update_leaderboard(user_id=user_id, xp=42)

    mock_redis.zadd.assert_awaited_once_with(
        "leaderboard:xp", {str(user_id): 42}
    )
    mock_redis.aclose.assert_awaited_once()
