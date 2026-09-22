"""Group SQLAlchemy model — mentor groups (curator, leader, specialist) and quest cohorts."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Group(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A group: mentor-owned (curator/leader/specialist) or auto quest cohort.

    Quest groups (type="quest") are auto-created, ownerless, gather paid
    users up to max_members and launch the quest at min_size members.
    """

    __tablename__ = "groups"

    owner_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # curator|leader|specialist|quest
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=10)
    launched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Quest groups only: set when min_size paid members gathered