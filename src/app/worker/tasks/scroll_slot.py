"""ARQ task for delivering scrolls by time slot."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from sqlalchemy import select

from app.bot.keyboards.scroll import completion_keyboard
from app.bot.services.day_type import get_available_scroll_codes
from app.bot.services.scroll_service import get_active_users
from app.bot.services.settings_service import get_bot_token
from app.shared.config import settings
from app.shared.database import session_factory
from app.shared.models.daily_scroll import DailyScroll
from app.shared.models.scroll_type import ScrollType
from app.shared.models.user import User

logger = logging.getLogger(__name__)


def _get_quest_day(user, tz_name: str) -> int:
    """Calculate the current quest day for a user."""
    if user.started_at is None:
        return 0
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    started = user.started_at.replace(tzinfo=timezone.utc).astimezone(tz)
    delta = (now.date() - started.date()).days
    return min(delta + 1, 90)


async def deliver_scroll_slot(hour: int, ctx: dict | None = None) -> None:
    """Deliver scrolls scheduled for a specific hour to all active users.

    Args:
        hour: The hour (Moscow time) to deliver scrolls for (5, 8, 12, 16, 21).
        ctx: ARQ context dict.
    """
    bot = Bot(token=await get_bot_token())
    sent = 0
    failed = 0

    try:
        # Get all scroll types for this hour
        async with session_factory() as session:
            result = await session.execute(
                select(ScrollType).where(ScrollType.hour == hour)
            )
            scroll_types = list(result.scalars().all())

        if not scroll_types:
            logger.info("No scroll types for hour %d", hour)
            return

        # Get all active users
        users = await get_active_users()

        for user in users:
            tz_name = user.timezone or settings.TZ
            quest_day = _get_quest_day(user, tz_name)
            if quest_day == 0:
                continue

            # Get available scroll codes for this day
            available_codes = get_available_scroll_codes(quest_day)

            # Get scroll types available for this user at this hour
            for st in scroll_types:
                if st.code not in available_codes:
                    continue

                # Get daily scroll content
                async with session_factory() as session:
                    result = await session.execute(
                        select(DailyScroll).where(
                            DailyScroll.day_number == quest_day,
                            DailyScroll.scroll_type_id == st.id,
                        )
                    )
                    daily_scroll = result.scalar_one_or_none()

                # Compose message
                text = f"📜 {st.name} — День {quest_day}\n"
                if daily_scroll and daily_scroll.content:
                    text += f"\n{daily_scroll.content}"
                else:
                    text += f"\n{st.description}"

                text += f"\n\n⏱ Выполни: {st.command} (+{st.xp_reward} XP)"

                # Attachment (admin panel → scroll media URL or Telegram file_id)
                media = daily_scroll.media_file_id if daily_scroll else None

                async def _send() -> None:
                    if media:
                        if len(text) <= 1024:
                            await bot.send_photo(user.telegram_id, media, caption=text)
                        else:
                            await bot.send_photo(user.telegram_id, media)
                            await bot.send_message(user.telegram_id, text)
                    else:
                        await bot.send_message(user.telegram_id, text)

                # Send to user
                try:
                    await _send()
                    sent += 1
                except TelegramRetryAfter as e:
                    logger.warning("Rate limited, sleeping %ds", e.retry_after)
                    await asyncio.sleep(e.retry_after)
                    try:
                        await _send()
                        sent += 1
                    except TelegramAPIError:
                        # Media failed (bad URL/file_id) — fall back to text
                        try:
                            await bot.send_message(user.telegram_id, text)
                            sent += 1
                        except TelegramAPIError:
                            failed += 1
                except TelegramAPIError:
                    # Media failed (bad URL/file_id) — fall back to text
                    try:
                        await bot.send_message(user.telegram_id, text)
                        sent += 1
                    except TelegramAPIError:
                        failed += 1

                # Small delay between messages
                await asyncio.sleep(0.05)

        logger.info("Scroll slot %d: sent=%d failed=%d", hour, sent, failed)
    finally:
        await bot.session.close()


async def deliver_daily_scrolls(ctx: dict | None = None) -> None:
    """Legacy: deliver all daily scrolls (used by old scheduler).

    Now delegates to deliver_scroll_slot for each hour.
    """
    for hour in [5, 8, 12, 16, 21]:
        await deliver_scroll_slot(hour)
