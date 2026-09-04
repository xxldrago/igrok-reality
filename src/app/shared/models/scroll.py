"""Scroll SQLAlchemy model — daily quest content (90 days)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Scroll(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Daily quest content — one scroll per day per archetype (90 days × 4 archetypes)."""

    __tablename__ = "scrolls"

    day_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–90
    archetype: Mapped[str] = mapped_column(String(50), nullable=False)  # head/shell/whirlwind/ghost
    text: Mapped[str] = mapped_column(Text, nullable=False)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (UniqueConstraint("day_number", "archetype"),)
