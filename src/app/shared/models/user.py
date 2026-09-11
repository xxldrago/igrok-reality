"""User and Referral SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Telegram user data, archetype, XP, streak."""

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), default="")
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    archetype: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # head/shell/whirlwind/ghost
    xp: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    streak_last_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    access_granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    referral_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    referred_by_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Krasnoyarsk")
    role: Mapped[str] = mapped_column(String(50), default="player")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    group_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("groups.id"), nullable=True)
    clan_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("clans.id"), nullable=True)


class Referral(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Referral relationships between users."""

    __tablename__ = "referrals"

    referrer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    referee_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    __table_args__ = (UniqueConstraint("referrer_id", "referee_id"),)
