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
from app.bot.services.scroll_service import get_scroll_for_user
from app.shared.models.scroll import Scroll
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
    archetype: str = "head",
    text: str = "День 6: Утренний ритуал",
) -> MagicMock:
    """Create a mock Scroll with the given parameters."""
    scroll = MagicMock(spec=Scroll)
    scroll.id = scroll_id or uuid4()
    scroll.day_number = day_number
    scroll.archetype = archetype
    scroll.text = text
    return scroll


class TestFullDeliveryFlow:
    """Integration test: user → day calculation → scroll → keyboard."""

    @pytest.mark.asyncio
    async def test_full_delivery_flow(self) -> None:
        """User with archetype 'head' and started_at 5 days ago gets day 6 scroll."""
        started_at = datetime.now(timezone.utc) - timedelta(days=5)
        user = _make_user(archetype="head", started_at=started_at)
        scroll_id = uuid4()
        expected_scroll = _make_scroll(scroll_id=scroll_id, day_number=6, archetype="head")

        # Mock session_factory to return the scroll
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

            # Step 1: Get scroll for user
            scroll = await get_scroll_for_user(user)
            assert scroll is not None
            assert scroll.day_number == 6
            assert scroll.archetype == "head"
            assert scroll.text == "День 6: Утренний ритуал"

            # Step 2: Build completion keyboard
            kb = completion_keyboard(str(scroll.id))
            assert len(kb.inline_keyboard) == 1
            assert len(kb.inline_keyboard[0]) == 1

            # Step 3: Verify callback data unpacks correctly
            button = kb.inline_keyboard[0][0]
            callback_data = button.callback_data
            unpacked = ScrollCompletion.unpack(callback_data)
            assert unpacked.scroll_id == str(scroll.id)

    @pytest.mark.asyncio
    async def test_delivery_task_handles_no_scroll(self) -> None:
        """User with started_at 100 days ago gets None (day > 90)."""
        started_at = datetime.now(timezone.utc) - timedelta(days=100)
        user = _make_user(started_at=started_at)

        # Mock session_factory to return None (no scroll found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

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

            # No scroll returned — delivery task would skip this user
            assert scroll is None

    @pytest.mark.asyncio
    async def test_different_archetype_gets_different_scroll(self) -> None:
        """User with 'shell' archetype gets scroll for 'shell', not 'head'."""
        started_at = datetime.now(timezone.utc) - timedelta(days=2)
        user = _make_user(archetype="shell", started_at=started_at)
        expected_scroll = _make_scroll(
            scroll_id=uuid4(),
            day_number=3,
            archetype="shell",
            text="День 3: Панцирь",
        )

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
            assert scroll.text == "День 3: Панцирь"
