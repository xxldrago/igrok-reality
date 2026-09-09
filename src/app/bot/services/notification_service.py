"""Notification service — queue and dispatch notifications."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from app.bot.services.settings_service import get_setting
from app.shared.database import session_factory
from app.shared.models.notification import Notification
from app.shared.models.user import User


async def send_system_notification(
    user_id: UUID,
    type_: str,
    payload: str,
) -> Notification | None:
    """Create a notification row and enqueue for delivery.

    Returns the created Notification or None if user not found.
    """
    async with session_factory() as session:
        # Verify user exists
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return None

        notification = Notification(
            user_id=user_id,
            type=type_,
            payload=payload,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
        return notification


async def send_system_notification_to_all(
    type_: str,
    payload: str,
) -> list[Notification]:
    """Create a notification for ALL active users."""
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.archetype.isnot(None), User.started_at.isnot(None))
        )
        users = list(result.scalars().all())

        notifications = []
        for user in users:
            notification = Notification(
                user_id=user.id,
                type=type_,
                payload=payload,
            )
            session.add(notification)
            notifications.append(notification)

        await session.commit()
        return notifications


async def mark_sent(notification_id: UUID) -> bool:
    """Mark a notification as sent."""
    async with session_factory() as session:
        result = await session.execute(select(Notification).where(Notification.id == notification_id))
        notification = result.scalar_one_or_none()
        if notification is None:
            return False

        notification.sent_at = datetime.now(timezone.utc)
        await session.commit()
        return True


async def get_pending_notifications(limit: int = 100) -> list[Notification]:
    """Get pending notifications (sent_at IS NULL) for ARQ worker delivery."""
    async with session_factory() as session:
        result = await session.execute(
            select(Notification)
            .where(Notification.sent_at.is_(None))
            .limit(limit)
        )
        return list(result.scalars().all())


async def send_notification(notification_id: UUID, bot_token: str) -> bool:
    """Send a single notification via Telegram Bot API."""
    from aiogram import Bot
    from aiogram.exceptions import TelegramAPIError

    async with session_factory() as session:
        result = await session.execute(select(Notification).where(Notification.id == notification_id))
        notification = result.scalar_one_or_none()
        if notification is None or notification.sent_at is not None:
            return False

        if notification.user_id is None:
            return False

        # Get user's telegram_id
        user_result = await session.execute(
            select(User).where(User.id == notification.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            return False

    bot = Bot(token=bot_token)
    try:
        await bot.send_message(user.telegram_id, notification.payload)
        await mark_sent(notification_id)
        return True
    except TelegramAPIError:
        return False
    finally:
        await bot.session.close()