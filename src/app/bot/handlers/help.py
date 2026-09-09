"""Help handler — /help command for player support requests."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.bot.services.moderation_service import submit_report
from app.bot.services.user_service import get_user_by_telegram_id

help_router = Router(name="help")


class HelpState(StatesGroup):
    """FSM state for help report submission."""

    waiting_for_reason = State()


HELP_TEXT = (
    "Если у вас возникли проблемы или вопросы, опишите ситуацию.\n"
    "Ваш запрос будет передан куратору или мастеру.\n"
    "\n"
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
    await state.clear()
    await message.answer(
        "Ваш запрос отправлен. Мы свяжемся с вами в ближайшее время."
    )
