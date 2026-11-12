"""ARQ background worker process entrypoint."""

from __future__ import annotations

import logging

from arq.worker import create_worker

from app.worker.settings import WorkerSettings

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the ARQ background worker (sync entrypoint)."""
    logger.info("Worker starting...")
    # create_worker maps only the attributes arq's Worker actually accepts,
    # so settings can grow without crashing the worker at startup.
    worker = create_worker(WorkerSettings())
    worker.run()


if __name__ == "__main__":
    main()
