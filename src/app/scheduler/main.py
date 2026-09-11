"""APScheduler cron process entrypoint."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select

from app.shared.config import settings
from app.shared.database import session_factory
from app.shared.models.settings import Setting

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Fallback time slots for scroll delivery (server time) — live value comes
# from settings (delivery_slots, editable via admin panel, scheduler restart).
# Each slot delivers scrolls that are scheduled for that hour
DELIVERY_SLOTS = [
    (5, 0),   # 05:00 — Rassvet, Ogne, Korni (meditation days)
    (8, 0),   # 08:00 — Vetr
    (12, 0),  # 12:00 — Sledy
    (16, 0),  # 16:00 — Zrya, Pitaniye
    (21, 0),  # 21:00 — Integratsiya
]


async def get_reminder_time() -> tuple[int, int]:
    """Get configured reminder hour and minute from Settings table."""
    async with session_factory() as session:
        hour_result = await session.execute(
            select(Setting).where(Setting.key == "reminder_hour")
        )
        hour_setting = hour_result.scalar_one_or_none()

        minute_result = await session.execute(
            select(Setting).where(Setting.key == "reminder_minute")
        )
        minute_setting = minute_result.scalar_one_or_none()

    hour = int(hour_setting.value) if hour_setting and hour_setting.value else 20
    minute = int(minute_setting.value) if minute_setting and minute_setting.value else 0
    return hour, minute


async def enqueue_scroll_slot(hour: int, ctx: None = None) -> None:
    """Enqueue scroll delivery for a specific time slot via ARQ.

    Args:
        hour: The hour (Moscow time) to deliver scrolls for.
        ctx: Unused — APScheduler passes no context.
    """
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    pool = await create_pool(redis_settings)
    try:
        await pool.enqueue_job("deliver_scroll_slot", hour)
        logger.info("Enqueued deliver_scroll_slot(hour=%d) via ARQ", hour)
    finally:
        await pool.close()


async def enqueue_evening_reminder(ctx: None = None) -> None:
    """Enqueue the evening scroll reminder task via ARQ."""
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    pool = await create_pool(redis_settings)
    try:
        await pool.enqueue_job("evening_scroll_reminder")
        logger.info("Enqueued evening_scroll_reminder via ARQ")
    finally:
        await pool.close()


async def enqueue_streak_warning(ctx: None = None) -> None:
    """Enqueue the streak loss warning task via ARQ."""
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    pool = await create_pool(redis_settings)
    try:
        await pool.enqueue_job("streak_loss_warning")
        logger.info("Enqueued streak_loss_warning via ARQ")
    finally:
        await pool.close()


async def enqueue_new_stream(ctx: None = None) -> None:
    """Enqueue the new stream notification task via ARQ."""
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    pool = await create_pool(redis_settings)
    try:
        await pool.enqueue_job("new_stream_notification")
        logger.info("Enqueued new_stream_notification via ARQ")
    finally:
        await pool.close()


async def enqueue_pending_notifications(ctx: None = None) -> None:
    """Enqueue the notification queue pump via ARQ (every minute).

    Picks up queued broadcasts (immediate + due scheduled ones).
    """
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    pool = await create_pool(redis_settings)
    try:
        await pool.enqueue_job("send_pending_notifications")
    finally:
        await pool.close()


async def schedule_jobs() -> None:
    """Configure and add all scheduled jobs."""
    from app.bot.services.settings_service import (
        get_delivery_slots,
        get_streak_warning_time,
    )

    # Scroll delivery slots (editable via admin panel, defaults 5/8/12/16/21)
    delivery_slots = await get_delivery_slots()
    for hour, minute in delivery_slots:
        job_id = f"scroll_slot_{hour:02d}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        scheduler.add_job(
            enqueue_scroll_slot,
            CronTrigger(hour=hour, minute=minute, timezone=settings.TZ),
            args=[hour],
            id=job_id,
            replace_existing=True,
        )
        logger.info("Scheduled scroll slot at %02d:%02d %s time", hour, minute, settings.TZ)

    # Evening reminder
    r_hour, r_minute = await get_reminder_time()
    if scheduler.get_job("evening_reminder"):
        scheduler.remove_job("evening_reminder")
    scheduler.add_job(
        enqueue_evening_reminder,
        CronTrigger(hour=r_hour, minute=r_minute, timezone=settings.TZ),
        id="evening_reminder",
        replace_existing=True,
    )
    logger.info("Scheduled evening reminder at %02d:%02d %s time", r_hour, r_minute, settings.TZ)

    # Streak loss warning (editable via admin panel, default 23:00)
    w_hour, w_minute = await get_streak_warning_time()
    if scheduler.get_job("streak_warning"):
        scheduler.remove_job("streak_warning")
    scheduler.add_job(
        enqueue_streak_warning,
        CronTrigger(hour=w_hour, minute=w_minute, timezone=settings.TZ),
        id="streak_warning",
        replace_existing=True,
    )
    logger.info(
        "Scheduled streak warning at %02d:%02d %s time", w_hour, w_minute, settings.TZ
    )

    # Notification queue pump (every minute — broadcasts + scheduled)
    if scheduler.get_job("pending_notifications"):
        scheduler.remove_job("pending_notifications")
    scheduler.add_job(
        enqueue_pending_notifications,
        IntervalTrigger(minutes=1),
        id="pending_notifications",
        replace_existing=True,
    )
    logger.info("Scheduled notification pump every minute")


async def main() -> None:
    """Start the APScheduler cron process."""
    logger.info("Scheduler starting...")
    await schedule_jobs()
    scheduler.start()
    logger.info(
        "Scheduler started — %d job(s) registered",
        len(scheduler.get_jobs()),
    )
    # Block forever
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
