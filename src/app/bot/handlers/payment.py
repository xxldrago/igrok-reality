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

    Real payments are not connected yet, so no Platega calls and no
    payment records — the button answers with a stub notice.
    Shared by /pay, the post-registration flow and the pricing page.
    """
    amount = await get_payment_amount()

    await message.answer(
        f"Для продолжения игры необходимо оплатить участие — {amount // 100} ₽.\n"
        "Нажмите кнопку для оплаты:",
        reply_markup=payment_keyboard(amount=amount),
    )


@payment_router.callback_query(PaymentInit.filter())
async def handle_pay_stub(callback_query: CallbackQuery, callback_data: PaymentInit) -> None:
    """Stub handler: online payments are coming soon."""
    await callback_query.answer(
        "💳 Онлайн-оплата скоро будет доступна. Следите за новостями!",
        show_alert=True,
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

