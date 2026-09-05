"""Tests for channel_access — invite link creation, revocation, error handling."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.channel_access import grant_access, revoke_access
from app.shared.models.user import User


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def mock_user() -> User:
    return User(
        telegram_id=12345,
        first_name="Test",
        last_name="User",
        username="testuser",
        archetype="head",
        xp=0,
        streak=0,
        referral_code="abc123",
    )


# --- grant_access ---


@patch("app.bot.services.channel_access.session_factory")
async def test_grant_access_success(
    mock_session_factory: MagicMock, user_id: UUID, mock_user: User
) -> None:
    """grant_access calls bot.create_chat_invite_link with member_limit=1 and returns invite URL."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # First call: load user; second call: update access_granted_at
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_result.scalar_one.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_bot = AsyncMock()
    mock_invite = MagicMock()
    mock_invite.invite_link = "https://t.me/+abc123"
    mock_bot.create_chat_invite_link = AsyncMock(return_value=mock_invite)

    result = await grant_access(user_id=user_id, bot=mock_bot)

    assert result == "https://t.me/+abc123"
    mock_bot.create_chat_invite_link.assert_awaited_once_with(
        chat_id=mock_bot.create_chat_invite_link.call_args.kwargs["chat_id"],
        name=f"User {user_id}",
        member_limit=1,
    )
    assert mock_user.access_granted_at is not None
    mock_session.commit.assert_awaited()


@patch("app.bot.services.channel_access.session_factory")
async def test_grant_access_user_not_found(
    mock_session_factory: MagicMock, user_id: UUID
) -> None:
    """grant_access returns None when user does not exist."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_bot = AsyncMock()

    result = await grant_access(user_id=user_id, bot=mock_bot)

    assert result is None
    mock_bot.create_chat_invite_link.assert_not_awaited()


@patch("app.bot.services.channel_access.session_factory")
async def test_grant_access_api_error(
    mock_session_factory: MagicMock, user_id: UUID, mock_user: User
) -> None:
    """grant_access returns None on Telegram API error."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_bot = AsyncMock()
    mock_bot.create_chat_invite_link = AsyncMock(side_effect=Exception("Telegram API error"))

    result = await grant_access(user_id=user_id, bot=mock_bot)

    assert result is None


# --- revoke_access ---


@patch("app.bot.services.channel_access.session_factory")
async def test_revoke_access_success(
    mock_session_factory: MagicMock, user_id: UUID, mock_user: User
) -> None:
    """revoke_access calls bot.ban_chat_member with user.telegram_id and returns True."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_bot = AsyncMock()
    mock_bot.ban_chat_member = AsyncMock()
    mock_bot.unban_chat_member = AsyncMock()

    result = await revoke_access(user_id=user_id, bot=mock_bot)

    assert result is True
    mock_bot.ban_chat_member.assert_awaited_once()
    call_kwargs = mock_bot.ban_chat_member.call_args.kwargs
    assert call_kwargs["user_id"] == 12345  # mock_user.telegram_id
    mock_bot.unban_chat_member.assert_awaited_once()


@patch("app.bot.services.channel_access.session_factory")
async def test_revoke_access_user_not_found(
    mock_session_factory: MagicMock, user_id: UUID
) -> None:
    """revoke_access returns False when user does not exist."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_bot = AsyncMock()

    result = await revoke_access(user_id=user_id, bot=mock_bot)

    assert result is False
    mock_bot.ban_chat_member.assert_not_awaited()


@patch("app.bot.services.channel_access.session_factory")
async def test_revoke_access_api_error(
    mock_session_factory: MagicMock, user_id: UUID, mock_user: User
) -> None:
    """revoke_access returns False on Telegram API error."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_bot = AsyncMock()
    mock_bot.ban_chat_member = AsyncMock(side_effect=Exception("Telegram API error"))

    result = await revoke_access(user_id=user_id, bot=mock_bot)

    assert result is False
