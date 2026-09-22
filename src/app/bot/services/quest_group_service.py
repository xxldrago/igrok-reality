"""Quest group gathering: auto-create groups, fill to 50, launch at 30.

Rules:
- Paid users join the latest gathering quest group (auto-created as
  "Группа №N"); a full group (max_size members) opens a new one.
- Scrolls start only after the group launches at min_size paid members
  (default 30) or when the emulate_full_group test toggle is on.
- Quest clock starts next midnight (server TZ) after launch/join, so
  mid-day purchases begin receiving scrolls the next day.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.shared.config import settings
from app.shared.database import session_factory
from app.shared.models.group import Group
from app.shared.models.user import User
from app.shared.models.user_daily_command import UserDailyCommand

from app.bot.services.settings_service import get_setting

logger = logging.getLogger(__name__)


async def get_group_sizes() -> tuple[int, int]:
    """(min_size, max_size) from settings, defaults (30, 50)."""
    try:
        min_size = int(await get_setting("min_group_size", "30"))
    except (TypeError, ValueError):
        min_size = 30
    try:
        max_size = int(await get_setting("max_group_size", "50"))
    except (TypeError, ValueError):
        max_size = 50
    min_size = max(2, min_size)
    max_size = max(min_size, max_size)
    return min_size, max_size


async def get_emulate_full_group() -> bool:
    """Test toggle: pretend every gathering group is full."""
    try:
        val = await get_setting("emulate_full_group", "false")
    except Exception:
        return False
    return val.lower() not in ("", "false", "0", "no")


def next_midnight(now: datetime | None = None) -> datetime:
    """Next 00:00 in server TZ (quest clocks start at day boundary)."""
    tz = ZoneInfo(settings.TZ)
    now_tz = (now or datetime.now(timezone.utc)).astimezone(tz)
    midnight = (now_tz + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight


async def _paid_count(session, group_id: UUID) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(
            User.group_id == group_id, User.paid_at.isnot(None)
        )
    )
    return result.scalar() or 0


async def _member_count(session, group_id: UUID) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(User.group_id == group_id)
    )
    return result.scalar() or 0


async def _next_group_number(session) -> int:
    numbers = await session.execute(
        select(Group.name).where(Group.type == "quest")
    )
    max_n = 0
    for (name,) in numbers.all():
        try:
            n = int(str(name).split("№")[-1])
            max_n = max(max_n, n)
        except (ValueError, IndexError):
            continue
    return max_n + 1


async def get_or_create_gathering_group(session) -> Group:
    """Latest gathering quest group with free slots, or a fresh 'Группа №N'."""
    _, max_size = await get_group_sizes()
    result = await session.execute(
        select(Group)
        .where(Group.type == "quest", Group.launched_at.is_(None))
        .order_by(Group.created_at.desc())
        .limit(1)
    )
    group = result.scalar_one_or_none()
    if group is not None and await _member_count(session, group.id) < max_size:
        return group
    number = await _next_group_number(session)
    group = Group(
        name=f"Группа №{number}",
        type="quest",
        owner_id=None,
        max_members=max_size,
    )
    session.add(group)
    await session.flush()
    logger.info("quest group '%s' opened for gathering", group.name)
    return group


async def maybe_launch_group(session, group: Group) -> bool:
    """Launch a gathering quest group at min_size paid members (or emulate on).

    Launched members with no quest clock yet start next midnight.
    Returns True when the group launched now.
    """
    if group.launched_at is not None:
        return False
    min_size, _ = await get_group_sizes()
    paid = await _paid_count(session, group.id)
    emulate = await get_emulate_full_group()
    if not emulate and paid < min_size:
        return False

    now = datetime.now(timezone.utc)
    group.launched_at = now
    members = await session.execute(
        select(User).where(User.group_id == group.id, User.started_at.is_(None))
    )
    for member in members.scalars().all():
        has_commands = await session.execute(
            select(UserDailyCommand.id)
            .where(UserDailyCommand.user_id == member.id)
            .limit(1)
        )
        if has_commands.scalar_one_or_none() is None:
            member.started_at = next_midnight(now)
    await session.flush()
    logger.info(
        "quest group '%s' launched with %d paid members (emulate=%s)",
        group.name, paid, emulate,
    )
    return True


async def assign_user_to_group(user_id: UUID) -> Group | None:
    """Put a paid user into a gathering quest group, launching it if ready.

    Members of an already-launched group start next midnight.
    Returns the group, or None when the user is unknown/unpaid.
    """
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.paid_at is None:
            return None

        group: Group | None = None
        if user.group_id is not None:
            result = await session.execute(
                select(Group).where(Group.id == user.group_id, Group.type == "quest")
            )
            group = result.scalar_one_or_none()

        if group is None:
            group = await get_or_create_gathering_group(session)
            user.group_id = group.id

        if group.launched_at is not None and user.started_at is None:
            has_commands = await session.execute(
                select(UserDailyCommand.id)
                .where(UserDailyCommand.user_id == user.id)
                .limit(1)
            )
            if has_commands.scalar_one_or_none() is None:
                user.started_at = next_midnight()
        else:
            await maybe_launch_group(session, group)

        await session.commit()
        await session.refresh(group)
        return group


async def get_group_progress(group_id: UUID) -> tuple[int, int]:
    """(paid_members, min_size) for status messages."""
    min_size, _ = await get_group_sizes()
    async with session_factory() as session:
        paid = await _paid_count(session, group_id)
    return paid, min_size


async def list_quest_groups() -> list[dict]:
    """Quest groups with member/paid counters for the admin panel."""
    async with session_factory() as session:
        result = await session.execute(
            select(Group).where(Group.type == "quest").order_by(Group.created_at.asc())
        )
        groups = list(result.scalars().all())
        out = []
        for group in groups:
            total = await _member_count(session, group.id)
            paid = await _paid_count(session, group.id)
            out.append(
                {
                    "id": str(group.id),
                    "name": group.name,
                    "status": "launched" if group.launched_at else "gathering",
                    "members": total,
                    "paid": paid,
                    "launched_at": group.launched_at.isoformat() if group.launched_at else None,
                    "created_at": group.created_at.isoformat() if group.created_at else None,
                }
            )
        return out
