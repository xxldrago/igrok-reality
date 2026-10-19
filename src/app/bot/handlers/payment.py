"""Payment handlers — /pay command and payment flow."""

from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.callbacks.payment import PaymentInit
from app.bot.keyboards.payment import payment_keyboard
from app.bot.services.settings_service import get_payment_amount, get_payment_provider
from app.shared.database import session_factory
from app.shared.models.user import User

logger = logging.getLogger(__name__)

payment_router = Router(name="payment")


class PaymentState(StatesGroup):
    """FSM state for collecting the receipt email (YooKassa fiscalization)."""

    waiting_for_email = State()


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def ensure_email_for_provider(message: Message, user, state: FSMContext) -> bool:
    """Gate YooKassa payments on having the user's email for the receipt.

    Returns True when payment may proceed; otherwise asks for the email,
    sets the FSM state and returns False.
    """
    provider = await get_payment_provider()
    if provider != "yookassa":
        return True
    if getattr(user, "email", None):
        return True
    await state.set_state(PaymentState.waiting_for_email)
    await message.answer(
        "📧 Для чека об оплате укажите ваш email:"
    )
    return False


@payment_router.message(PaymentState.waiting_for_email, ~F.text.startswith("/"))
async def handle_email_input(message: Message, state: FSMContext) -> None:
    """Validate and save the receipt email, then continue to payment."""
    email = (message.text or "").strip().lower()
    if not EMAIL_RE.match(email):
        await message.answer("Похоже, это не email. Попробуйте ещё раз:")
        return

    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        db_user = result.scalar_one_or_none()
        if db_user is None:
            await state.clear()
            await message.answer("Сначала зарегистрируйтесь через /start.")
            return
        db_user.email = email
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Email сохранён: {email}")
    await send_pay_prompt(message, db_user)


async def send_pay_prompt(message: Message, user) -> None:
    """Send the payment prompt using the active provider.

    Provider is chosen via the payment_provider setting (stub | platega |
    yookassa). stub shows a placeholder button with no provider calls.
    Shared by /pay, the post-registration flow and the pricing page.
    """
    provider = await get_payment_provider()
    amount = await get_payment_amount()

    if provider == "stub":
        await message.answer(
            f"Для продолжения игры необходимо оплатить участие — {amount // 100} ₽ в месяц.\n"
            "Нажмите кнопку для оплаты:",
            reply_markup=payment_keyboard(amount=amount),
        )
        return

    try:
        from app.bot.services.payment_service import create_payment

        payment = await create_payment(user_id=user.id, amount=amount, currency="RUB")
        if provider == "yookassa":
            from app.bot.services.payment_service import create_yookassa_payment

            payment_url = await create_yookassa_payment(
                payment, email=getattr(user, "email", None)
            )
        else:  # platega
            from app.bot.services.payment_service import call_platega_api

            response = await call_platega_api(payment)
            payment_url = response.get("url")
    except Exception:
        logger.exception("Payment creation failed (provider=%s)", provider)
        await message.answer("Ошибка при создании платежа. Попробуйте позже.")
        return

    if not payment_url:
        await message.answer("Ошибка при создании платежа. Попробуйте позже.")
        return

    await message.answer(
        f"Для продолжения игры необходимо оплатить участие — {amount // 100} ₽ в месяц.\n"
        "Нажмите кнопку для оплаты:",
        reply_markup=payment_keyboard(amount=amount, payment_url=payment_url),
    )


@payment_router.message(Command("pay"))
async def handle_pay(message: Message, state: FSMContext) -> None:
    """Handle /pay command — show the payment prompt."""
    from app.bot.services.user_service import get_user_by_telegram_id

    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return
    if not await ensure_email_for_provider(message, user, state):
        return
    await send_pay_prompt(message, user)


@payment_router.callback_query(PaymentInit.filter())
async def handle_pay_stub(callback: CallbackQuery, callback_data: PaymentInit) -> None:
    """Stub handler: online payments are coming soon."""
    await callback.answer(
        "💳 Онлайн-оплата скоро будет доступна. Следите за новостями!",
        show_alert=True,
    )
