"""Help handler — /help command and /menu command for role-based navigation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.bot.services.day_type import get_available_scroll_codes
from app.bot.services.moderation_service import submit_report
from app.bot.services.user_service import get_user_by_telegram_id

help_router = Router(name="help")

# Grace period hours — same value used in daily.py
_GRACE_PERIOD_HOURS = 5


def _get_quest_day(user, tz_name: str) -> int:
    """Calculate current quest day for a user based on their timezone."""
    if user.started_at is None:
        return 0
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    started = user.started_at.replace(tzinfo=timezone.utc).astimezone(tz)
    effective_date = now.date()
    if _GRACE_PERIOD_HOURS > 0 and now.hour < _GRACE_PERIOD_HOURS:
        effective_date = now.date() - timedelta(days=1)
    delta = (effective_date - started.date()).days
    return min(delta + 1, 90)


# ── /menu ──────────────────────────────────────────────────────────

# Commands available to all players, with description and optional scroll code
_PLAYER_COMMANDS: list[tuple[str, str, str | None]] = [
    ("/start", "Регистрация / вход", None),
    ("/wakeup", "Свиток Рассвета", "rassvet"),
    ("/cold", "Свиток Огня", "ogne"),
    ("/scan", "Свиток Ветра", "korni"),
    ("/scanreport", "Свиток Следы", "korni"),
    ("/breath", "Свиток Дыхания", "vetr"),
    ("/micro", "Свиток Зрения", "sledy"),
    ("/focus", "Свиток Питания", "zrya"),
    ("/food", "Свиток Интеграции", "pitaniye"),
    ("/sleep", "Свиток Отчёта", "integratsiya"),
    ("/progress", "Мой прогресс", None),
    ("/leaderboard", "Таблица лидеров", None),
    ("/referral", "Реферальная ссылка", None),
    ("/help", "Помощь / связаться с куратором", None),
]

_CURATOR_COMMANDS: list[tuple[str, str]] = [
    ("/moderation", "Модерация"),
]

_LEADER_COMMANDS: list[tuple[str, str]] = [
    ("/broadcast", "Рассылка"),
]

_MASTER_COMMANDS: list[tuple[str, str]] = [
    ("/admin", "Админ-панель"),
]


@help_router.message(Command("menu"))
async def handle_menu(message: Message) -> None:
    """Show available commands based on the user's role and today's quest day."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return

    role = user.role or "player"

    # Determine available scroll codes for today
    available_codes: set[str] = set()
    if user.started_at is not None:
        quest_day = _get_quest_day(user, user.timezone or "Asia/Krasnoyarsk")
        available_codes = set(get_available_scroll_codes(quest_day))

    lines: list[str] = []
    lines.append("*📋 Меню команд*\n")

    # ── Scroll commands ────────────────────────────────────────────
    lines.append("*📜 Свитки:*")
    for cmd, desc, scroll_code in _PLAYER_COMMANDS:
        if scroll_code is not None and available_codes and scroll_code not in available_codes:
            lines.append(f"  {cmd} — {desc} \\(_недоступен сегодня\\)")
        else:
            lines.append(f"  {cmd} — {desc}")

    # ── Role-gated admin commands ──────────────────────────────────
    if role in ("curator", "leader", "master"):
        lines.append("\n*⚙️ Модерация:*")
        for cmd, desc in _CURATOR_COMMANDS:
            lines.append(f"  {cmd} — {desc}")

    if role in ("leader", "master"):
        lines.append("\n*📨 Командование:*")
        for cmd, desc in _LEADER_COMMANDS:
            lines.append(f"  {cmd} — {desc}")

    if role == "master":
        lines.append("\n*🔑 Управление:*")
        for cmd, desc in _MASTER_COMMANDS:
            lines.append(f"  {cmd} — {desc}")

    await message.answer("\n".join(lines), parse_mode="Markdown")


# ── /help ──────────────────────────────────────────────────────────


class HelpState(StatesGroup):
    """FSM state for help report submission."""

    waiting_for_reason = State()


HELP_TEXT = (
    "Если у вас возникли проблемы или вопросы, опишите ситуацию.\n"
    "Ваш запрос будет передан куратору или мастеру.\n\n"
    "Напишите причину обращения:"
)


@help_router.message(Command("help"))
async def handle_help(message: Message, state: FSMContext) -> None:
    """Start help report flow."""
    await message.answer(HELP_TEXT)
    await state.set_state(HelpState.waiting_for_reason)


@help_router.message(HelpState.waiting_for_reason)
async def handle_help_reason(message: Message, state: FSMContext) -> None:
    """Save the help report reason."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        await state.clear()
        return

    reason = message.text or ""
    if len(reason.strip()) < 5:
        await message.answer("Опишите причину подробнее (минимум 5 символов).")
        return

    await submit_report(user.id, reason)

    # Notify the master channel (best-effort, never blocks the user flow).
    try:
        from app.bot.services.master_feed_service import forward_support_request

        await forward_support_request(user, reason)
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "support notify failed for user %s", user.id
        )

    await state.clear()
    await message.answer(
        "Ваш запрос отправлен. Мы свяжемся с вами в ближайшее время."
    )
