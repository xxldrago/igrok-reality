"""ARQ background worker process entrypoint."""

from __future__ import annotations

import logging

from arq.worker import Worker

from app.shared.config import settings
from app.worker.settings import WorkerSettings

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the ARQ background worker (sync entrypoint)."""
    logger.info("Worker starting...")
    worker_settings = WorkerSettings()
    worker = Worker(
        functions=worker_settings.functions,
        redis_settings=worker_settings.redis_settings,
        max_tries=worker_settings.max_tries,
        retry_delay=worker_settings.retry_delay,
    )
    worker.run()


if __name__ == "__main__":
    main()
