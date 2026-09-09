"""ScrollType SQLAlchemy model — defines the 9 scroll types with their commands and schedules."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ScrollType(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A scroll type (Rassvet, Ogne, etc.) with its command, time, and XP."""

    __tablename__ = "scroll_types"

    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    # rassvet, ogne, korni, vetr, sledy, zrya, pitaniye, integratsiya, otchet

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # "Свиток Рассвета", "Свиток Огня", etc.

    command: Mapped[str] = mapped_column(String(30), nullable=False)
    # /wakeup, /cold, /scan, /scanreport, /breath, /micro, /focus, /food, /sleep, /report

    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    # Delivery hour (Moscow time): 5, 8, 12, 16, 21, or -1 for "any time"

    minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Delivery minute: 0 or 30

    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # XP awarded for completing this scroll

    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Short description of what this scroll is about

    requires_meditation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # True for Korni (only on meditation days: 1, 8, 15, 22, 29, 36, 43, 50, 57, 64, 71, 78, 85)

    is_breathing_day_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # True for extra Vetr on breathing days (7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 84)

    is_awareness_day_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # True for awareness-day-only scrolls

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Display order within a time slot
