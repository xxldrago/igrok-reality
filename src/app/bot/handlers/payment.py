"""Payment handlers — /pay command and payment flow."""

from __future__ import annotations

from uuid import UUID

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards.payment import payment_keyboard
from app.bot.services.payment_service import call_platega_api, create_payment
from app.bot.services.settings_service import get_payment_amount

payment_router = Router(name="payment")


@payment_router.message(Command("pay"))
async def handle_pay(message: Message) -> None:
    """Handle /pay command — create payment and return payment link."""
    user_id = UUID(message.from_user.id)

    # Price is editable via admin panel (settings → payment_amount, kopecks)
    amount = await get_payment_amount()

    try:
        payment = await create_payment(user_id=user_id, amount=amount, currency="RUB")
    except Exception:
        await message.answer("Ошибка при создании платежа. Попробуйте позже.")
        return

    try:
        response = await call_platega_api(payment)
    except Exception:
        await message.answer("Ошибка при создании платежа. Попробуйте позже.")
        return

    payment_url = response.get("data", {}).get("paymentUrl")
    if not payment_url:
        await message.answer("Ошибка при создании платежа. Попробуйте позже.")
        return

    keyboard = payment_keyboard(amount=amount)
    await message.answer(
        "Нажмите кнопку для оплаты:",
        reply_markup=keyboard,
    )
