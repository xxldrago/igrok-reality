"""Tests for completion report attachment."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

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
        from app.bot.services.progress_service import update_completion_report
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
async def test_user_completion_report_fields() -> None:
    """UserCompletion has report_text, report_media_url, report_media_type fields."""
    completion = UserCompletion(
        id=uuid4(),
        user_id=uuid4(),
        scroll_id=uuid4(),
        xp_awarded=10,
        report_text="Check my form",
        report_media_url="AgACAgIAAxkB",
        report_media_type="photo",
    )
    assert completion.report_text == "Check my form"
    assert completion.report_media_url == "AgACAgIAAxkB"
    assert completion.report_media_type == "photo"


@pytest.mark.asyncio
async def test_user_completion_report_defaults_none() -> None:
    """UserCompletion report fields default to None."""
    completion = UserCompletion(
        id=uuid4(),
        user_id=uuid4(),
        scroll_id=uuid4(),
        xp_awarded=10,
    )
    assert completion.report_text is None
    assert completion.report_media_url is None
    assert completion.report_media_type is None
