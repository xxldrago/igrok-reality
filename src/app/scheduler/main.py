"""APScheduler cron process entrypoint."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select

from app.shared.config import settings
from app.shared.database import session_factory
from app.shared.models.settings import Setting

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Time slots for scroll delivery (Moscow time)
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


async def schedule_jobs() -> None:
    """Configure and add all scheduled jobs."""
    # Scroll delivery slots (5:00, 8:00, 12:00, 16:00, 21:00)
    for hour, minute in DELIVERY_SLOTS:
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

    # Streak loss warning (runs at 23:00 by default)
    if scheduler.get_job("streak_warning"):
        scheduler.remove_job("streak_warning")
    scheduler.add_job(
        enqueue_streak_warning,
        CronTrigger(hour=23, minute=0, timezone=settings.TZ),
        id="streak_warning",
        replace_existing=True,
    )
    logger.info("Scheduled streak warning at 23:00 %s time", settings.TZ)


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
