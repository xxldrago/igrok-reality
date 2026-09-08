"""Scroll service — business logic for daily scroll delivery and user queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.scroll import Scroll
from app.shared.models.scroll_archetype_task import ScrollArchetypeTask
from app.shared.models.user import User

# Section headers used when composing the 5-section scroll message.
SECTION_HEADERS: dict[str, str] = {
    "common_task": "Общее задание",
    "ritual": "Утренний ритуал",
    "habits": "Привычки",
    "micromovements": "Микродвижения",
}


@dataclass
class ScrollContent:
    """Composed scroll content for a user's day + archetype.

    Carries both the fully formatted message text and the structured fields so
    downstream flows (09-02 report, 09-06 content editor) can render the scroll
    in different formats without re-joining the DB.
    """

    scroll: Scroll
    individual_task: str
    archetype_code: str

    @property
    def text(self) -> str:
        """Return the fully formatted 5-section scroll message."""
        return build_scroll_text(self.scroll, self.individual_task)


def build_scroll_text(scroll: Scroll, individual_task: str) -> str:
    """Compose the 5-section scroll message from a Scroll and its individual task.

    The 4 shared sections (common task, ritual, habits, micromovements) come from
    the scroll, and the per-archetype individual task is appended last.

    Args:
        scroll: The per-day Scroll with the 4 shared sections.
        individual_task: The user's archetype-specific task text.

    Returns:
        Formatted multi-section message ready for Telegram delivery.
    """
    lines: list[str] = [f"📜 День {scroll.day_number}"]

    for attr, header in SECTION_HEADERS.items():
        value = getattr(scroll, attr)
        if value:
            lines.append("")
            lines.append(f"🔹 {header}:")
            lines.append(str(value))

    if individual_task:
        lines.append("")
        lines.append(f"🔸 Индивидуальное задание:")
        lines.append(individual_task)

    return "\n".join(lines)


async def get_scroll_content(user: User) -> ScrollContent | None:
    """Return composed scroll content for a user's current day and archetype.

    Loads the per-day scroll for the user's quest day and joins the matching
    per-archetype individual task from ``scroll_archetype_tasks``.

    Returns None if started_at is not set, day_number is outside 1-90, or neither
    the scroll nor the archetype task can be found.
    """
    if user.started_at is None or user.archetype is None:
        return None

    day_number = (date.today() - user.started_at.date()).days + 1

    if day_number < 1 or day_number > 90:
        return None

    async with session_factory() as session:
        result = await session.execute(
            select(Scroll).where(Scroll.day_number == day_number)
        )
        scroll = result.scalar_one_or_none()
        if scroll is None:
            return None

        task_result = await session.execute(
            select(ScrollArchetypeTask).where(
                ScrollArchetypeTask.scroll_id == scroll.id,
                ScrollArchetypeTask.archetype_code == user.archetype,
            )
        )
        task = task_result.scalar_one_or_none()
        individual_task = task.task_text if task is not None else ""

        return ScrollContent(
            scroll=scroll,
            individual_task=individual_task,
            archetype_code=user.archetype,
        )


async def get_scroll_for_user(user: User) -> Scroll | None:
    """Return the per-day scroll for the user's current quest day.

    Calculates the day number as (today - started_at).days + 1.
    Returns None if started_at is not set or day_number is outside 1-90.
    """
    if user.started_at is None:
        return None

    day_number = (date.today() - user.started_at.date()).days + 1

    if day_number < 1 or day_number > 90:
        return None

    async with session_factory() as session:
        result = await session.execute(
            select(Scroll).where(Scroll.day_number == day_number)
        )
        return result.scalar_one_or_none()


async def get_active_users() -> list[User]:
    """Return all users with archetype set and started_at not null.

    These are users eligible for daily scroll delivery.
    """
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(
                User.archetype.isnot(None),
                User.started_at.isnot(None),
            )
        )
        return list(result.scalars().all())
