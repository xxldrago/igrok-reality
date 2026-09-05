"""APScheduler cron process entrypoint."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from arq import create_pool
from arq.connections import RedisSettings

from app.shared.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def enqueue_daily_scrolls(ctx: None = None) -> None:
    """Enqueue the daily scroll delivery task via ARQ.

    Called by APScheduler at 08:00 Moscow time. Creates a short-lived
    ARQ pool to enqueue the deliver_daily_scrolls task, then closes
    the connection.

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


# Register the daily scroll delivery cron job at 08:00 Moscow time
scheduler.add_job(
    enqueue_daily_scrolls,
    CronTrigger(hour=8, minute=0, timezone="Europe/Moscow"),
    id="daily_scroll_delivery",
    replace_existing=True,
)


async def main() -> None:
    """Start the APScheduler cron process."""
    logger.info("Scheduler starting...")
    scheduler.start()
    logger.info(
        "Scheduler started — %d job(s) registered",
        len(scheduler.get_jobs()),
    )
    # Block forever
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
