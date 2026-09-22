"""AdminUser SQLAlchemy model — panel login accounts (multiple masters allowed)."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AdminUser(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An admin panel account: login username, password hash, role."""

    __tablename__ = "admin_users"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="master")
    # master | leader | curator
    telegram: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
