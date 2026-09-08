"""Clan SQLAlchemy model — leader-created clans for team competition."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Clan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A clan created by a leader, with member aggregation."""

    __tablename__ = "clans"

    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class ClanMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Membership of a user in a clan."""

    __tablename__ = "clan_members"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    clan_id: Mapped[str] = mapped_column(ForeignKey("clans.id"), nullable=False)