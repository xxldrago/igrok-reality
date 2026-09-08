"""Role service — role changes with history tracking."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.role_history import RoleHistory
from app.shared.models.user import User

VALID_ROLES = frozenset({"player", "curator", "leader", "specialist", "master"})


async def change_role(
    user_id: UUID,
    new_role: str,
    changed_by_id: UUID | None = None,
) -> bool:
    """Change a user's role and record the transition in role_history.

    Returns True on success, False if role is invalid or user not found.
    """
    if new_role not in VALID_ROLES:
        return False

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return False

        old_role = user.role
        if old_role == new_role:
            return True  # No change needed

        user.role = new_role

        history = RoleHistory(
            user_id=user_id,
            old_role=old_role,
            new_role=new_role,
            changed_by_id=changed_by_id,
        )
        session.add(history)

        await session.commit()
        return True


async def get_role_history(user_id: UUID) -> list[RoleHistory]:
    """Return role change history for a user, newest first."""
    async with session_factory() as session:
        result = await session.execute(
            select(RoleHistory)
            .where(RoleHistory.user_id == user_id)
            .order_by(RoleHistory.created_at.desc())
        )
        return list(result.scalars().all())


def is_valid_role(role: str) -> bool:
    """Check if a role is in the valid set."""
    return role in VALID_ROLES