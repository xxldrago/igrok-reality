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
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # scroll_reminder|streak_warning|system|broadcast
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Broadcast attachments + scheduling (nullable for other notification types)
    media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # photo|video|document
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    audience: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # archetype or 'all'
    parse_mode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # HTML|Markdown or None