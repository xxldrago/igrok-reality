"""ARQ task for daily scroll delivery to active users."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from app.bot.keyboards.scroll import completion_keyboard
from app.bot.services.scroll_service import get_active_users, get_scroll_for_user
from app.shared.config import settings

logger = logging.getLogger(__name__)


async def deliver_daily_scrolls(ctx: dict) -> None:
    """Deliver daily scrolls to all active users.

    Fetches active users, retrieves each user's scroll, and sends it
    with a completion keyboard. Handles Telegram rate limits gracefully.

    Args:
        ctx: ARQ worker context (unused but required by ARQ signature).
    """
    bot = Bot(token=settings.BOT_TOKEN)
    sent = 0
    failed = 0

    try:
        active_users = await get_active_users()
        logger.info("Delivering scrolls to %d active users", len(active_users))

        for user in active_users:
            scroll = await get_scroll_for_user(user)
            if scroll is None:
                logger.debug("No scroll for user %s (day out of range)", user.id)
                continue

            kb = completion_keyboard(str(scroll.id))

            try:
                await bot.send_message(
                    user.telegram_id,
                    scroll.text,
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
                        scroll.text,
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
