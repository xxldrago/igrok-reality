"""Payment handlers — /pay command and payment flow."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.payment import PaymentInit
from app.bot.keyboards.payment import payment_keyboard
from app.bot.services.settings_service import get_payment_amount

payment_router = Router(name="payment")


async def send_pay_prompt(message: Message, user) -> None:
    """Send the payment prompt with a stub pay button.

    Real payments are not connected yet, so no provider calls and no
    payment records — the button answers with a stub notice.
    Shared by /pay, the post-registration flow and the pricing page.
    """
    amount = await get_payment_amount()

    await message.answer(
        f"Для продолжения игры необходимо оплатить участие — {amount // 100} ₽ в месяц.\n"
        "Нажмите кнопку для оплаты:",
        reply_markup=payment_keyboard(amount=amount),
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
