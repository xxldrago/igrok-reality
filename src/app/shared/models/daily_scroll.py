"""DailyScroll SQLAlchemy model — scroll content for each day + scroll_type combination."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DailyScroll(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Actual scroll content for a specific day and scroll type."""

    __tablename__ = "daily_scrolls"
    __table_args__ = (
        UniqueConstraint("day_number", "scroll_type_id", name="uq_daily_scroll_day_type"),
    )

    day_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Quest day 1-90

    scroll_type_id: Mapped[UUID] = mapped_column(
        ForeignKey("scroll_types.id"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    # Section header for this scroll

    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # The actual scroll text content (markdown)

    media_file_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Telegram file_id for photo/video attachment

    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # When this scroll was published to the channel (for idempotency)
