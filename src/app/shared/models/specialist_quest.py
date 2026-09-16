"""SpecialistQuest SQLAlchemy model — additional quests created by specialists."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SpecialistQuest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An additional quest created by a specialist for their group."""

    __tablename__ = "specialist_quests"

    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("groups.id"), nullable=False, index=True
    )
    specialist_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    xp_reward: Mapped[int] = mapped_column(Integer, default=10)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
