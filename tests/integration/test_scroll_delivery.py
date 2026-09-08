"""Integration tests for scroll delivery flow — end-to-end from user to keyboard."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Ensure src is on path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.callbacks.scroll import ScrollCompletion
from app.bot.keyboards.scroll import completion_keyboard
from app.bot.services.scroll_service import get_scroll_content, get_scroll_for_user
from app.shared.models.scroll import Scroll
from app.shared.models.scroll_archetype_task import ScrollArchetypeTask
from app.shared.models.user import User


def _make_user(
    *,
    user_id: str | None = None,
    archetype: str = "head",
    started_at: datetime | None = None,
) -> MagicMock:
    """Create a mock User with the given parameters."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid4()
    user.archetype = archetype
    user.started_at = started_at
    user.telegram_id = 123456789
    return user


def _make_scroll(
    *,
    scroll_id: str | None = None,
    day_number: int = 6,
    common_task: str = "Физика дня 6",
    ritual: str = "Утренний ритуал дня 6",
    habits: str = "Привычки дня 6",
    micromovements: str = "Микродвижения дня 6",
) -> MagicMock:
    """Create a mock Scroll with the new 5-section fields."""
    scroll = MagicMock(spec=Scroll)
    scroll.id = scroll_id or uuid4()
    scroll.day_number = day_number
    scroll.common_task = common_task
    scroll.ritual = ritual
    scroll.habits = habits
    scroll.micromovements = micromovements
    return scroll


def _make_task(*, scroll: MagicMock, archetype_code: str = "head", task_text: str = "") -> MagicMock:
    """Create a mock ScrollArchetypeTask."""
    task = MagicMock(spec=ScrollArchetypeTask)
    task.scroll_id = scroll.id
    task.archetype_code = archetype_code
    task.task_text = task_text
    return task


class TestFullDeliveryFlow:
    """Integration test: user → day calculation → composed scroll → keyboard."""

    @pytest.mark.asyncio
    async def test_full_delivery_flow(self) -> None:
        """User with archetype 'head' and started_at 5 days ago gets day 6 scroll."""
        started_at = datetime.now(timezone.utc) - timedelta(days=5)
        user = _make_user(archetype="head", started_at=started_at)
        scroll_id = uuid4()
        expected_scroll = _make_scroll(scroll_id=scroll_id, day_number=6)
        expected_task = _make_task(
            scroll=expected_scroll, archetype_code="head", task_text="Задача Голова"
        )

        scroll_result = MagicMock()
        scroll_result.scalar_one_or_none.return_value = expected_scroll
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = expected_task

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.side_effect = [scroll_result, task_result]
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            # Step 1: Get composed scroll content for user
            content = await get_scroll_content(user)
            assert content is not None
            assert content.scroll.day_number == 6
            assert content.archetype_code == "head"
            assert "Задача Голова" in content.text
            assert "Физика дня 6" in content.text

            # Step 2: Build completion keyboard from the scroll id
            kb = completion_keyboard(str(content.scroll.id))
            assert len(kb.inline_keyboard) == 1
            assert len(kb.inline_keyboard[0]) == 1

            # Step 3: Verify callback data unpacks correctly
            button = kb.inline_keyboard[0][0]
            callback_data = button.callback_data
            unpacked = ScrollCompletion.unpack(callback_data)
            assert unpacked.scroll_id == str(content.scroll.id)

    @pytest.mark.asyncio
    async def test_delivery_task_handles_no_scroll(self) -> None:
        """User with started_at 100 days ago gets None (day > 90)."""
        started_at = datetime.now(timezone.utc) - timedelta(days=100)
        user = _make_user(started_at=started_at)

        # Mock session_factory to return None (no scroll found)
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

            # No scroll returned — delivery task would skip this user
            assert content is None

    @pytest.mark.asyncio
    async def test_different_archetype_gets_different_individual_task(self) -> None:
        """User with 'shell' archetype gets shell's individual task, not head's."""
        started_at = datetime.now(timezone.utc) - timedelta(days=2)
        user = _make_user(archetype="shell", started_at=started_at)
        expected_scroll = _make_scroll(scroll_id=uuid4(), day_number=3)
        expected_task = _make_task(
            scroll=expected_scroll, archetype_code="shell", task_text="Задача Панцирь"
        )

        scroll_result = MagicMock()
        scroll_result.scalar_one_or_none.return_value = expected_scroll
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = expected_task

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
            assert content.archetype_code == "shell"
            assert "Задача Панцирь" in content.text

    @pytest.mark.asyncio
    async def test_get_scroll_for_user_returns_per_day_scroll(self) -> None:
        """get_scroll_for_user now returns the per-day scroll (no archetype filter)."""
        started_at = datetime.now(timezone.utc) - timedelta(days=5)
        user = _make_user(archetype="ghost", started_at=started_at)
        expected_scroll = _make_scroll(day_number=6)

        scroll_result = MagicMock()
        scroll_result.scalar_one_or_none.return_value = expected_scroll

        with patch(
            "app.bot.services.scroll_service.session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.execute.return_value = scroll_result
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            scroll = await get_scroll_for_user(user)

            assert scroll is not None
            assert scroll.day_number == 6
