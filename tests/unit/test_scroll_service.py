"""Tests for scroll service — day calculation, archetype content join, text composition."""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure src is on path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.scroll_service import (
    build_scroll_text,
    get_active_users,
    get_scroll_content,
    get_scroll_for_user,
)
from app.shared.models.scroll import Scroll
from app.shared.models.scroll_archetype_task import ScrollArchetypeTask
from app.shared.models.user import User


def _make_user(
    *,
    archetype: str | None = "head",
    started_at: datetime | None = None,
    timezone: str = "Europe/Moscow",
) -> MagicMock:
    """Create a mock User with the given archetype and started_at."""
    user = MagicMock(spec=User)
    user.id = MagicMock()
    user.archetype = archetype
    user.started_at = started_at
    user.timezone = timezone
    return user


def _make_scroll(
    *,
    day_number: int = 1,
    common_task: str = "Общее задание дня",
    ritual: str = "Утренний ритуал",
    habits: str = "Привычки",
    micromovements: str = "Микродвижения",
) -> MagicMock:
    """Create a mock Scroll with the new 5-section fields."""
    scroll = MagicMock(spec=Scroll)
    scroll.id = MagicMock()
    scroll.day_number = day_number
    scroll.common_task = common_task
    scroll.ritual = ritual
    scroll.habits = habits
    scroll.micromovements = micromovements
    return scroll


def _make_task(
    *, scroll_id: MagicMock, archetype_code: str = "head", task_text: str = "Индивидуальная задача"
) -> MagicMock:
    """Create a mock ScrollArchetypeTask."""
    task = MagicMock(spec=ScrollArchetypeTask)
    task.scroll_id = scroll_id
    task.archetype_code = archetype_code
    task.task_text = task_text
    return task


class TestBuildScrollText:
    """Tests for 5-section scroll composition."""

    def test_composes_all_sections_and_individual_task(self) -> None:
        """The message includes all 4 shared sections plus the individual task."""
        scroll = _make_scroll(
            day_number=5,
            common_task="Физика",
            ritual="Ритуал",
            habits="Привычки",
            micromovements="Микро",
        )
        text = build_scroll_text(scroll, "Индивидуальная задача Голова")

        assert "День 5" in text
        assert "Общее задание" in text and "Физика" in text
        assert "Утренний ритуал" in text and "Ритуал" in text
        assert "Привычки" in text
        assert "Микродвижения" in text and "Микро" in text
        assert "Индивидуальная задача Голова" in text

    def test_composition_for_each_archetype(self) -> None:
        """Each archetype's individual task appears in the composed message."""
        for code, archetype_task in [("head", "Задача Голова"), ("shell", "Задача Панцирь")]:
            scroll = _make_scroll(day_number=1, common_task="Физика")
            text = build_scroll_text(scroll, archetype_task)
            assert archetype_task in text

    def test_no_individual_task_when_empty(self) -> None:
        """When the individual task is empty, the section is omitted."""
        scroll = _make_scroll(day_number=1)
        text = build_scroll_text(scroll, "")
        assert "Индивидуальное задание" not in text


class TestGetScrollForUser:
    """Tests for get_scroll_for_user day calculation and per-day query logic."""

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


class TestGetScrollContent:
    """Tests for get_scroll_content loading scroll + archetype task and composing."""

    @pytest.mark.asyncio
    async def test_returns_composed_content_for_user_archetype(self) -> None:
        """Should join the user's per-day scroll with their archetype task."""
        started_at = datetime.now(timezone.utc) - timedelta(days=5)
        user = _make_user(archetype="shell", started_at=started_at)
        scroll = _make_scroll(
            day_number=6, common_task="Физика 6", micromovements="Микро 6"
        )
        task = _make_task(scroll_id=scroll.id, archetype_code="shell", task_text="Задача Панцирь")

        scroll_result = MagicMock()
        scroll_result.scalar_one_or_none.return_value = scroll
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.side_effect = [scroll_result, task_result]
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            content = await get_scroll_content(user)

            assert content is not None
            assert content.scroll is scroll
            assert content.archetype_code == "shell"
            assert content.individual_task == "Задача Панцирь"
            assert "Задача Панцирь" in content.text
            assert "Физика 6" in content.text

    @pytest.mark.asyncio
    async def test_empty_individual_task_when_task_missing(self) -> None:
        """If no archetype task row exists, individual_task is empty string."""
        started_at = datetime.now(timezone.utc) - timedelta(days=5)
        user = _make_user(archetype="ghost", started_at=started_at)
        scroll = _make_scroll(day_number=6, common_task="Физика 6")

        scroll_result = MagicMock()
        scroll_result.scalar_one_or_none.return_value = scroll
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = None

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.side_effect = [scroll_result, task_result]
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            content = await get_scroll_content(user)

            assert content is not None
            assert content.individual_task == ""
            assert "Индивидуальное задание" not in content.text

    @pytest.mark.asyncio
    async def test_returns_none_when_no_scroll(self) -> None:
        """If the per-day scroll is missing, returns None."""
        started_at = datetime.now(timezone.utc) - timedelta(days=5)
        user = _make_user(started_at=started_at)

        scroll_result = MagicMock()
        scroll_result.scalar_one_or_none.return_value = None

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.return_value = scroll_result
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            content = await get_scroll_content(user)
            assert content is None

    @pytest.mark.asyncio
    async def test_returns_none_without_archetype(self) -> None:
        """User without archetype should get None."""
        user = _make_user(archetype=None, started_at=datetime.now(timezone.utc))
        content = await get_scroll_content(user)
        assert content is None


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
