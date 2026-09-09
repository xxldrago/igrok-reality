"""Notification SQLAlchemy model — queued notifications for users."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A queued notification for a user (or system-wide)."""

    __tablename__ = "notifications"

    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # scroll_reminder|streak_warning|system
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)