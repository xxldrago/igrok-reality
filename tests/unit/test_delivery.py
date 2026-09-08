"""Tests for channel publishing and delivery."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.worker.tasks.scrolls import deliver_daily_scrolls, publish_to_channel
from app.shared.models.scroll import Scroll
from app.shared.models.user import User
from app.shared.models.scroll_archetype_task import ScrollArchetypeTask


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    
    # session.execute returns a result with scalars().all()
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[])
    result.scalars = MagicMock(return_value=scalars_mock)
    session.execute = AsyncMock(return_value=result)
    
    return session


@pytest.mark.asyncio
@patch("app.worker.tasks.scrolls.session_factory")
async def test_publish_to_channel_skips_if_already_published(mock_session_factory, mock_session) -> None:
    """publish_to_channel returns True if scroll already published."""
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    bot = AsyncMock()
    scroll = Scroll(
        id=uuid4(),
        day_number=1,
        common_task="Test",
        ritual="Test",
        habits="Test",
        micromovements="Test",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),  # Already published
    )
    individual_tasks = {}

    result = await publish_to_channel(bot, scroll, individual_tasks)

    assert result is True
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("app.worker.tasks.scrolls.session_factory")
async def test_publish_to_channel_sends_message(mock_session_factory, mock_session) -> None:
    """publish_to_channel sends composed message and marks scroll as published."""
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    bot = AsyncMock()
    bot.send_message = AsyncMock()

    scroll = Scroll(
        id=uuid4(),
        day_number=1,
        common_task="Common task",
        ritual="Ritual",
        habits="Habits",
        micromovements="Micromovements",
        published_at=None,
    )
    individual_tasks = {
        "head": "Head task",
        "shell": "Shell task",
        "whirlwind": "Whirlwind task",
        "ghost": "Ghost task",
    }

    result = await publish_to_channel(bot, scroll, individual_tasks)

    assert result is True
    bot.send_message.assert_called_once()
    call_args = bot.send_message.call_args
    assert call_args.args[0] is not None  # settings.QUEST_CHANNEL_ID as positional arg
    text = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("text", "")
    assert "День 1" in text
    assert "Common task" in text
    assert "Head task" in text
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.worker.tasks.scrolls.session_factory")
async def test_deliver_daily_scrolls_publishes_then_delivers(mock_session_factory, mock_session) -> None:
    """deliver_daily_scrolls publishes to channel then delivers to users."""
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    ctx = {}

    user = User(
        id=uuid4(),
        telegram_id=123456,
        first_name="Test",
        username="testuser",
        archetype="head",
        role="player",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    with patch("app.worker.tasks.scrolls.get_active_users") as mock_get_users:
        mock_get_users.return_value = [user]

        with patch("app.worker.tasks.scrolls.get_scroll_by_day") as mock_get_scroll:
            scroll = Scroll(
                id=uuid4(),
                day_number=1,
                common_task="Common",
                ritual="Ritual",
                habits="Habits",
                micromovements="Micro",
                published_at=None,
            )
            mock_get_scroll.return_value = scroll

            with patch("app.worker.tasks.scrolls.publish_to_channel") as mock_publish:
                mock_publish.return_value = True

                with patch("app.worker.tasks.scrolls.get_scroll_content") as mock_get_content:
                    from app.bot.services.scroll_service import ScrollContent
                    content = ScrollContent(
                        scroll=scroll,
                        individual_task="Individual task",
                        archetype_code="head",
                    )
                    mock_get_content.return_value = content

                    with patch("app.worker.tasks.scrolls.Bot") as mock_bot_class:
                        bot = AsyncMock()
                        bot.send_message = AsyncMock()
                        mock_bot_class.return_value = bot

                        await deliver_daily_scrolls(ctx)

    mock_publish.assert_called_once()
    bot.send_message.assert_called()  # Once per user