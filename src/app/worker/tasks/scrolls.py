"""ARQ task for daily scroll delivery to active users and channel publishing."""

from __future__ import annotations

import asyncio
import logging
from datetime import date

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from sqlalchemy import select

from app.bot.keyboards.scroll import completion_keyboard
from app.bot.services.scroll_service import SECTION_HEADERS, get_active_users, get_scroll_by_day, get_scroll_content
from app.shared.config import settings
from app.shared.database import session_factory
from app.shared.models.scroll import Scroll

logger = logging.getLogger(__name__)


async def publish_to_channel(bot: Bot, scroll: Scroll, individual_tasks: dict[str, str]) -> bool:
    """Publish the daily scroll to the closed channel.

    Returns True if published (or already published), False on error.
    """
    # Check if already published
    if scroll.published_at is not None:
        logger.info("Scroll day %d already published to channel", scroll.day_number)
        return True

    # Compose the channel message — include all 4 archetype tasks
    lines: list[str] = [f"📜 День {scroll.day_number} (опубликовано в канале)"]

    for attr, header in SECTION_HEADERS.items():
        value = getattr(scroll, attr)
        if value:
            lines.append("")
            lines.append(f"🔹 {header}:")
            lines.append(str(value))

    # Add all individual tasks for reference
    for code, task_text in individual_tasks.items():
        if task_text:
            archetype_name = {"head": "Голова", "shell": "Панцирь", "whirlwind": "Вихрь", "ghost": "Призрак"}.get(code, code)
            lines.append("")
            lines.append(f"🔸 {archetype_name}:")
            lines.append(task_text)

    channel_text = "\n".join(lines)

    try:
        await bot.send_message(
            settings.QUEST_CHANNEL_ID,
            channel_text,
            disable_web_page_preview=True,
        )
        # Mark as published
        async with session_factory() as session:
            await session.execute(
                Scroll.__table__.update()
                .where(Scroll.id == scroll.id)
                .values(published_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc))
            )
            await session.commit()
        logger.info("Published scroll day %d to channel", scroll.day_number)
        return True
    except TelegramAPIError as e:
        logger.error("Failed to publish scroll day %d to channel: %s", scroll.day_number, e)
        return False


async def deliver_daily_scrolls(ctx: dict) -> None:
    """Deliver daily scrolls to all active users and publish to channel.

    Fetches active users, retrieves each user's composed 5-section scroll content,
    and sends it with a completion keyboard. Handles Telegram rate limits gracefully.

    Args:
        ctx: ARQ worker context (unused but required by ARQ signature).
    """
    bot = Bot(token=settings.BOT_TOKEN)
    sent = 0
    failed = 0

    try:
        active_users = await get_active_users()
        logger.info("Delivering scrolls to %d active users", len(active_users))

        # Determine current day (same for all users in this delivery)
        if not active_users:
            logger.info("No active users to deliver to")
            return

        # Use first user's day to find the scroll to publish
        first_user = active_users[0]
        day_number = (date.today() - first_user.started_at.date()).days + 1

        # Get the scroll for this day
        scroll = await get_scroll_by_day(day_number)
        if scroll is None:
            logger.warning("No scroll found for day %d", day_number)
            return

        # Get all 4 archetype tasks for channel publication
        individual_tasks = {}
        async with session_factory() as session:
            from app.shared.models.scroll_archetype_task import ScrollArchetypeTask
            task_result = await session.execute(
                select(ScrollArchetypeTask).where(ScrollArchetypeTask.scroll_id == scroll.id)
            )
            for task in task_result.scalars().all():
                individual_tasks[task.archetype_code] = task.task_text

        # Publish to channel first
        await publish_to_channel(bot, scroll, individual_tasks)

        # Then deliver privately to each user
        for user in active_users:
            content = await get_scroll_content(user)
            if content is None:
                logger.debug("No scroll for user %s (day out of range)", user.id)
                continue

            kb = completion_keyboard(str(content.scroll.id))
            message_text = content.text

            try:
                await bot.send_message(
                    user.telegram_id,
                    message_text,
                    reply_markup=kb,
                )
                sent += 1
            except TelegramRetryAfter as e:
                logger.warning(
                    "Rate limited, sleeping %ds then retrying for user %s",
                    e.retry_after,
                    user.id,
                )
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(
                        user.telegram_id,
                        message_text,
                        reply_markup=kb,
                    )
                    sent += 1
                except TelegramAPIError as retry_err:
                    logger.warning(
                        "Retry failed for user %s: %s", user.id, retry_err
                    )
                    failed += 1
            except TelegramAPIError as e:
                logger.warning("Failed to send scroll to user %s: %s", user.id, e)
                failed += 1

        logger.info("Scroll delivery complete — sent=%d failed=%d", sent, failed)
    finally:
        await bot.session.close()
