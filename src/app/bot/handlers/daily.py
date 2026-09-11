"""Daily command handlers — /wakeup, /cold, /scan, /scanreport, /breath, /micro, /focus, /food, /sleep, /report."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ContentType, Message
from sqlalchemy import select

from app.shared.config import settings
from app.bot.services.day_type import (
    COMMAND_TO_SCROLL_CODE,
    GRACE_PERIOD_HOURS,
    get_day_type,
    get_available_scroll_codes,
)
from app.bot.services.scroll_service import get_scroll_for_user
from app.bot.services.settings_service import get_grace_period_hours
from app.bot.services.user_service import get_user_by_telegram_id
from app.shared.database import session_factory
from app.shared.models.daily_scroll import DailyScroll
from app.shared.models.scroll_type import ScrollType
from app.shared.models.user_daily_command import UserDailyCommand

if TYPE_CHECKING:
    pass

daily_router = Router(name="daily")


class ReportState(StatesGroup):
    """FSM state for /report command (optional text/photo attachment)."""

    waiting_for_report = State()


def _get_quest_day(
    user, tz_name: str, now: datetime | None = None, grace_hours: int | None = None
) -> int:
    """Calculate the current quest day for a user based on their timezone.

    Applies the grace period: if it's within grace_hours after midnight
    local time, the command counts for the PREVIOUS day (night-shift workers).
    grace_hours defaults to GRACE_PERIOD_HOURS (callers pass the DB value).
    """
    if user.started_at is None:
        return 0
    tz = ZoneInfo(tz_name)
    now = now or datetime.now(tz)
    started = user.started_at.replace(tzinfo=timezone.utc).astimezone(tz)

    # Determine which day this command belongs to
    grace = GRACE_PERIOD_HOURS if grace_hours is None else grace_hours
    effective_date = now.date()
    if grace > 0 and now.hour < grace:
        effective_date = now.date() - timedelta(days=1)

    delta = (effective_date - started.date()).days
    return min(delta + 1, 90)  # Clamp to 90


async def _is_command_allowed(
    user_id, quest_day: int, command: str, scroll_code: str, now: datetime | None = None
) -> tuple[bool, str]:
    """Check if a command is allowed for this user on this day.

    Returns (allowed, reason_if_not).
    """
    # Get scroll type
    async with session_factory() as session:
        result = await session.execute(
            select(ScrollType).where(ScrollType.code == scroll_code)
        )
        scroll_type = result.scalar_one_or_none()
        if scroll_type is None:
            return False, "Неизвестный тип свитка."

        # Check meditation requirement
        day_type = get_day_type(quest_day)
        if scroll_type.requires_meditation and not day_type.is_meditation:
            return False, "Свиток Корней доступен только в дни медитации (1, 8, 15, 22...)."

        # Check awareness day restriction
        if day_type.is_awareness and scroll_code not in ("zrya", "otchet"):
            return False, "В день осознания доступны только Свиток Зря и Отчёт."

        # Check breathing day extras
        if scroll_type.is_breathing_day_only and not day_type.is_breathing:
            return False, "Этот свиток доступен только в дни дыхания (7, 14, 21, 28...)."

        # Check if command already used today
        result = await session.execute(
            select(UserDailyCommand).where(
                UserDailyCommand.user_id == user_id,
                UserDailyCommand.quest_day == quest_day,
                UserDailyCommand.command == command,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return False, "Эта команда уже использована сегодня."

        return True, ""


async def _record_command(
    user_id,
    quest_day: int,
    command: str,
    scroll_code: str,
    xp: int,
    report_text: str | None = None,
    report_media_url: str | None = None,
    report_media_type: str | None = None,
) -> UserDailyCommand:
    """Record a command completion and return the record."""
    async with session_factory() as session:
        # Get scroll type and daily scroll
        result = await session.execute(
            select(ScrollType).where(ScrollType.code == scroll_code)
        )
        scroll_type = result.scalar_one_or_none()

        daily_scroll = None
        if scroll_type:
            result = await session.execute(
                select(DailyScroll).where(
                    DailyScroll.day_number == quest_day,
                    DailyScroll.scroll_type_id == scroll_type.id,
                )
            )
            daily_scroll = result.scalar_one_or_none()

        record = UserDailyCommand(
            user_id=user_id,
            quest_day=quest_day,
            command=command,
            scroll_type_id=scroll_type.id if scroll_type else None,
            daily_scroll_id=daily_scroll.id if daily_scroll else None,
            xp_awarded=xp,
            completed_at=datetime.now(timezone.utc),
            report_text=report_text,
            report_media_url=report_media_url,
            report_media_type=report_media_type,
        )
        session.add(record)
        await session.commit()
        return record


async def _update_xp(user_id, xp: int) -> None:
    """Add XP to user's total."""
    from app.shared.models.user import User

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.xp = (user.xp or 0) + xp
            await session.commit()


async def _handle_scroll_command(
    message: Message, command: str, scroll_code: str, xp_override: int | None = None
) -> None:
    """Generic handler for scroll commands.

    Args:
        message: Telegram message
        command: The slash command (e.g. /wakeup)
        scroll_code: The scroll type code (e.g. rassvet)
        xp_override: Optional XP override (e.g. /scan gives +0)
    """
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return

    tz_name = user.timezone or settings.TZ
    quest_day = _get_quest_day(user, tz_name, grace_hours=await get_grace_period_hours())

    if quest_day == 0:
        await message.answer("Вы ещё не начали квест. Используйте /start.")
        return

    allowed, reason = await _is_command_allowed(user.id, quest_day, command, scroll_code)
    if not allowed:
        await message.answer(reason)
        return

    # Get scroll type for XP
    async with session_factory() as session:
        result = await session.execute(
            select(ScrollType).where(ScrollType.code == scroll_code)
        )
        scroll_type = result.scalar_one_or_none()
        xp = xp_override if xp_override is not None else (scroll_type.xp_reward if scroll_type else 0)

    # Get scroll content
    daily_scroll = None
    async with session_factory() as session:
        if scroll_type:
            result = await session.execute(
                select(DailyScroll).where(
                    DailyScroll.day_number == quest_day,
                    DailyScroll.scroll_type_id == scroll_type.id,
                )
            )
            daily_scroll = result.scalar_one_or_none()

    # Record the command
    await _record_command(user.id, quest_day, command, scroll_code, xp)

    # Award XP
    await _update_xp(user.id, xp)

    # Send response
    scroll_name = scroll_type.name if scroll_type else scroll_code
    text = f"✅ {scroll_name} — день {quest_day}\n+{xp} XP"

    if daily_scroll and daily_scroll.content:
        text += f"\n\n{daily_scroll.content}"

    await message.answer(text)


# --- Command handlers ---


@daily_router.message(Command("wakeup"))
async def handle_wakeup(message: Message, state: FSMContext) -> None:
    """Handle /wakeup — Рассвет (утренние потягушки)."""
    await _handle_scroll_command(message, "/wakeup", "rassvet")


@daily_router.message(Command("cold"))
async def handle_cold(message: Message, state: FSMContext) -> None:
    """Handle /cold — Огонь (контрастный душ)."""
    await _handle_scroll_command(message, "/cold", "ogne")


@daily_router.message(Command("scan"))
async def handle_scan(message: Message, state: FSMContext) -> None:
    """Handle /scan — Корни (медитация, получить, +0 XP)."""
    await _handle_scroll_command(message, "/scan", "korni", xp_override=0)


@daily_router.message(Command("scanreport"))
async def handle_scanreport(message: Message, state: FSMContext) -> None:
    """Handle /scanreport — Корни (медитация, отчёт +5 XP)."""
    await _handle_scroll_command(message, "/scanreport", "korni")


@daily_router.message(Command("breath"))
async def handle_breath(message: Message, state: FSMContext) -> None:
    """Handle /breath — Ветер (дыхательная практика)."""
    await _handle_scroll_command(message, "/breath", "vetr")


@daily_router.message(Command("micro"))
async def handle_micro(message: Message, state: FSMContext) -> None:
    """Handle /micro — Следы (микро-привычка)."""
    await _handle_scroll_command(message, "/micro", "sledy")


@daily_router.message(Command("focus"))
async def handle_focus(message: Message, state: FSMContext) -> None:
    """Handle /focus — Зря (теория дня)."""
    await _handle_scroll_command(message, "/focus", "zrya")


@daily_router.message(Command("food"))
async def handle_food(message: Message, state: FSMContext) -> None:
    """Handle /food — Питание (рекомендации)."""
    await _handle_scroll_command(message, "/food", "pitaniye")


@daily_router.message(Command("sleep"))
async def handle_sleep(message: Message, state: FSMContext) -> None:
    """Handle /sleep — Интеграция Истока (ночная практика)."""
    await _handle_scroll_command(message, "/sleep", "integratsiya")


@daily_router.message(Command("report"))
async def handle_report(message: Message, state: FSMContext) -> None:
    """Handle /report — Отчёт о дне (+2 XP, optional text/photo)."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return

    tz_name = user.timezone or settings.TZ
    quest_day = _get_quest_day(user, tz_name, grace_hours=await get_grace_period_hours())

    if quest_day == 0:
        await message.answer("Вы ещё не начали квест. Используйте /start.")
        return

    allowed, reason = await _is_command_allowed(user.id, quest_day, "/report", "otchet")
    if not allowed:
        await message.answer(reason)
        return

    # Record with +2 XP
    await _record_command(user.id, quest_day, "/report", "otchet", 2)
    await _update_xp(user.id, 2)

    await message.answer(
        "✅ Отчёт о дне — день {day}\n+2 XP\n\n"
        "Можно добавить текст или фото (необязательно):".format(day=quest_day)
    )
    await state.set_state(ReportState.waiting_for_report)


@daily_router.message(ReportState.waiting_for_report)
async def handle_report_attachment(message: Message, state: FSMContext) -> None:
    """Handle optional text/photo attachment for the daily report."""
    # Update the last report command with the attachment
    async with session_factory() as session:
        result = await session.execute(
            select(UserDailyCommand)
            .where(
                UserDailyCommand.user_id == (await get_user_by_telegram_id(message.from_user.id)).id,
                UserDailyCommand.command == "/report",
            )
            .order_by(UserDailyCommand.completed_at.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record:
            if message.text:
                record.report_text = message.text
            elif message.photo:
                record.report_media_url = message.photo[-1].file_id
                record.report_media_type = "photo"
            elif message.video:
                record.report_media_url = message.video.file_id
                record.report_media_type = "video"
            elif message.document:
                record.report_media_url = message.document.file_id
                record.report_media_type = "document"
            await session.commit()

    await state.clear()
    await message.answer("Отчёт сохранён. Спасибо!")


# --- Status command ---


@daily_router.message(Command("today"))
async def handle_today(message: Message, state: FSMContext) -> None:
    """Show today's scroll status — which commands have been used."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return

    tz_name = user.timezone or settings.TZ
    quest_day = _get_quest_day(user, tz_name, grace_hours=await get_grace_period_hours())

    if quest_day == 0:
        await message.answer("Вы ещё не начали квест.")
        return

    # Get available scrolls for today
    available_codes = get_available_scroll_codes(quest_day)

    # Get completed commands
    async with session_factory() as session:
        result = await session.execute(
            select(UserDailyCommand.command).where(
                UserDailyCommand.user_id == user.id,
                UserDailyCommand.quest_day == quest_day,
            )
        )
        completed = {row[0] for row in result.all()}

    # Get scroll types for display
    async with session_factory() as session:
        result = await session.execute(select(ScrollType))
        all_types = {st.code: st for st in result.scalars().all()}

    day_type = get_day_type(quest_day)
    lines = [f"📅 День {quest_day} из 90\n"]

    if day_type.is_meditation:
        lines.append("🧘 День медитации")
    elif day_type.is_breathing:
        lines.append("🌬️ День дыхания")
    elif day_type.is_awareness:
        lines.append("🔮 День осознания")
    lines.append("")

    for code in available_codes:
        st = all_types.get(code)
        if st is None:
            continue
        cmd = st.command
        done = "✅" if cmd in completed else "⬜"
        time_str = f"{st.hour:02d}:{st.minute:02d}" if st.hour >= 0 else "когда удобно"
        lines.append(f"{done} {st.name} — {cmd} (+{st.xp_reward} XP) — {time_str}")

    # XP summary
    total_xp_today = sum(
        all_types[c].xp_reward for c in available_codes if c in all_types
    )
    earned_xp = sum(
        all_types.get(COMMAND_TO_SCROLL_CODE.get(c, ""), ScrollType(xp_reward=0)).xp_reward
        for c in completed
        if COMMAND_TO_SCROLL_CODE.get(c) in all_types
    )

    lines.append(f"\n💰 XP сегодня: {earned_xp}/{total_xp_today}")

    await message.answer("\n".join(lines))
