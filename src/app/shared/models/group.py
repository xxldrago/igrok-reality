"""Group SQLAlchemy model — mentor groups (curator, leader, specialist)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Group(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A mentor group owned by a curator/leader/specialist."""

    __tablename__ = "groups"

    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # curator|leader|specialist
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=10)