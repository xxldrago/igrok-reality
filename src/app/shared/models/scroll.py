"""Scroll SQLAlchemy model — daily quest content (90 days, 5-section structure)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Scroll(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Daily quest content — one scroll per day with 5 structured sections.

    The 4 shared sections (common task, ritual, habits, micromovements) live on
    this table; the per-archetype individual task lives in ``scroll_archetype_tasks``.
    """

    __tablename__ = "scrolls"

    day_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–90
    common_task: Mapped[str] = mapped_column(Text, nullable=False)  # физика
    ritual: Mapped[str] = mapped_column(Text, nullable=False)  # утренний ритуал
    habits: Mapped[str] = mapped_column(Text, nullable=False)  # простые привычки
    micromovements: Mapped[str] = mapped_column(Text, nullable=False)  # микродвижения
    media_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("day_number"),)
