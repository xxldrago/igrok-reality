"""ARQ background worker process entrypoint."""

from __future__ import annotations

import logging

from arq.worker import Worker
from arq.connections import RedisSettings

from app.shared.config import settings
from app.worker.tasks.scrolls import deliver_daily_scrolls
from app.worker.tasks.scroll_slot import deliver_scroll_slot
from app.worker.tasks.notifications import (
    evening_scroll_reminder,
    streak_loss_warning,
    new_stream_notification,
    send_pending_notifications,
)

logger = logging.getLogger(__name__)

FUNCTIONS = [
    deliver_daily_scrolls,
    deliver_scroll_slot,
    evening_scroll_reminder,
    streak_loss_warning,
    new_stream_notification,
    send_pending_notifications,
]


def main() -> None:
    """Start the ARQ background worker (sync entrypoint)."""
    logger.info("Worker starting...")
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    worker = Worker(
        functions=FUNCTIONS,
        redis_settings=redis_settings,
        max_tries=3,
    )
    worker.run()


if __name__ == "__main__":
    main()
