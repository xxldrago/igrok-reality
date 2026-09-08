"""Group service — mentor group membership and queries."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.group import Group
from app.shared.models.user import User


# Valid mentor roles
MENTOR_ROLES = frozenset({"curator", "leader", "specialist", "master"})


@dataclass
class GroupMember:
    """A member of a mentor's group with basic stats."""

    user_id: UUID
    first_name: str
    username: str | None
    streak: int
    is_active: bool


async def get_user_group(user_id: UUID) -> Group | None:
    """Return the group the user belongs to (via users.group_id)."""
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.group_id is None:
            return None
        result = await session.execute(select(Group).where(Group.id == user.group_id))
        return result.scalar_one_or_none()


async def get_group_members(group_id: UUID, limit: int = 100) -> list[GroupMember]:
    """Return members of a group via users.group_id."""
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.group_id == group_id).limit(limit)
        )
        users = list(result.scalars().all())

        return [
            GroupMember(
                user_id=u.id,
                first_name=u.first_name,
                username=u.username,
                streak=u.streak,
                is_active=u.is_active,
            )
            for u in users
        ]


async def create_group(owner_id: UUID, type_: str, name: str, max_members: int = 10) -> Group:
    """Create a new group and set the owner as its owner."""
    async with session_factory() as session:
        group = Group(owner_id=owner_id, type=type_, name=name, max_members=max_members)
        session.add(group)
        await session.flush()

        # Set owner's group_id to the new group
        result = await session.execute(select(User).where(User.id == owner_id))
        owner = result.scalar_one_or_none()
        if owner:
            owner.group_id = group.id

        await session.commit()
        await session.refresh(group)
        return group


async def assign_user_to_group(user_id: UUID, group_id: UUID) -> bool:
    """Assign a user to a group. Returns False if group is full."""
    async with session_factory() as session:
        # Check group capacity
        result = await session.execute(select(Group).where(Group.id == group_id))
        group = result.scalar_one_or_none()
        if group is None:
            return False

        count_result = await session.execute(
            select(User).where(User.group_id == group_id)
        )
        current_count = len(list(count_result.scalars().all()))
        if current_count >= group.max_members:
            return False

        # Assign user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return False

        user.group_id = group_id
        await session.commit()
        return True