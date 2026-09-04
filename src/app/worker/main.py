"""ARQ background worker process entrypoint."""

from __future__ import annotations

import asyncio
import logging

from arq.worker import Worker

from app.worker.settings import WorkerSettings

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the ARQ background worker."""
    logger.info("Worker starting...")
    worker = Worker(settings=WorkerSettings)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
