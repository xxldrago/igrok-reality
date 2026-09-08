"""RoleHistory SQLAlchemy model — audit log for role changes."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RoleHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Records role transitions for a user."""

    __tablename__ = "role_history"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    old_role: Mapped[str] = mapped_column(String(50), nullable=False)
    new_role: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)