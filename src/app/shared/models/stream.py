"""Stream SQLAlchemy model — quest cohorts of 30-50 paid users."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Stream(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A quest stream: gathers paid users, launches at min_size, caps at max_size."""

    __tablename__ = "streams"

    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="gathering")
    # gathering | launched
    min_size: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_size: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    launched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
