"""User service — database operations for User and Referral records."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.user import Referral, User


def generate_referral_code() -> str:
    """Return first 8 hex characters of a UUID4 as a referral code."""
    return uuid.uuid4().hex[:8]


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    """Look up a user by their Telegram ID."""
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def create_user(
    telegram_id: int,
    first_name: str,
    last_name: str | None,
    username: str | None,
    archetype: str,
    referral_code: str,
) -> User:
    """Create a new User record and return it."""
    async with session_factory() as session:
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            archetype=archetype,
            referral_code=referral_code,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_referral(referrer_code: str, referee_id: UUID) -> Referral | None:
    """Create a Referral record linking referrer to referee.

    Returns None if the referrer is not found or if referrer == referee.
    """
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.referral_code == referrer_code)
        )
        referrer = result.scalar_one_or_none()

        if referrer is None or referrer.id == referee_id:
            return None

        referral = Referral(
            referrer_id=referrer.id,
            referee_id=referee_id,
        )
        session.add(referral)
        await session.commit()
        await session.refresh(referral)
        return referral


async def get_user_by_referral_code(referral_code: str) -> User | None:
    """Look up a user by their referral code (for deep-link resolution)."""
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.referral_code == referral_code)
        )
        return result.scalar_one_or_none()
