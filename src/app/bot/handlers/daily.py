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
from app.bot.keyboards.scroll import today_keyboard
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
from app.bot.services.progress_service import create_completion

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
    grace_hours defaults to GRACE_PERIOD_HOURS (callers pass the
    actual value from settings).
    """
    tz = ZoneInfo(tz_name)
    now = now or datetime.now(timezone.utc)
    local_time = now.astimezone(tz)
    day_start = local_time.replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_start = (local_time - day_start).days
    grace = timedelta(hours=grace_hours or GRACE_PERIOD_HOURS)
    if local_time - day_start < grace:
        days_since_start -= 1
    return max(0, days_since_start + 1)


async def _is_command_allowed(
    user_id: int, quest_day: int, command: str, scroll_code: str, slot: str = ""
) -> tuple[bool, str]:
    """Check if the user can use this command today."""
    from app.shared.models.user import User
    from app.shared.models.user_daily_command import UserDailyCommand

    async with session_factory() as session:
        # Check if user has paid
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.paid_at is None:
            return False, "Сначала оплатите участие: /pay"

        # Check day range
        if quest_day > 90:
            return False, "Квест завершён."

        # Check day type restrictions
        day_type = get_day_type(quest_day)
        scroll_type = None
        if scroll_code:
            result = await session.execute(
                select(ScrollType).where(ScrollType.code == scroll_code)
            )
            scroll_type = result.scalar_one_or_none()

        # Awareness days: only zrya, otchet allowed
        if day_type.is_awareness and scroll_code not in ("zrya", "otchet"):
            return False, "В день осознанности доступны только Зря и Отчёт."

        # Breathing day restrictions
        BREATHING_CODES = ("vetr", "vetr_day", "vetr_evening")
        if day_type.is_breathing and scroll_code not in (*BREATHING_CODES, "zrya", "otchet"):
            return False, "В день дыхания доступны только Ветер, Зря и Отчёт."

        # Check breathing day extras
        if scroll_type and scroll_type.is_breathing_day_only and not day_type.is_breathing:
            return False, "Этот свиток доступен только в дни дыхания (7, 14, 21, 28...)."

        # Check if command already used today (slot-aware for 3x /breath)
        result = await session.execute(
            select(UserDailyCommand).where(
                UserDailyCommand.user_id == user_id,
                UserDailyCommand.quest_day == quest_day,
                UserDailyCommand.command == command,
                UserDailyCommand.slot == slot,
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
    slot: str = "",
) -> UserDailyCommand:
    """Record a command completion and return the record."""
    async with session_factory() as session:
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
            slot=slot,
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
    message: Message,
    command: str,
    scroll_code: str,
    xp_override: int | None = None,
    slot: str = "",
    tg_id: int | None = None,
    reply=None,
) -> None:
    """Generic handler for scroll commands.

    Args:
        message: Telegram message (reply target for command flow)
        command: The slash command (e.g. /wakeup)
        scroll_code: The scroll type code (e.g. rassvet)
        xp_override: Optional XP override (e.g. /scan gives +0)
        slot: Breathing-day slot (morning/day/evening) for repeated /breath
        tg_id: Telegram user id override (button flow: callback.from_user.id)
        reply: Reply coroutine override (button flow: callback.message.answer)
    """
    tid = tg_id if tg_id is not None else message.from_user.id
    send = reply or message.answer
    user = await get_user_by_telegram_id(tid)
    if user is None:
        await send("Сначала зарегистрируйтесь через /start.")
        return

    if user.paid_at is None:
        await send("Сначала оплатите участие: /pay")
        return

    tz_name = user.timezone or settings.TZ
    quest_day = _get_quest_day(user, tz_name, grace_hours=await get_grace_period_hours())

    if quest_day == 0:
        await send("Вы ещё не начали квест. Используйте /start.")
        return

    allowed, reason = await _is_command_allowed(
        user.id, quest_day, command, scroll_code, slot=slot
    )
    if not allowed:
        await send(reason)
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
    await _record_command(user.id, quest_day, command, scroll_code, xp, slot=slot)

    # Award XP
    await _update_xp(user.id, xp)

    # Remove the passed scroll's delivery message from the chat (best-effort).
    try:
        from app.bot.services.delivery_service import delete_delivery_message

        await delete_delivery_message(
            message.bot, message.from_user.id, user.id, quest_day, scroll_code
        )
    except Exception:
        import logging

        logging.getLogger(__name__).warning(
            "delivery cleanup failed for user %s", user.id
        )

    # Send response
    scroll_name = scroll_type.name if scroll_type else scroll_code
    text = f"✅ {scroll_name} — день {quest_day}\n+{xp} XP"

    if daily_scroll and daily_scroll.content:
        text += f"\n\n{daily_scroll.content}"

    await send(text)


# --- Command handlers ---

@daily_router.message(Command("wakeup"))
async def handle_wakeup(message: Message, state: FSMContext) -> None:
    """Handle /wakeup — Рассвет (утренние потягушки)."""
    await _handle_scroll_command(message, "/wakeup", "rassvet")


@daily_router.message(Command("cold"))
async def handle_cold(message: Message, state: FSMContext) -> None:
    """Handle /cold — Огонь (контрастный душ)."""
    await _handle_scroll_command(message, "/cold", "ogon")


@daily_router.message(Command("scan"))
async def handle_scan(message: Message, state: FSMContext) -> None:
    """Handle /scan — Следы (проверка осанки, +0 XP)."""
    await _handle_scroll_command(message, "/scan", "sledy", xp_override=0)


@daily_router.message(Command("scanreport"))
async def handle_scanreport(message: Message, state: FSMContext) -> None:
    """Handle /scanreport — Корни (медитация, отчёт +5 XP)."""
    await _handle_scroll_command(message, "/scanreport", "korni")


@daily_router.message(Command("breath"))
async def handle_breath(
    message: Message,
    state: FSMContext,
    slot: str = "",
) -> None:
    """Handle /breath — Ветер (дыхательное упражнение, +5 XP)."""
    await _handle_scroll_command(message, "/breath", "vetr", slot=slot)


@daily_router.message(Command("micro"))
async def handle_micro(message: Message, state: FSMContext) -> None:
    """Handle /micro — Микродвижения."""
    await _handle_scroll_command(message, "/micro", "mikro")


@daily_router.message(Command("focus"))
async def handle_focus(message: Message, state: FSMContext) -> None:
    """Handle /focus — Втреб (осознанность в теле)."""
    await _handle_scroll_command(message, "/focus", "vtreb")


@daily_router.message(Command("food"))
async def handle_food(message: Message, state: FSMContext) -> None:
    """Handle /food — Питание."""
    await _handle_scroll_command(message, "/food", "pitaniye")


@daily_router.message(Command("sleep"))
async def handle_sleep(message: Message, state: FSMContext) -> None:
    """Handle /sleep — Интеграция."""
    await _handle_scroll_command(message, "/sleep", "integratsiya")


@daily_router.message(Command("zrya"))
async def handle_zrya(message: Message, state: FSMContext) -> None:
    """Handle /zrya — Зря (наблюдение за мыслями)."""
    await _handle_scroll_command(message, "/zrya", "zrya", xp_override=0)


@daily_router.message(Command("report"))
async def handle_report(
    message: Message,
    state: FSMContext,
    tg_id: int | None = None,
    reply=None,
) -> None:
    """Handle /report — Отчёт о дне (+2 XP, optional text/photo).

    DOES NOT create the completion record yet. That happens only after
    the user sends a report attachment (text/photo/video) and clicks
    the completion button. This prevents bot commands from being saved
    as report completions.
    """
    tid = tg_id if tg_id is not None else message.from_user.id
    send = reply or message.answer
    user = await get_user_by_telegram_id(tid)
    if user is None:
        await send("Сначала зарегистрируйтесь через /start.")
        return

    if user.paid_at is None:
        await send("Сначала оплатите участие: /pay")
        return

    tz_name = user.timezone or settings.TZ
    quest_day = _get_quest_day(user, tz_name, grace_hours=await get_grace_period_hours())

    if quest_day == 0:
        await send("Вы ещё не начали квест. Используйте /start.")
        return

    allowed, reason = await _is_command_allowed(user.id, quest_day, "/report", "otchet")
    if not allowed:
        await send(reason)
        return

    # Awareness days: report is the weekly summary, +5 XP (spec 3.4); else +2
    report_xp = 5 if get_day_type(quest_day).is_awareness else 2

    # Store report metadata in FSM state
    await state.set_data({
        "report_xp": report_xp,
        "quest_day": quest_day,
        "report_command": "/report",
        "report_scroll_code": "otchet",
    })

    await send(
        f"✅ Отчёт о дне — день {quest_day}\n+{report_xp} XP\n\n"
        "Можно добавить текст или фото (необязательно):\n"
        "1. Пришлите текст/фото/видео/документ\n"
        "2. Нажмите «✅ Свиток пройден» внизу"
    )
    await state.set_state(ReportState.waiting_for_report)


@daily_router.message(ReportState.waiting_for_report)
async def handle_report_attachment(message: Message, state: FSMContext) -> None:
    """Handle optional text/photo attachment for the daily report.

    Also handles the "Свиток пройден" button click.
    """
    # Skip bot commands (/help, /today, /start, etc.)
    if message.text and message.text.startswith('/'):
        return

    data = await state.get_data()
    report_xp = data.get("report_xp", 2)
    quest_day = data.get("quest_day", 0)

    # Process attachment
    report_text = None
    report_media_url = None
    report_media_type = None

    if message.text:
        report_text = message.text
    elif message.photo:
        report_media_url = message.photo[-1].file_id
        report_media_type = "photo"
    elif message.video:
        report_media_url = message.video.file_id
        report_media_type = "video"
    elif message.document:
        report_media_url = message.document.file_id
        report_media_type = "document"

    # Record the completion with the report
    user = await get_user_by_telegram_id(message.from_user.id)
    if user:
        await _record_command(
            user.id,
            quest_day,
            "/report",
            "otchet",
            report_xp,
            report_text=report_text,
            report_media_url=report_media_url,
            report_media_type=report_media_type,
        )

        await _update_xp(user.id, report_xp)
        await state.clear()
        await message.answer("Отчёт сохранён. Спасибо!")


# --- Status command ---


@daily_router.message(Command("today"))
async def handle_today(
    message: Message,
    state: FSMContext,
    tg_id: int | None = None,
    reply=None,
) -> None:
    """Show today's scroll status — which commands have been used."""
    tid = tg_id if tg_id is not None else message.from_user.id
    send = reply or message.answer
    user = await get_user_by_telegram_id(tid)
    if user is None:
        await send("Сначала зарегистрируйтесь через /start.")
        return

    if user.paid_at is None:
        await send("Сначала оплатите участие: /pay")
        return

    tz_name = user.timezone or settings.TZ
    quest_day = _get_quest_day(user, tz_name, grace_hours=await get_grace_period_hours())

    if quest_day == 0:
        await send("Вы ещё не начали квест. Используйте /start.")
        return

    # Get today's scrolls
    async with session_factory() as session:
        result = await session.execute(
            select(ScrollType).where(ScrollType.code.in_(COMMAND_TO_SCROLL_CODE.values()))
        )
        scroll_types = result.scalars().all()

        # Get completed scrolls for this user today
        result = await session.execute(
            select(UserDailyCommand).where(
                UserDailyCommand.user_id == user.id,
                UserDailyCommand.quest_day == quest_day,
            )
        )
        completed = result.scalars().all()

    completed_codes = {c.scroll_type.code for c in completed if c.scroll_type}

    text = f"📊 Статус сегодня (день {quest_day}):\n\n"
    for st in sorted(scroll_types, key=lambda x: COMMAND_TO_SCROLL_CODE.get(x.code, "")):
        done = st.code in completed_codes
        icon = "✅" if done else "❌"
        text += f"{icon} {st.name}\n"

    await send(text + "\nИспользуйте команды для прохождения свитков.")


@daily_router.message(Command("streak"))
async def handle_streak(
    message: Message,
    state: FSMContext,
    tg_id: int | None = None,
    reply=None,
) -> None:
    """Show current streak."""
    tid = tg_id if tg_id is not None else message.from_user.id
    send = reply or message.answer
    user = await get_user_by_telegram_id(tid)
    if user is None:
        await send("Сначала зарегистрируйтесь через /start.")
        return

    streak = user.streak or 0
    await send(f"🔥 Ваша серия: {streak} дней")


@daily_router.message(Command("leaderboard"))
async def handle_leaderboard(
    message: Message,
    state: FSMContext,
    tg_id: int | None = None,
    reply=None,
) -> None:
    """Show top users by XP."""
    tid = tg_id if tg_id is not None else message.from_user.id
    send = reply or message.answer
    user = await get_user_by_telegram_id(tid)
    if user is None:
        await send("Сначала зарегистрируйтесь через /start.")
        return

    async with session_factory() as session:
        result = await session.execute(
            select(User)
            .where(User.paid_at.isnot(None))
            .order_by(User.xp.desc())
            .limit(10)
        )
        top_users = result.scalars().all()

    text = "🏆 Топ участников:\n\n"
    for i, u in enumerate(top_users, 1):
        text += f"{i}. {u.full_name or u.telegram_username} — {u.xp or 0} XP\n"

    await send(text)


@daily_router.message(Command("help"))
async def handle_help(message: Message, state: FSMContext) -> None:
    """Show help message."""
    text = (
        "📚 Помощь по квесту «Игрок.Реальность»:\n\n"
        "Команды:\n"
        "/start — Начать квест\n"
        "/today — Статус сегодня\n"
        "/streak — Текущая серия\n"
        "/leaderboard — Топ участников\n"
        "/pay — Оплата\n"
        "/report — Отчёт о дне\n\n"
        "Свитки (для прохождения):\n"
        "/wakeup — Рассвет\n"
        "/cold — Огонь\n"
        "/scan — Следы\n"
        "/breath — Ветер\n"
        "/micro — Микродвижения\n"
        "/focus — Втреб\n"
        "/food — Питание\n"
        "/sleep — Интеграция\n"
        "/zrya — Зря\n"
        "/scanreport — Корни"
    )
    await message.answer(text)
