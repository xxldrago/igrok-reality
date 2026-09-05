"""CommissionBalance SQLAlchemy model — mentor commission tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CommissionBalance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-user commission balance — earned, pending, and paid-out amounts in kopecks."""

    __tablename__ = "commission_balances"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True, nullable=False
    )
    total_earned: Mapped[int] = mapped_column(Integer, default=0)  # kopecks
    total_pending: Mapped[int] = mapped_column(Integer, default=0)  # kopecks
    total_paid_out: Mapped[int] = mapped_column(Integer, default=0)  # kopecks
    last_commission_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
