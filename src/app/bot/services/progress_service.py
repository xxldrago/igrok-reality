"""Progress service — completion recording, XP award, and leaderboard updates."""

from __future__ import annotations

from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import select

from app.shared.config import settings
from app.shared.database import session_factory
from app.shared.models.completion import UserCompletion
from app.shared.models.user import User


async def create_completion(
    user_id: UUID, scroll_id: UUID, xp: int = 10
) -> UserCompletion | None:
    """Record a scroll completion for a user.

    Returns the created UserCompletion, or None if already completed (idempotent).
    """
    async with session_factory() as session:
        existing = await session.execute(
            select(UserCompletion).where(
                UserCompletion.user_id == user_id,
                UserCompletion.scroll_id == scroll_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return None

        completion = UserCompletion(
            user_id=user_id,
            scroll_id=scroll_id,
            xp_awarded=xp,
        )
        session.add(completion)
        await session.commit()
        await session.refresh(completion)
        return completion


async def add_xp(user_id: UUID, xp: int) -> int:
    """Add XP to a user and return the new total."""
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.xp += xp
        await session.commit()
        return user.xp


async def update_leaderboard(user_id: UUID, xp: int) -> None:
    """Update the Redis leaderboard sorted set with the user's XP score."""
    redis = aioredis.from_url(settings.REDIS_URL)
    try:
        await redis.zadd("leaderboard:xp", {str(user_id): xp})
    finally:
        await redis.aclose()
