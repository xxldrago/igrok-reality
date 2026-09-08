"""Tests for /profile command."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.bot.handlers.progress import handle_profile
from app.shared.models.user import User


@pytest.mark.asyncio
async def test_handle_profile_composes_correct_text() -> None:
    """handle_profile composes the expected message format."""
    message = AsyncMock()
    message.from_user.id = 123456

    user = User(
        id=uuid4(),
        telegram_id=123456,
        first_name="Test",
        username="testuser",
        archetype="head",
        role="curator",
        xp=150,
        streak=7,
        timezone="Europe/Moscow",
        is_active=True,
        paid_at="2026-01-01T00:00:00+00:00",
    )

    with patch("app.bot.handlers.progress.get_user_by_telegram_id") as mock_get_user:
        mock_get_user.return_value = user
        with patch("app.bot.handlers.progress.get_full_profile") as mock_get_profile:
            mock_get_profile.return_value = {
                "archetype_name": "Голова",
                "quest_day": "День 5 из 90",
                "xp": 150,
                "streak": 7,
                "completions": 5,
                "role": "curator",
                "payment_status": "Оплачен",
                "referral_code": "abc123",
            }
            await handle_profile(message)

    # Verify message was sent with expected format
    message.answer.assert_called_once()
    called_text = message.answer.call_args[0][0]
    assert "👤 Твой профиль" in called_text
    assert "Архетип: Голова" in called_text
    assert "День 5 из 90" in called_text
    assert "XP: 150" in called_text
    assert "Серия: 7 дней" in called_text
    assert "Выполнено: 5 свитков" in called_text
    assert "Роль: Куратор" in called_text
    assert "Оплачен" in called_text
    assert "Реферальная ссылка" in called_text
    assert "abc123" in called_text