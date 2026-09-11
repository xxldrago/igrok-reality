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
    parse_mode: str | None = None,
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
                parse_mode=parse_mode if parse_mode in ("HTML", "Markdown") else None,
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

    async def _send_text(chat_id: int, text: str) -> None:
        """Send text with parse_mode, falling back to plain text on markup errors."""
        parse_mode = notification.parse_mode if notification.parse_mode in ("HTML", "Markdown") else None
        if parse_mode:
            try:
                await bot.send_message(chat_id, text, parse_mode=parse_mode)
                return
            except TelegramAPIError:
                pass
        await bot.send_message(chat_id, text)

    async def _send_media(
        method: str, chat_id: int, url: str, caption: str | None, long_text: str | None
    ) -> None:
        """Send photo/video/document with caption, fall back to text on errors."""
        parse_mode = notification.parse_mode if notification.parse_mode in ("HTML", "Markdown") else None
        send = {"photo": bot.send_photo, "video": bot.send_video, "document": bot.send_document}[method]
        try:
            await send(chat_id, url, caption=caption, parse_mode=parse_mode)
        except TelegramAPIError:
            try:
                await send(chat_id, url, caption=caption)
            except TelegramAPIError:
                await _send_text(chat_id, (caption or "") + (f"\n\n{long_text}" if long_text else ""))
                return
        if long_text:
            await _send_text(chat_id, long_text)

    bot = Bot(token=bot_token)
    try:
        media_url = notification.media_url
        media_type = notification.media_type
        payload = notification.payload
        if media_url and media_type in ("photo", "video", "document"):
            caption = payload[:1024] or None
            rest = payload[1024:] if len(payload) > 1024 else None
            await _send_media(media_type, user.telegram_id, media_url, caption, rest)
        else:
            await _send_text(user.telegram_id, payload)
        await mark_sent(notification_id)
        return True
    except TelegramAPIError:
        return False
    finally:
        await bot.session.close()