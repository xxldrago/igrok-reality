"""ARQ worker settings configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from arq.connections import RedisSettings

from app.shared.config import settings


@dataclass
class WorkerSettings:
    """ARQ worker settings with Redis connection from application config."""

    functions: list[Any] = field(default_factory=list)  # Will be populated in Phase 3
    cron_jobs: list[Any] = field(default_factory=list)  # Will be populated in Phase 3

    redis_settings: RedisSettings = field(
        default_factory=lambda: RedisSettings.from_dsn(settings.REDIS_URL)
    )
    max_tries: int = 3
    retry_delay: int = 60
