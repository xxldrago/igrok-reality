"""Registration flow handlers — /start command, consent callbacks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.registration import ConsentCallback
from app.bot.keyboards.registration import consent_keyboard
from app.bot.states.registration import RegistrationState

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext

registration_router = Router(name="registration")

CONSENT_TEXT = (
    "Добро пожаловать в Игрок.Реальность!\n"
    "\n"
    "Для участия в квесте нам нужны ваши данные:\n"
    "• Имя и фамилия из Telegram\n"
    "• Username (если есть)\n"
    "\n"
    "Мы обрабатываем ваши данные для:\n"
    "• Управления вашим прогрессом в квесте\n"
    "• Связи с вами по вопросам квеста\n"
    "• Отправки ежедневных заданий\n"
    "\n"
    "Нажимая «Я согласен», вы подтверждаете обработку персональных данных."
)


@registration_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    """Handle /start command — initialise registration flow.

    Stores Telegram profile data and, if a deep-link referral code is present,
    saves it for later binding.
    """
    # TODO: check if user already exists via get_user_by_telegram_id()
    #       For now, always treat as new user (Plan 02-01 scope).

    # Parse referral deep-link
    referral_code = None
    if message.text and " " in message.text:
        referral_code = message.text.split(maxsplit=1)[1]

    # Persist Telegram profile + referral to FSM context
    await state.update_data(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
        referral_code=referral_code,
    )

    await state.set_state(RegistrationState.consent)
    await message.answer(CONSENT_TEXT, reply_markup=consent_keyboard())


@registration_router.callback_query(ConsentCallback.filter(F.action == "agree"), RegistrationState.consent)
async def handle_consent_agree(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Process consent agreement — store consent flag and move to quiz."""
    await state.update_data(consent=True)
    await state.set_state(RegistrationState.test_q1)
    await callback.message.edit_text("Отлично! Давайте определим ваш архетип.")
    await callback.answer("Согласие записано")


@registration_router.callback_query(ConsentCallback.filter(F.action == "decline"), RegistrationState.consent)
async def handle_consent_decline(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Process consent decline — clear FSM and show retry hint."""
    await state.clear()
    await callback.message.edit_text("Вы можете начать заново командой /start")
    await callback.answer()
