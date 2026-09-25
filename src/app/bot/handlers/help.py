"""Help handler — /help command and /menu command for role-based navigation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.runner import InfoPage

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

@help_router.message(Command("menu"))
async def handle_menu(message: Message) -> None:
    """Show inline-button menu based on the user's role and today's quest day."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from app.bot.callbacks.runner import RunCommand

    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return

    # Determine available scroll codes for today
    available_codes: set[str] = set()
    quest_day = 0
    if user.started_at is not None:
        quest_day = _get_quest_day(user, user.timezone or "Asia/Krasnoyarsk")
        available_codes = set(get_available_scroll_codes(quest_day))

    # Scroll button labels come from scroll types
    names: dict[str, str] = {}
    if available_codes:
        from sqlalchemy import select

        from app.shared.database import session_factory
        from app.shared.models.scroll_type import ScrollType

        async with session_factory() as session:
            result = await session.execute(select(ScrollType))
            names = {st.code: st.name for st in result.scalars().all()}

    builder = InlineKeyboardBuilder()
    for cmd, _desc, scroll_code in _PLAYER_COMMANDS:
        if cmd == "/start" or scroll_code is None:
            continue
        # Зря и Отчёт живут только в /today
        if scroll_code == "zrya":
            continue
        if available_codes and scroll_code not in available_codes:
            continue
        label = names.get(scroll_code, scroll_code)
        builder.button(text=label, callback_data=RunCommand(command=cmd).pack())
    builder.adjust(2)

    # ── Quick actions ──────────────────────────────────────────────
    for label, cmd in (
        ("Свитки сегодня", "/today"),
        ("⚡ Прогресс", "/progress"),
        ("🏆 Топ", "/leaderboard"),
        ("💳 Оплата", "/pay"),
        ("🔗 Рефералка", "/referral"),
        ("❓ Помощь", "/help"),
    ):
        builder.button(text=label, callback_data=RunCommand(command=cmd).pack())
    builder.adjust(2)

    # ── Info pages ─────────────────────────────────────────────────
    for label, page in (
        ("Политика конфиденциальности", "privacy"),
        ("Пользовательское соглашение", "agreement"),
        ("📞 Поддержка", "contacts"),
        ("💰 Тарифы", "pricing"),
    ):
        builder.button(text=label, callback_data=InfoPage(page=page).pack())
    builder.adjust(2)

    lines = [f"📋 Меню — день {quest_day} из 90\n", "Выбирайте кнопками ниже:", "/pay"]

    await message.answer("\n".join(lines), reply_markup=builder.as_markup())


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
async def handle_help(
    message: Message, state: FSMContext, reply=None
) -> None:
    """Start help report flow."""
    send = reply or message.answer
    await send(HELP_TEXT)
    await state.set_state(HelpState.waiting_for_reason)


_INFO_GETTERS = {
    "privacy": "get_privacy_policy",
    "agreement": "get_user_agreement",
    "contacts": "get_support_contacts",
    "pricing": "get_pricing_text",
}


@help_router.callback_query(InfoPage.filter())
async def handle_info_page(callback: CallbackQuery, callback_data: InfoPage) -> None:
    """Show an info page (/menu buttons). Long texts are split into chunks."""
    from app.bot.handlers.registration import split_message
    from app.bot.services import settings_service

    await callback.answer()
    getter_name = _INFO_GETTERS.get(callback_data.page)
    if getter_name is None:
        await callback.message.answer("Раздел не найден. Откройте /menu.")
        return
    text = await getattr(settings_service, getter_name)()
    for chunk in split_message(text):
        await callback.message.answer(chunk)


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
