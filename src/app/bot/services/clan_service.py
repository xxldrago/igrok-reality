"""Clan service — clan creation, membership, and aggregate progress."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, func

from app.shared.database import session_factory
from app.shared.models.clan import Clan, ClanMember
from app.shared.models.user import User


@dataclass
class ClanProgress:
    """Aggregated progress metrics for a clan."""

    clan_id: UUID
    clan_name: str
    member_count: int
    total_xp: int
    avg_xp: float
    total_streak: int
    avg_streak: float


async def create_clan(owner_id: UUID, name: str) -> Clan:
    """Create a new clan with the given leader as owner."""
    async with session_factory() as session:
        clan = Clan(owner_id=owner_id, name=name)
        session.add(clan)
        await session.flush()

        # Create clan membership for owner
        clan_member = ClanMember(user_id=owner_id, clan_id=clan.id)
        session.add(clan_member)

        # Set owner's clan_id
        result = await session.execute(select(User).where(User.id == owner_id))
        owner = result.scalar_one_or_none()
        if owner:
            owner.clan_id = clan.id

        await session.commit()
        await session.refresh(clan)
        return clan


async def join_clan(user_id: UUID, clan_id: UUID) -> bool:
    """Add a user to a clan."""
    async with session_factory() as session:
        result = await session.execute(select(Clan).where(Clan.id == clan_id))
        clan = result.scalar_one_or_none()
        if clan is None:
            return False

        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return False

        # Check if already in a clan
        if user.clan_id is not None:
            return False

        clan_member = ClanMember(user_id=user_id, clan_id=clan_id)
        session.add(clan_member)
        user.clan_id = clan_id

        await session.commit()
        return True


async def leave_clan(user_id: UUID) -> bool:
    """Remove a user from their clan."""
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.clan_id is None:
            return False

        clan_id = user.clan_id
        user.clan_id = None

        # Remove clan membership
        result = await session.execute(
            select(ClanMember).where(ClanMember.user_id == user_id)
        )
        clan_member = result.scalar_one_or_none()
        if clan_member:
            await session.delete(clan_member)

        # If clan is now empty, optionally delete it (keep for history)
        count_result = await session.execute(
            select(func.count(ClanMember.id)).where(ClanMember.clan_id == clan_id)
        )
        if count_result.scalar() == 0:
            result = await session.execute(select(Clan).where(Clan.id == clan_id))
            clan = result.scalar_one_or_none()
            if clan:
                await session.delete(clan)

        await session.commit()
        return True


async def get_clan_members(clan_id: UUID) -> list[User]:
    """Return all members of a clan."""
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.clan_id == clan_id)
        )
        return list(result.scalars().all())


async def get_clan_progress(clan_id: UUID) -> ClanProgress | None:
    """Calculate aggregate progress for a clan."""
    async with session_factory() as session:
        result = await session.execute(select(Clan).where(Clan.id == clan_id))
        clan = result.scalar_one_or_none()
        if clan is None:
            return None

        members_result = await session.execute(
            select(User).where(User.clan_id == clan_id)
        )
        members = list(members_result.scalars().all())

        if not members:
            return ClanProgress(
                clan_id=clan.id,
                clan_name=clan.name,
                member_count=0,
                total_xp=0,
                avg_xp=0.0,
                total_streak=0,
                avg_streak=0.0,
            )

        total_xp = sum(m.xp for m in members)
        total_streak = sum(m.streak for m in members)

        return ClanProgress(
            clan_id=clan.id,
            clan_name=clan.name,
            member_count=len(members),
            total_xp=total_xp,
            avg_xp=total_xp / len(members),
            total_streak=total_streak,
            avg_streak=total_streak / len(members),
        )


async def get_user_clan(user_id: UUID) -> Clan | None:
    """Return the clan a user belongs to."""
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.clan_id is None:
            return None
        result = await session.execute(select(Clan).where(Clan.id == user.clan_id))
        return result.scalar_one_or_none()