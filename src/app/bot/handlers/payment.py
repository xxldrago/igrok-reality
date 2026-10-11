"""Payment handlers — /pay command and payment flow."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.payment import PaymentInit
from app.bot.keyboards.payment import payment_keyboard
from app.bot.services.settings_service import get_payment_amount, get_payment_provider

logger = logging.getLogger(__name__)

payment_router = Router(name="payment")


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

            payment_url = await create_yookassa_payment(payment)
        else:  # platega
            from app.bot.services.payment_service import call_platega_api

            response = await call_platega_api(payment)
            payment_url = response.get("data", {}).get("paymentUrl")
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
async def handle_pay(message: Message) -> None:
    """Handle /pay command — show the payment prompt."""
    from app.bot.services.user_service import get_user

    user = await get_user(message.from_user.id)
    await send_pay_prompt(message, user)


@payment_router.callback_query(PaymentInit.filter())
async def handle_pay_stub(callback: CallbackQuery, callback_data: PaymentInit) -> None:
    """Stub handler: online payments are coming soon."""
    await callback.answer(
        "💳 Онлайн-оплата скоро будет доступна. Следите за новостями!",
        show_alert=True,
    )
