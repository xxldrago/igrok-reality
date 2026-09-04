"""Health check endpoint with PostgreSQL and Redis status."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import text

import redis.asyncio as aioredis

from app.shared.config import settings
from app.shared.database import get_session

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check PostgreSQL and Redis connectivity."""
    result: dict[str, str] = {"status": "healthy", "database": "ok", "redis": "ok"}

    # Check PostgreSQL
    try:
        async for session in get_session():
            await session.execute(text("SELECT 1"))
    except Exception:
        result["database"] = "error"
        result["status"] = "unhealthy"

    # Check Redis
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
    except Exception:
        result["redis"] = "error"
        result["status"] = "unhealthy"

    return result
