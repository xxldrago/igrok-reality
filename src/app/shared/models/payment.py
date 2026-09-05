"""Payment SQLAlchemy model — Platega.io payment transactions."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Payment transaction record from Platega.io."""

    __tablename__ = "payments"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    platega_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # kopecks
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending/succeeded/canceled/chargebacked/refunded
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
