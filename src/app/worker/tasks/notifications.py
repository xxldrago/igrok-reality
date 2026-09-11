"""ARQ tasks for notification delivery."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from sqlalchemy import select

from app.bot.services.notification_service import (
    get_pending_notifications,
    send_notification,
)
from app.bot.services.settings_service import get_bot_token, get_setting
from app.shared.database import session_factory
from app.shared.models.user import User
from app.shared.models.completion import UserCompletion

logger = logging.getLogger(__name__)


async def send_pending_notifications(ctx: dict) -> None:
    """ARQ task to send pending notifications from the queue."""
    bot = Bot(token=await get_bot_token())
    sent = 0
    failed = 0

    try:
        notifications = await get_pending_notifications(limit=100)
        logger.info("Processing %d pending notifications", len(notifications))

        for notification in notifications:
            try:
                success = await send_notification(notification.id, await get_bot_token())
                if success:
                    sent += 1
                else:
                    failed += 1
            except Exception as e:
                logger.warning("Failed to send notification %s: %s", notification.id, e)
                failed += 1

        logger.info("Notification delivery complete — sent=%d failed=%d", sent, failed)
    finally:
        await bot.session.close()


async def evening_scroll_reminder(ctx: dict) -> None:
    """ARQ task: evening reminder for users who haven't completed today's scroll.

    Runs at configured time (default 20:00 Moscow). Sends notification to all
    active users who have not completed today's scroll.
    """
    bot = Bot(token=await get_bot_token())
    sent = 0

    try:
        # Get reminder time from settings
        hour = int(await get_setting("reminder_hour", "20"))
        minute = int(await get_setting("reminder_minute", "0"))

        # Get all active users
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(
                    User.archetype.isnot(None),
                    User.started_at.isnot(None),
                )
            )
            active_users = list(result.scalars().all())

        # For each user, check if they completed today's scroll
        for user in active_users:
            from app.bot.services.scroll_service import get_scroll_content

            content = await get_scroll_content(user)
            if content is None:
                continue

            # Check completion
            from app.shared.models.completion import UserCompletion
            from sqlalchemy import select

            async with session_factory() as session:
                result = await session.execute(
                    select(UserCompletion).where(
                        UserCompletion.user_id == user.id,
                        UserCompletion.scroll_id == content.scroll.id,
                    )
                )
                completion = result.scalar_one_or_none()

            if completion is None:
                # Not completed — send reminder
                try:
                    await bot.send_message(
                        user.telegram_id,
                        "🌅 Не забывай про сегодняшний свиток! Ещё есть время выполнить его."
                    )
                    sent += 1
                except TelegramRetryAfter as e:
                    logger.warning("Rate limited for user %s, sleeping %ds", user.id, e.retry_after)
                    await asyncio.sleep(e.retry_after)
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            "🌅 Не забывай про сегодняшний свиток! Ещё есть время выполнить его."
                        )
                        sent += 1
                    except TelegramAPIError:
                        pass
                except TelegramAPIError:
                    pass

        logger.info("Evening scroll reminder sent to %d users", sent)
    finally:
        await bot.session.close()


async def streak_loss_warning(ctx: dict) -> None:
    """ARQ task: warning for users who completed yesterday but not today.

    Runs before midnight (e.g., 23:00 Moscow). Targets users who:
    - Have a streak > 0
    - Completed yesterday (streak_last_date == today)
    - Have not completed today
    """
    bot = Bot(token=await get_bot_token())
    sent = 0

    try:
        # Get all active users with streak > 0
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(
                    User.archetype.isnot(None),
                    User.started_at.isnot(None),
                    User.streak > 0,
                )
            )
            active_users = list(result.scalars().all())

        from datetime import date
        from zoneinfo import ZoneInfo

        for user in active_users:
            tz = ZoneInfo(user.timezone)
            today = datetime.now(tz).date()

            # Check if streak is at risk (completed yesterday, not today)
            if user.streak_last_date == today - timedelta(days=1):
                # Check if completed today
                from app.bot.services.scroll_service import get_scroll_content
                content = await get_scroll_content(user)

                if content:
                    from app.shared.models.completion import UserCompletion
                    from sqlalchemy import select

                    async with session_factory() as session:
                        result = await session.execute(
                            select(UserCompletion).where(
                                UserCompletion.user_id == user.id,
                                UserCompletion.scroll_id == content.scroll.id,
                            )
                        )
                        completion = result.scalar_one_or_none()

                    if completion is None:
                        # At risk — send warning
                        try:
                            await bot.send_message(
                                user.telegram_id,
                                f"⚠️ Твоя серия {user.streak} дней под угрозой! "
                                "Выполни свиток сегодня, чтобы её сохранить."
                            )
                            sent += 1
                        except TelegramRetryAfter as e:
                            logger.warning("Rate limited for user %s, sleeping %ds", user.id, e.retry_after)
                            await asyncio.sleep(e.retry_after)
                            try:
                                await bot.send_message(
                                    user.telegram_id,
                                    f"⚠️ Твоя серия {user.streak} дней под угрозой! "
                                    "Выполни свиток сегодня, чтобы её сохранить."
                                )
                                sent += 1
                            except TelegramAPIError:
                                pass
                        except TelegramAPIError:
                            pass

        logger.info("Streak loss warning sent to %d users", sent)
    finally:
        await bot.session.close()


async def new_stream_notification(ctx: dict) -> None:
    """ARQ task: notify all active users about new stream start."""
    bot = Bot(token=await get_bot_token())
    sent = 0

    try:
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(
                    User.archetype.isnot(None),
                    User.started_at.isnot(None),
                )
            )
            active_users = list(result.scalars().all())

        for user in active_users:
            try:
                await bot.send_message(
                    user.telegram_id,
                    "🚀 Новый поток начался! Добро пожаловать в новую волну Игрок.Реальность.\n"
                    "Твой день 1 уже доступен — заходи выполнять первый свиток."
                )
                sent += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(
                        user.telegram_id,
                        "🚀 Новый поток начался! Добро пожаловать в новую волну Игрок.Реальность.\n"
                        "Твой день 1 уже доступен — заходи выполнять первый свиток."
                    )
                    sent += 1
                except TelegramAPIError:
                    pass
            except TelegramAPIError:
                pass

        logger.info("New stream notification sent to %d users", sent)
    finally:
        await bot.session.close()