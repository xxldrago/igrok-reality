"""Scroll service — business logic for daily scroll delivery and user queries."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.scroll import Scroll
from app.shared.models.user import User


async def get_scroll_for_user(user: User) -> Scroll | None:
    """Return the scroll matching the user's archetype for their current day.

    Calculates the day number as (today - started_at).days + 1.
    Returns None if started_at is not set or day_number is outside 1-90.
    """
    if user.started_at is None:
        return None

    day_number = (date.today() - user.started_at.date()).days + 1

    if day_number < 1 or day_number > 90:
        return None

    async with session_factory() as session:
        result = await session.execute(
            select(Scroll).where(
                Scroll.day_number == day_number,
                Scroll.archetype == user.archetype,
            )
        )
        return result.scalar_one_or_none()


async def get_active_users() -> list[User]:
    """Return all users with archetype set and started_at not null.

    These are users eligible for daily scroll delivery.
    """
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(
                User.archetype.isnot(None),
                User.started_at.isnot(None),
            )
        )
        return list(result.scalars().all())
