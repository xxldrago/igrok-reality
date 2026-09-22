"""Registration flow handlers — /start command, consent callbacks, archetype quiz."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.deep_linking import create_start_link

from app.bot.callbacks.registration import ArchetypeAnswer, ConsentCallback
from app.bot.keyboards.registration import (
    archetype_keyboard,
    consent_keyboard,
)
from app.bot.services.archetype import (
    ARCHETYPE_NAMES,
    DEFAULT_RESULTS,
    calculate_archetype,
    load_quiz_config,
)
from app.bot.services.settings_service import get_consent_text, get_welcome_message
from app.bot.services.user_service import (
    create_referral,
    create_user,
    generate_referral_code,
    get_user_by_id,
    get_user_by_telegram_id,
)
from app.bot.states.registration import RegistrationState

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

registration_router = Router(name="registration")

TELEGRAM_MESSAGE_LIMIT = 4000


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split long text into Telegram-sized chunks by paragraphs."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in text.split("\n\n"):
        if len(para) > limit:
            # Single oversized paragraph — hard split
            if current:
                chunks.append("\n\n".join(current))
                current, current_len = [], 0
            for i in range(0, len(para), limit):
                chunks.append(para[i : i + limit])
            continue
        piece_len = len(para) if not current else len(para) + 2
        if current_len + piece_len > limit and current:
            chunks.append("\n\n".join(current))
            current, current_len = [para], len(para)
        else:
            current.append(para)
            current_len += piece_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks

# Legacy constant (kept for backward compatibility) — the live text comes
# from settings (consent_text, editable via admin panel).
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
    saves it for later binding. If the user is already registered, skips the
    quiz and shows the role-aware command menu instead of re-registering.
    """
    # If user is already registered, don't re-run registration
    existing = await get_user_by_telegram_id(message.from_user.id)
    if existing is not None:
            await state.clear()
            from app.bot.handlers.help import handle_menu
            await handle_menu(message)
            return

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

    welcome_text = await get_welcome_message()
    consent_text = await get_consent_text()
    for chunk in split_message(welcome_text):
        await message.answer(chunk)
    await message.answer(consent_text, reply_markup=consent_keyboard())


@registration_router.callback_query(ConsentCallback.filter(F.action == "agree"), RegistrationState.consent)
async def handle_consent_agree(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Process consent agreement — store consent flag and move to quiz."""
    await state.update_data(consent=True)
    await state.set_state(RegistrationState.test_q1)
    
    # Load quiz config and show intro + question 1
    quiz = await load_quiz_config()
    q1 = quiz.questions[0]
    q1_text = f"{quiz.intro}\n\n{_format_quiz_question(q1.text, q1.options)}"
    await callback.message.edit_text(q1_text, reply_markup=archetype_keyboard(1, q1.options))
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


def _format_quiz_question(question_text: str, options: list[dict[str, str]]) -> str:
    """Append full option texts below the question for user reference.

    Since button labels may be truncated to 64 bytes, the question message
    lists every option in full so the user always sees the complete text.
    """
    lines = [question_text, ""]
    for opt in options:
        lines.append(f"• {opt['text']}")
    return "\n".join(lines)


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
    answer = callback.data.split(":")[-1]
    await state.update_data(**{f"q{question}_answer": answer})

    if question < 4:
        await state.set_state(next_state)
        quiz = await load_quiz_config()
        q_data = quiz.questions[question]  # 0-indexed
        q_text = _format_quiz_question(q_data.text, q_data.options)
        await callback.message.edit_text(q_text, reply_markup=archetype_keyboard(question + 1, q_data.options))
        await callback.answer()
        return None
    else:
        data = await state.get_data()
        archetype = await calculate_archetype(data)
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

    try:
        archetype, archetype_name = result
        data = await state.get_data()

        # Load the personalized archetype result text (finalization of the test)
        quiz = await load_quiz_config()
        result_text = quiz.results.get(archetype) or DEFAULT_RESULTS.get(archetype, "")

        # Persist entrance test answers (visible in admin user card)
        import json

        quiz_answers = json.dumps(
            [data.get(f"q{i}_answer") for i in range(1, 5)], ensure_ascii=False
        )

        # Get-or-create: re-running /start must not crash on existing telegram_id.
        # Quest clock stays unset — it starts on stream launch, not registration.
        user = await get_user_by_telegram_id(data["telegram_id"])
        if user is None:
            user_referral_code = generate_referral_code()
            user = await create_user(
                telegram_id=data["telegram_id"],
                first_name=data["first_name"],
                last_name=data.get("last_name"),
                username=data.get("username"),
                archetype=archetype,
                referral_code=user_referral_code,
                started_at=None,
                quiz_answers=quiz_answers,
            )
        else:
            logger.info("handle_q4: re-registration for telegram_id=%s", data["telegram_id"])
            user_referral_code = user.referral_code
            # Retook the quiz — store the new archetype + answers
            from sqlalchemy import select

            from app.shared.database import session_factory
            from app.shared.models.user import User

            async with session_factory() as session:
                result = await session.execute(select(User).where(User.id == user.id))
                db_user = result.scalar_one_or_none()
                if db_user is not None:
                    db_user.archetype = archetype
                    db_user.quiz_answers = quiz_answers
                    await session.commit()

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
            f"Следующий шаг — оплата участия: /pay\n"
            f"\n"
            f"Добро пожаловать в квест!"
        )

        # Finalization: first show the personalized archetype result,
        # then the profile summary as a follow-up message.
        if result_text:
            await callback.message.edit_text(result_text)
            await callback.message.answer(profile_text)
        else:
            await callback.message.edit_text(profile_text)

        # Payment prompt right away: test button or Platega URL (no /pay typing needed)
        from app.bot.handlers.payment import send_pay_prompt

        await send_pay_prompt(callback.message, user)
    except Exception:
        logger.exception(
            "handle_q4 failed for telegram_id=%s",
            (await state.get_data()).get("telegram_id"),
        )
        await callback.message.answer(
            "Что-то пошло не так при завершении регистрации. "
            "Попробуйте ещё раз: /start"
        )
    finally:
        await state.clear()
