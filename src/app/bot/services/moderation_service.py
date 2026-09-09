"""Moderation service — submit and manage player reports."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.moderation_report import ModerationReport
from app.shared.models.user import User


async def submit_report(user_id: UUID, reason: str) -> ModerationReport:
    """Submit a moderation report for a user.

    Called by the /help handler when a player requests assistance.
    """
    async with session_factory() as session:
        # Verify user exists
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"User {user_id} not found")

        report = ModerationReport(
            user_id=user_id,
            reason=reason,
            status="pending",
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        return report
