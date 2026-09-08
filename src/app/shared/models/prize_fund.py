"""PrizeFund SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PrizeFund(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Prize fund pool for distributing rewards."""

    __tablename__ = "prize_funds"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, default=0)  # kopecks
    percent_rule: Mapped[str] = mapped_column(String(20), default="xp")  # xp|streak|custom
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|distributed
    distributed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class PrizeFundPayout(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual payout from a prize fund."""

    __tablename__ = "prize_fund_payouts"

    prize_fund_id: Mapped[UUID] = mapped_column(ForeignKey("prize_funds.id"), index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)