"""ScrollDelivery SQLAlchemy model — maps delivered scroll messages for cleanup.

When a daily scroll is delivered, the bot message id is stored here.
On completion the delivery message is deleted; a nightly job deletes
messages whose quest day has expired.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ScrollDelivery(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A delivered scroll message awaiting completion or expiry cleanup."""

    __tablename__ = "scroll_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "quest_day", "scroll_code",
            name="uq_delivery_user_day_code",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    quest_day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scroll_code: Mapped[str] = mapped_column(String(30), nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
