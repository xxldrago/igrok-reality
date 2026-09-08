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


async def get_publish_time() -> tuple[int, int]:
    """Get configured publish hour and minute from Settings table."""
    async with session_factory() as session:
        hour_result = await session.execute(
            select(Setting).where(Setting.key == "scroll_publish_hour")
        )
        hour_setting = hour_result.scalar_one_or_none()

        minute_result = await session.execute(
            select(Setting).where(Setting.key == "scroll_publish_minute")
        )
        minute_setting = minute_result.scalar_one_or_none()

    hour = int(hour_setting.value) if hour_setting and hour_setting.value else 8
    minute = int(minute_setting.value) if minute_setting and minute_setting.value else 0
    return hour, minute


async def enqueue_daily_scrolls(ctx: None = None) -> None:
    """Enqueue the daily scroll delivery task via ARQ.

    Called by APScheduler at the configured time (default 08:00 Moscow).
    Creates a short-lived ARQ pool to enqueue the deliver_daily_scrolls task,
    then closes the connection.

    Args:
        ctx: Unused — APScheduler passes no context, but the signature
             must accept an optional argument.
    """
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    pool = await create_pool(redis_settings)
    try:
        await pool.enqueue_job("deliver_daily_scrolls")
        logger.info("Enqueued deliver_daily_scrolls via ARQ")
    finally:
        await pool.close()


async def schedule_jobs() -> None:
    """Configure and add the daily scroll delivery job."""
    hour, minute = await get_publish_time()

    # Remove existing job if any
    if scheduler.get_job("daily_scroll_delivery"):
        scheduler.remove_job("daily_scroll_delivery")

    scheduler.add_job(
        enqueue_daily_scrolls,
        CronTrigger(hour=hour, minute=minute, timezone="Europe/Moscow"),
        id="daily_scroll_delivery",
        replace_existing=True,
    )
    logger.info("Scheduled daily scroll delivery at %02d:%02d Moscow time", hour, minute)


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
