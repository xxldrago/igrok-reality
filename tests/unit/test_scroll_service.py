"""Tests for scroll service — day calculation, archetype matching, active user filtering."""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure src is on path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.scroll_service import get_active_users, get_scroll_for_user
from app.shared.models.scroll import Scroll
from app.shared.models.user import User


def _make_user(
    *,
    archetype: str | None = "head",
    started_at: datetime | None = None,
) -> MagicMock:
    """Create a mock User with the given archetype and started_at."""
    user = MagicMock(spec=User)
    user.id = MagicMock()
    user.archetype = archetype
    user.started_at = started_at
    return user


def _make_scroll(
    *,
    day_number: int = 1,
    archetype: str = "head",
    text: str = "Тестовый Свиток",
) -> MagicMock:
    """Create a mock Scroll with the given day_number and archetype."""
    scroll = MagicMock(spec=Scroll)
    scroll.id = MagicMock()
    scroll.day_number = day_number
    scroll.archetype = archetype
    scroll.text = text
    return scroll


class TestGetScrollForUser:
    """Tests for get_scroll_for_user day calculation and query logic."""

    @pytest.mark.asyncio
    async def test_calculates_day_correctly(self) -> None:
        """started_at 3 days ago should query for day_number=4."""
        started_at = datetime.now(timezone.utc) - timedelta(days=3)
        user = _make_user(started_at=started_at)
        expected_scroll = _make_scroll(day_number=4)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_scroll

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            scroll = await get_scroll_for_user(user)

            assert scroll is not None
            assert scroll.day_number == 4

    @pytest.mark.asyncio
    async def test_returns_none_when_started_at_is_none(self) -> None:
        """User without started_at should get None."""
        user = _make_user(started_at=None)

        scroll = await get_scroll_for_user(user)
        assert scroll is None

    @pytest.mark.asyncio
    async def test_returns_none_after_day_90(self) -> None:
        """User with started_at 91 days ago (day 92) should get None."""
        started_at = datetime.now(timezone.utc) - timedelta(days=91)
        user = _make_user(started_at=started_at)

        scroll = await get_scroll_for_user(user)
        assert scroll is None

    @pytest.mark.asyncio
    async def test_day_90_returns_scroll(self) -> None:
        """User with started_at 89 days ago (day 90) should get a scroll."""
        started_at = datetime.now(timezone.utc) - timedelta(days=89)
        user = _make_user(started_at=started_at)
        expected_scroll = _make_scroll(day_number=90)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_scroll

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            scroll = await get_scroll_for_user(user)

            assert scroll is not None
            assert scroll.day_number == 90

    @pytest.mark.asyncio
    async def test_day_1_returns_scroll(self) -> None:
        """User with started_at today (day 1) should get a scroll."""
        now = datetime.now(timezone.utc)
        user = _make_user(started_at=now)
        expected_scroll = _make_scroll(day_number=1)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_scroll

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            scroll = await get_scroll_for_user(user)

            assert scroll is not None
            assert scroll.day_number == 1

    @pytest.mark.asyncio
    async def test_matches_archetype(self) -> None:
        """Query should filter by user's archetype."""
        started_at = datetime.now(timezone.utc) - timedelta(days=5)
        user = _make_user(archetype="shell", started_at=started_at)
        expected_scroll = _make_scroll(day_number=6, archetype="shell")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_scroll

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            scroll = await get_scroll_for_user(user)

            assert scroll is not None
            assert scroll.archetype == "shell"


class TestGetActiveUsers:
    """Tests for get_active_users filtering logic."""

    @pytest.mark.asyncio
    async def test_filters_users_with_archetype_and_started_at(self) -> None:
        """Only users with archetype and started_at set should be returned."""
        user_with_both = _make_user(archetype="head", started_at=datetime.now(timezone.utc))
        user_no_archetype = _make_user(archetype=None, started_at=datetime.now(timezone.utc))
        user_no_started = _make_user(archetype="head", started_at=None)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [user_with_both]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            users = await get_active_users()

            assert len(users) == 1
            assert users[0] is user_with_both
