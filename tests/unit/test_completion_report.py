"""Tests for completion report attachment."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.bot.handlers.scroll import (
    handle_scroll_completion,
    skip_report,
    handle_report_text,
    handle_report_media,
)
from app.bot.services.progress_service import update_completion_report, create_completion
from app.bot.states.completion import CompletionReportState
from app.shared.models.completion import UserCompletion


@pytest.mark.asyncio
async def test_update_completion_report_updates_existing() -> None:
    """update_completion_report updates report fields without creating new completion."""
    user_id = uuid4()
    scroll_id = uuid4()

    completion = UserCompletion(
        id=uuid4(),
        user_id=user_id,
        scroll_id=scroll_id,
        xp_awarded=10,
    )

    session = AsyncMock()
    session.execute = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=completion)
    session.execute.return_value = result

    import app.bot.services.progress_service as ps
    original_factory = ps.session_factory
    ps.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        await update_completion_report(
            user_id=user_id,
            scroll_id=scroll_id,
            report_text="Test report",
            report_media_url="file_id_123",
            report_media_type="photo",
        )

        assert completion.report_text == "Test report"
        assert completion.report_media_url == "file_id_123"
        assert completion.report_media_type == "photo"
        session.commit.assert_called_once()
    finally:
        ps.session_factory = original_factory


@pytest.mark.asyncio
async def test_skip_report_clears_state() -> None:
    """skip_report clears FSM state and informs user."""
    message = AsyncMock()
    message.text = "/skip"

    state = AsyncMock()
    state.clear = AsyncMock()

    await skip_report(message, state)

    state.clear.assert_called_once()
    message.answer.assert_called_once_with("Отчёт не добавлен. Продолжайте в том же духе!")


@pytest.mark.asyncio
async def test_handle_report_text_saves_text() -> None:
    """handle_report_text saves text to completion."""
    message = AsyncMock()
    message.text = "My report text"

    state = AsyncMock()
    state.get_data = AsyncMock(return_value={
        "scroll_id": str(uuid4()),
        "user_id": str(uuid4()),
    })

    with patch("app.bot.handlers.scroll.update_completion_report") as mock_update:
        mock_update.return_value = AsyncMock()
        await handle_report_text(message, state)

    state.clear.assert_called_once()
    message.answer.assert_called_once_with("Отчёт сохранён. Спасибо!")
    mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_handle_report_media_saves_photo() -> None:
    """handle_report_media saves photo file_id."""
    message = AsyncMock()
    message.photo = [MagicMock(file_id="photo_123"), MagicMock(file_id="photo_456")]
    message.caption = "Photo caption"

    state = AsyncMock()
    state.get_data = AsyncMock(return_value={
        "scroll_id": str(uuid4()),
        "user_id": str(uuid4()),
    })

    with patch("app.bot.handlers.scroll.update_completion_report") as mock_update:
        mock_update.return_value = AsyncMock()
        await handle_report_media(message, state)

    state.clear.assert_called_once()
    message.answer.assert_called_once_with("Отчёт сохранён. Спасибо!")
    mock_update.assert_called_once()
    # Verify last photo (largest) was used
    call_args = mock_update.call_args
    assert call_args.kwargs["report_media_url"] == "photo_456"
    assert call_args.kwargs["report_media_type"] == "photo"