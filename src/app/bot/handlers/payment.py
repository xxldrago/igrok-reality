"""Payment handlers — /pay command and payment flow."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards.payment import payment_keyboard
from app.bot.services.payment_service import call_platega_api, create_payment
from app.bot.services.settings_service import get_payment_amount

payment_router = Router(name="payment")


async def send_pay_prompt(message: Message, user) -> None:
    """Send the payment prompt with a Platega checkout button.

    Shared by /pay, the post-registration flow and the pricing page.
    """
    amount = await get_payment_amount()

    try:
        payment = await create_payment(user_id=user.id, amount=amount, currency="RUB")
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

    await message.answer(
        f"Для продолжения игры необходимо оплатить участие — {amount // 100} ₽.\n"
        "Нажмите кнопку для оплаты:",
        reply_markup=payment_keyboard(amount=amount, payment_url=payment_url),
    )


@payment_router.message(Command("pay"))
async def handle_pay(message: Message) -> None:
    """Handle /pay command — show real payment link or test-pay button."""
    from app.bot.services.user_service import get_user_by_telegram_id

    tg_user = await get_user_by_telegram_id(message.from_user.id)
    if tg_user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return

    await send_pay_prompt(message, tg_user)

