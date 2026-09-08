"""Team service — group member queries for curators and mentors."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.user import Referral, User

MENTOR_ROLES: frozenset[str] = frozenset({"curator", "leader", "specialist", "master"})


@dataclass
class TeamMember:
    """A member of a curator's group with basic stats."""

    user_id: UUID
    first_name: str
    username: str | None
    streak: int
    is_active: bool


async def get_group_members(user_id: UUID, limit: int = 10) -> list[TeamMember]:
    """Return the group members referred by user_id, up to limit.

    Uses the referrals table where referrer_id = user_id.
    """
    async with session_factory() as session:
        result = await session.execute(
            select(Referral).where(Referral.referrer_id == user_id).limit(limit)
        )
        referrals = list(result.scalars().all())

        if not referrals:
            return []

        referee_ids = [r.referee_id for r in referrals]
        user_result = await session.execute(
            select(User).where(User.id.in_(referee_ids))
        )
        users = {u.id: u for u in user_result.scalars().all()}

        members: list[TeamMember] = []
        for ref in referrals:
            u = users.get(ref.referee_id)
            if u is not None:
                members.append(
                    TeamMember(
                        user_id=u.id,
                        first_name=u.first_name,
                        username=u.username,
                        streak=u.streak,
                        is_active=u.is_active,
                    )
                )
        return members
