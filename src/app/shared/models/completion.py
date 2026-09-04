"""UserCompletion SQLAlchemy model — quest completion with XP and streak tracking."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, UUIDPrimaryKeyMixin


class UserCompletion(Base, UUIDPrimaryKeyMixin):
    """Records when a user completes a scroll, with XP awarded."""

    __tablename__ = "user_completions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    scroll_id: Mapped[UUID] = mapped_column(ForeignKey("scrolls.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    xp_awarded: Mapped[int] = mapped_column(Integer, default=10)

    __table_args__ = (UniqueConstraint("user_id", "scroll_id"),)
