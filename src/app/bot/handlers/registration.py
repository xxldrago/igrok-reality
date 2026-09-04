"""Registration flow handlers — /start command, consent callbacks, archetype quiz."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.deep_linking import create_start_link

from app.bot.callbacks.registration import ArchetypeAnswer, ConsentCallback
from app.bot.keyboards.registration import (
    ARCHETYPE_QUESTIONS,
    archetype_keyboard,
    consent_keyboard,
)
from app.bot.services.archetype import ARCHETYPE_NAMES, calculate_archetype
from app.bot.services.user_service import (
    create_referral,
    create_user,
    generate_referral_code,
    get_user_by_id,
)
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


# ── Archetype quiz handlers ──────────────────────────────────────────────


async def _handle_quiz_answer(
    callback: CallbackQuery,
    state: FSMContext,
    question: int,
    next_state: RegistrationState,
) -> tuple[str, str] | None:
    """Shared logic for processing a quiz answer.

    Stores the answer, edits the message to the next question, and transitions state.
    Returns (archetype, archetype_name) when question == 4, else None.
    """
    await state.update_data(**{f"q{question}_answer": callback.data.split(":")[-1]})

    if question < 4:
        next_q = question + 1
        q_text = ARCHETYPE_QUESTIONS[next_q]["text"]
        await callback.message.edit_text(q_text, reply_markup=archetype_keyboard(next_q))
        await callback.answer()
        return None
    else:
        data = await state.get_data()
        archetype = calculate_archetype(data)
        archetype_name = ARCHETYPE_NAMES[archetype]
        await state.update_data(archetype=archetype)
        await state.set_state(RegistrationState.complete)
        await callback.answer()
        return archetype, archetype_name


@registration_router.callback_query(
    ArchetypeAnswer.filter(F.question == 1),
    RegistrationState.test_q1,
)
async def handle_q1(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Process question 1 answer — store and show question 2."""
    await state.set_state(RegistrationState.test_q2)
    await _handle_quiz_answer(callback, state, question=1, next_state=RegistrationState.test_q2)


@registration_router.callback_query(
    ArchetypeAnswer.filter(F.question == 2),
    RegistrationState.test_q2,
)
async def handle_q2(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Process question 2 answer — store and show question 3."""
    await state.set_state(RegistrationState.test_q3)
    await _handle_quiz_answer(callback, state, question=2, next_state=RegistrationState.test_q3)


@registration_router.callback_query(
    ArchetypeAnswer.filter(F.question == 3),
    RegistrationState.test_q3,
)
async def handle_q3(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Process question 3 answer — store and show question 4."""
    await state.set_state(RegistrationState.test_q4)
    await _handle_quiz_answer(callback, state, question=3, next_state=RegistrationState.test_q4)


@registration_router.callback_query(
    ArchetypeAnswer.filter(F.question == 4),
    RegistrationState.test_q4,
)
async def handle_q4(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Process question 4 answer — create user, handle referral, show profile."""
    result = await _handle_quiz_answer(callback, state, question=4, next_state=RegistrationState.complete)
    if result is None:
        return

    archetype, archetype_name = result
    data = await state.get_data()

    # Create user record in the database
    user_referral_code = generate_referral_code()
    user = await create_user(
        telegram_id=data["telegram_id"],
        first_name=data["first_name"],
        last_name=data.get("last_name"),
        username=data.get("username"),
        archetype=archetype,
        referral_code=user_referral_code,
    )

    # Handle referral if deep_link was present
    referral_msg = ""
    stored_referral_code = data.get("referral_code")
    if stored_referral_code:
        referrer = await create_referral(
            referrer_code=stored_referral_code,
            referee_id=user.id,
        )
        if referrer:
            referrer_user = await get_user_by_id(referrer.referrer_id)
            referrer_name = referrer_user.first_name if referrer_user else "Неизвестный"
            referral_msg = f"\nВы приглашены {referrer_name}!"
        else:
            referral_msg = "\nПриглашение не найдено, но вы можете начать квест!"

    # Build referral link for this user
    referral_link = await create_start_link(callback.bot, user_referral_code)

    # Show profile summary
    profile_text = (
        f"Регистрация завершена!\n"
        f"\n"
        f"Имя: {data['first_name']}\n"
        f"Архетип: {archetype_name}{referral_msg}\n"
        f"\n"
        f"Ваш код для приглашения: {user_referral_code}\n"
        f"\n"
        f"Ссылка для приглашения:\n"
        f"{referral_link}\n"
        f"\n"
        f"Добро пожаловать в квест!"
    )

    await callback.message.edit_text(profile_text)
    await state.clear()
