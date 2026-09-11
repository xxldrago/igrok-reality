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
    media_url: str | None = None,
    media_type: str | None = None,
    scheduled_at: datetime | None = None,
    audience: str | None = None,
    archetype: str | None = None,
) -> list[Notification]:
    """Create a notification for active users (optionally one archetype).

    When scheduled_at is in the future the rows stay queued until due —
    the worker only picks notifications whose time has come.
    """
    async with session_factory() as session:
        query = select(User).where(User.archetype.isnot(None), User.started_at.isnot(None))
        if archetype:
            query = query.where(User.archetype == archetype)
        result = await session.execute(query)
        users = list(result.scalars().all())

        notifications = []
        for user in users:
            notification = Notification(
                user_id=user.id,
                type=type_,
                payload=payload,
                media_url=media_url,
                media_type=media_type,
                scheduled_at=scheduled_at,
                audience=audience or archetype or "all",
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
    """Get due notifications for ARQ worker delivery.

    Only rows that are unsent AND (not scheduled OR scheduled time reached).
    """
    async with session_factory() as session:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(Notification)
            .where(
                Notification.sent_at.is_(None),
                (Notification.scheduled_at.is_(None))
                | (Notification.scheduled_at <= now),
            )
            .order_by(Notification.created_at.asc())
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
        media_url = notification.media_url
        media_type = notification.media_type
        if media_url and media_type == "photo":
            try:
                await bot.send_photo(user.telegram_id, media_url, caption=notification.payload[:1024] or None)
                if len(notification.payload) > 1024:
                    await bot.send_message(user.telegram_id, notification.payload)
            except TelegramAPIError:
                await bot.send_message(user.telegram_id, notification.payload)
        elif media_url and media_type == "video":
            try:
                await bot.send_video(user.telegram_id, media_url, caption=notification.payload[:1024] or None)
                if len(notification.payload) > 1024:
                    await bot.send_message(user.telegram_id, notification.payload)
            except TelegramAPIError:
                await bot.send_message(user.telegram_id, notification.payload)
        elif media_url and media_type == "document":
            try:
                await bot.send_document(user.telegram_id, media_url, caption=notification.payload[:1024] or None)
                if len(notification.payload) > 1024:
                    await bot.send_message(user.telegram_id, notification.payload)
            except TelegramAPIError:
                await bot.send_message(user.telegram_id, notification.payload)
        else:
            await bot.send_message(user.telegram_id, notification.payload)
        await mark_sent(notification_id)
        return True
    except TelegramAPIError:
        return False
    finally:
        await bot.session.close()