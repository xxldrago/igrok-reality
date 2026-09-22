"""Quest streams (cohorts): gather paid users, launch at min_size, cap at max_size.

Rules:
- Users get scrolls only after their stream launches (started_at set).
- A gathering stream launches when paid members reach min_size (default 30)
  or when the emulate_full_group test toggle is on.
- A stream caps at max_size members (default 50); the next payer opens
  a new gathering stream.
- Quest clock starts the next midnight (server TZ) after launch/join, so
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
from app.shared.models.stream import Stream
from app.shared.models.user import User
from app.shared.models.user_daily_command import UserDailyCommand

from app.bot.services.settings_service import get_setting

logger = logging.getLogger(__name__)


async def get_stream_sizes() -> tuple[int, int]:
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
    """Test toggle: pretend every gathering stream is full."""
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


async def _paid_count(session, stream_id: UUID) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(
            User.stream_id == stream_id, User.paid_at.isnot(None)
        )
    )
    return result.scalar() or 0


async def _member_count(session, stream_id: UUID) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(User.stream_id == stream_id)
    )
    return result.scalar() or 0


async def get_or_create_gathering_stream(session) -> Stream:
    """Latest gathering stream with free slots, or a fresh one (number+1)."""
    _, max_size = await get_stream_sizes()
    result = await session.execute(
        select(Stream)
        .where(Stream.status == "gathering")
        .order_by(Stream.number.desc())
        .limit(1)
    )
    stream = result.scalar_one_or_none()
    if stream is not None and await _member_count(session, stream.id) < max_size:
        return stream
    if stream is not None:
        stream.status = "closed"
    number_result = await session.execute(select(func.coalesce(func.max(Stream.number), 0)))
    stream = Stream(number=(number_result.scalar() or 0) + 1, status="gathering")
    session.add(stream)
    await session.flush()
    logger.info("stream #%d opened for gathering", stream.number)
    return stream


async def maybe_launch_stream(session, stream: Stream) -> bool:
    """Launch a gathering stream when it has min_size paid members (or emulate on).

    Launched members with no quest clock yet start next midnight.
    Returns True when the stream launched now.
    """
    if stream.status != "gathering":
        return False
    min_size, _ = await get_stream_sizes()
    paid = await _paid_count(session, stream.id)
    emulate = await get_emulate_full_group()
    if not emulate and paid < min_size:
        return False

    now = datetime.now(timezone.utc)
    stream.status = "launched"
    stream.launched_at = now
    members = await session.execute(
        select(User).where(User.stream_id == stream.id, User.started_at.is_(None))
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
        "stream #%d launched with %d paid members (emulate=%s)",
        stream.number, paid, emulate,
    )
    return True


async def assign_user_to_stream(user_id: UUID) -> Stream | None:
    """Put a paid user into a gathering stream, launching it if ready.

    Members of an already-launched stream start next midnight.
    Returns the stream, or None when the user is unknown/unpaid.
    """
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.paid_at is None:
            return None

        stream: Stream | None = None
        if user.stream_id is not None:
            result = await session.execute(select(Stream).where(Stream.id == user.stream_id))
            stream = result.scalar_one_or_none()

        if stream is None:
            stream = await get_or_create_gathering_stream(session)
            user.stream_id = stream.id

        if stream.status == "launched" and user.started_at is None:
            has_commands = await session.execute(
                select(UserDailyCommand.id)
                .where(UserDailyCommand.user_id == user.id)
                .limit(1)
            )
            if has_commands.scalar_one_or_none() is None:
                user.started_at = next_midnight()
        else:
            await maybe_launch_stream(session, stream)

        await session.commit()
        await session.refresh(stream)
        return stream


async def list_streams() -> list[dict]:
    """Streams with member/paid counters for the admin panel."""
    async with session_factory() as session:
        result = await session.execute(select(Stream).order_by(Stream.number.asc()))
        streams = list(result.scalars().all())
        out = []
        for stream in streams:
            total = await _member_count(session, stream.id)
            paid = await _paid_count(session, stream.id)
            out.append(
                {
                    "id": str(stream.id),
                    "number": stream.number,
                    "status": stream.status,
                    "min_size": stream.min_size,
                    "max_size": stream.max_size,
                    "members": total,
                    "paid": paid,
                    "launched_at": stream.launched_at.isoformat() if stream.launched_at else None,
                    "created_at": stream.created_at.isoformat() if stream.created_at else None,
                }
            )
        return out
