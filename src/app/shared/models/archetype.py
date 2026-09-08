"""Archetype SQLAlchemy model — reference table of the 4 player archetypes."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Archetype(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reference table describing the 4 player archetypes.

    Codes follow the internal naming used across the bot:
    ``head``/Голова, ``shell``/Панцирь, ``whirlwind``/Вихрь, ``ghost``/Призрак.
    """

    __tablename__ = "archetypes"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # Голова/Панцирь/Вихрь/Призрак
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
