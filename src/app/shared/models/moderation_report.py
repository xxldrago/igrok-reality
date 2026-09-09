"""ModerationReport SQLAlchemy model — player complaints and moderation actions."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ModerationReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A moderation report submitted by a player (via /help) or system."""

    __tablename__ = "moderation_reports"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # status: pending | warned | banned | excluded
