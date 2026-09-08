"""ScrollArchetypeTask SQLAlchemy model — per-archetype individual task for each scroll."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ScrollArchetypeTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-archetype individual task linked to a scroll.

    One scroll (per day) has up to 4 rows here — one per archetype (head/shell/
    whirlwind/ghost), each carrying the archetype-specific "psychics" task.
    """

    __tablename__ = "scroll_archetype_tasks"

    scroll_id: Mapped[UUID] = mapped_column(ForeignKey("scrolls.id"), index=True, nullable=False)
    archetype_code: Mapped[str] = mapped_column(String(50), nullable=False)
    task_text: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("scroll_id", "archetype_code"),)
