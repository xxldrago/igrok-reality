"""User service — database operations for User and Referral records."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.user import Referral, User

# Paid access: each successful payment grants this many days from
# max(now, previous expiry) — early renewal stacks, late renewal restarts.
ACCESS_PERIOD_DAYS = 30

# Days before expiry when daily renewal reminders are sent (each day).
RENEWAL_REMINDER_DAYS = (3, 2, 1)


def is_access_active(user) -> bool:
    """Whether the user currently has paid access (access_until in the future)."""
    until = getattr(user, "access_until", None)
    if until is None:
        return False
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until > datetime.now(timezone.utc)


def days_until_expiry(user) -> int | None:
    """Full days left until access expiry (date-based, UTC). None if never paid."""
    until = getattr(user, "access_until", None)
    if until is None:
        return None
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return (until.date() - datetime.now(timezone.utc).date()).days


def access_gate_message(user) -> str | None:
    """Return the denial text when access is missing/expired, else None."""
    if user is None or getattr(user, "paid_at", None) is None:
        return "Сначала оплатите участие: /pay"
    if not is_access_active(user):
        return "⏳ Доступ к игре завершён. Продлите участие: /pay"
    return None


def grant_access_period(db_user, now: datetime | None = None) -> None:
    """Extend access_until by one period from max(now, previous expiry).

    Mutates the attached ORM object (caller commits).
    """
    now = now or datetime.now(timezone.utc)
    prev = db_user.access_until
    if prev is not None and prev.tzinfo is None:
        prev = prev.replace(tzinfo=timezone.utc)
    base = max(now, prev) if prev is not None else now
    db_user.access_until = base + timedelta(days=ACCESS_PERIOD_DAYS)


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


async def get_user_by_id(user_id: UUID) -> User | None:
    """Look up a user by their UUID primary key."""
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


async def create_user(
    telegram_id: int,
    first_name: str,
    last_name: str | None,
    username: str | None,
    archetype: str,
    referral_code: str,
    started_at: datetime | None = None,
    quiz_answers: str | None = None,
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
            started_at=started_at,
            quiz_answers=quiz_answers,
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


async def ensure_referral_code(user_id: UUID) -> str:
    """Return the user's referral code, generating and persisting one if missing.

    Handles legacy users created before referral codes existed.
    """
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"User {user_id} not found")
        if not user.referral_code:
            user.referral_code = generate_referral_code()
            await session.commit()
            await session.refresh(user)
        return user.referral_code


async def get_group_leaders(group_id: UUID, limit: int = 10) -> list[User]:
    """Top users of one quest group by XP (descending)."""
    async with session_factory() as session:
        result = await session.execute(
            select(User)
            .where(User.group_id == group_id)
            .order_by(User.xp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_user_by_referral_code(referral_code: str) -> User | None:
    """Look up a user by their referral code (for deep-link resolution)."""
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.referral_code == referral_code)
        )
        return result.scalar_one_or_none()