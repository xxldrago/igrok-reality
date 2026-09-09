"""ARQ worker settings configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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


@dataclass
class WorkerSettings:
    """ARQ worker settings with Redis connection from application config."""

    functions: list[Any] = field(
        default_factory=lambda: [
            deliver_daily_scrolls,
            deliver_scroll_slot,
            evening_scroll_reminder,
            streak_loss_warning,
            new_stream_notification,
            send_pending_notifications,
        ]
    )
    cron_jobs: list[Any] = field(default_factory=list)  # APScheduler handles cron

    redis_settings: RedisSettings = field(
        default_factory=lambda: RedisSettings.from_dsn(settings.REDIS_URL)
    )
    max_tries: int = 3
    retry_delay: int = 60
