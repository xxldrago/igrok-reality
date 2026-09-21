"""Scroll delivery bookkeeping — delete passed/expired scroll messages.

Every delivered daily scroll stores (user, quest day, scroll code) → Telegram
message id. On completion the delivery message is removed; a nightly job
removes messages whose quest day has expired. All deletions are best-effort
and never break the calling flow.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import delete, select

from app.shared.database import session_factory
from app.shared.models.scroll_delivery import ScrollDelivery

logger = logging.getLogger(__name__)


async def record_delivery(
    user_id: UUID, quest_day: int, scroll_code: str, message_id: int
) -> None:
    """Upsert the delivery message id for a (user, day, scroll) triple."""
    try:
        async with session_factory() as session:
            result = await session.execute(
                select(ScrollDelivery).where(
                    ScrollDelivery.user_id == user_id,
                    ScrollDelivery.quest_day == quest_day,
                    ScrollDelivery.scroll_code == scroll_code,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                existing.message_id = message_id
            else:
                session.add(
                    ScrollDelivery(
                        user_id=user_id,
                        quest_day=quest_day,
                        scroll_code=scroll_code,
                        message_id=message_id,
                    )
                )
            await session.commit()
    except Exception:
        logger.warning(
            "record_delivery failed for user %s day %d code %s",
            user_id, quest_day, scroll_code,
        )


async def delete_delivery_message(
    bot, telegram_id: int, user_id: UUID, quest_day: int, scroll_code: str
) -> bool:
    """Delete the delivery message for a completed scroll. Returns True if deleted."""
    try:
        async with session_factory() as session:
            result = await session.execute(
                select(ScrollDelivery).where(
                    ScrollDelivery.user_id == user_id,
                    ScrollDelivery.quest_day == quest_day,
                    ScrollDelivery.scroll_code == scroll_code,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return False
            try:
                await bot.delete_message(chat_id=telegram_id, message_id=row.message_id)
                deleted = True
            except Exception:
                logger.warning(
                    "delete_message failed for user %s msg %d (already gone?)",
                    user_id, row.message_id,
                )
                deleted = False
            await session.delete(row)
            await session.commit()
            return deleted
    except Exception:
        logger.warning("delete_delivery_message failed for user %s", user_id)
        return False


async def cleanup_expired_deliveries(ctx: dict | None = None) -> dict:
    """ARQ task: delete delivery messages whose quest day has passed.

    Runs after the grace period ends (05:30 server time): any delivery row
    with quest_day < the user's current quest day is removed from the chat.
    Returns {"deleted": N, "failed": M}.
    """
    from aiogram import Bot

    from app.bot.services.day_type import get_current_quest_day
    from app.bot.services.settings_service import get_bot_token, get_grace_period_hours
    from app.shared.config import settings
    from app.shared.models.user import User

    deleted = 0
    failed = 0
    try:
        grace = await get_grace_period_hours()
        async with session_factory() as session:
            rows = list((await session.execute(select(ScrollDelivery))).scalars().all())
            if not rows:
                return {"deleted": 0, "failed": 0}
            user_ids = {r.user_id for r in rows}
            users_result = await session.execute(
                select(User).where(User.id.in_(user_ids))
            )
            users = {u.id: u for u in users_result.scalars().all()}

        if not rows:
            return {"deleted": deleted, "failed": failed}

        bot = Bot(token=await get_bot_token())
        try:
            for row in rows:
                user = users.get(row.user_id)
                if user is None or user.started_at is None:
                    continue
                current = get_current_quest_day(
                    user.started_at, user.timezone or settings.TZ, grace
                )
                if current == 0 or row.quest_day >= current:
                    continue
                ok = await delete_delivery_message(
                    bot, user.telegram_id, row.user_id, row.quest_day, row.scroll_code
                )
                if ok:
                    deleted += 1
                else:
                    failed += 1
                await asyncio.sleep(0.05)
        finally:
            await bot.session.close()
    except Exception:
        logger.exception("cleanup_expired_deliveries failed")
    logger.info("Expired delivery cleanup: deleted=%d failed=%d", deleted, failed)
    return {"deleted": deleted, "failed": failed}
