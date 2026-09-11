"""Channel access service — grant/revoke Telegram channel access.

Manages one-time invite link generation and user banning for QUEST_CHANNEL_ID.
Called by the webhook handler on payment CONFIRMED (grant) and CHARGEBACKED/REFUNDED (revoke).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from app.bot.services.settings_service import get_quest_channel_id
from app.shared.database import session_factory
from app.shared.models.user import User

if TYPE_CHECKING:
    from aiogram import Bot

logger = logging.getLogger(__name__)


async def grant_access(user_id: UUID, bot: Bot) -> str | None:
    """Grant channel access by creating a one-time invite link.

    Creates a member_limit=1 invite link for QUEST_CHANNEL_ID, updates
    user.access_granted_at, and returns the invite URL.

    Returns None on Telegram API errors (logged, not raised).
    """
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if user is None:
        logger.error("grant_access: user %s not found", user_id)
        return None

    try:
        invite = await bot.create_chat_invite_link(
            chat_id=await get_quest_channel_id(),
            name=f"User {user_id}",
            member_limit=1,
        )
    except Exception:
        logger.exception("grant_access: Telegram API error for user %s", user_id)
        return None

    # Update access_granted_at timestamp
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one()
        db_user.access_granted_at = datetime.now(timezone.utc)
        await session.commit()

    logger.info("grant_access: invite link created for user %s", user_id)
    return invite.invite_link


async def revoke_access(user_id: UUID, bot: Bot) -> bool:
    """Revoke channel access by banning the user from QUEST_CHANNEL_ID.

    Uses ban_chat_member + unban_chat_member so the user can re-join later
    if they pay again.

    Returns True on success, False on Telegram API errors (logged, not raised).
    """
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if user is None:
        logger.error("revoke_access: user %s not found", user_id)
        return False

    try:
        channel_id = await get_quest_channel_id()
        await bot.ban_chat_member(
            chat_id=channel_id,
            user_id=user.telegram_id,
        )
        # Unban so user can re-join later if they pay again
        await bot.unban_chat_member(
            chat_id=channel_id,
            user_id=user.telegram_id,
        )
    except Exception:
        logger.exception("revoke_access: Telegram API error for user %s", user_id)
        return False

    logger.info("revoke_access: user %s banned from channel", user_id)
    return True
