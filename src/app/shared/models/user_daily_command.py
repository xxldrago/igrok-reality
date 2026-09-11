"""UserDailyCommand SQLAlchemy model — tracks which commands a user has completed each day."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserDailyCommand(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single command completion by a user on a specific day."""

    __tablename__ = "user_daily_commands"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "quest_day", "command", "slot",
            name="uq_user_day_command_slot",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    quest_day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Quest day 1-90

    command: Mapped[str] = mapped_column(String(30), nullable=False)
    # /wakeup, /cold, /scan, /scanreport, /breath, /micro, /focus, /food, /sleep, /report

    slot: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    # Breathing-day /breath repeats: "morning" | "day" | "evening", else ""

    scroll_type_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("scroll_types.id"), nullable=True
    )

    daily_scroll_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("daily_scrolls.id"), nullable=True
    )

    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    report_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_media_url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    report_media_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # "photo", "video", "document"
