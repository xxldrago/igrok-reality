"""APScheduler cron process entrypoint."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def main() -> None:
    """Start the APScheduler cron process."""
    logger.info("Scheduler starting...")
    scheduler.start()
    # Block forever
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
