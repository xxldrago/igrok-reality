"""Payment handlers — /pay command and payment flow."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.payment import PaymentInit
from app.bot.keyboards.payment import payment_keyboard
from app.bot.services.settings_service import get_payment_amount, get_payments_enabled

payment_router = Router(name="payment")


async def send_pay_prompt(message: Message, user) -> None:
    """Send the payment prompt with a stub pay button.

    Real payments are not connected yet, so no Platega calls and no
    payment records — the button answers with a stub notice.
    Shared by /pay, the post-registration flow and the pricing page.
    """
    payments_enabled = await get_payments_enabled()
    amount = await get_payment_amount()

    if not payments_enabled:
        await message.answer(
            f"👛 Приём платежей выключен. Нажмите кнопку для тестовой оплаты {amount // 100}₽/мес — "
            "доступ будет выдан мгновенно.",
            reply_markup=payment_keyboard(amount=amount),
        )
        return

    await message.answer(
        f"Для продолжения игры необходимо оплатить участие — {amount // 100} ₽/мес.\n"
        "Нажмите кнопку для оплаты:",
        reply_markup=payment_keyboard(amount=amount),
    )


@payment_router.message(Command("pay"))
async def handle_pay(message: Message) -> None:
    """Handle /pay command — show pricing info."""
    from app.bot.services.user_service import get_user
    from app.bot.services.settings_service import get_payments_enabled

    user = await get_user(message.from_user.id)
    payments_enabled = await get_payments_enabled()

    if not payments_enabled:
        await send_pay_prompt(message, user)
        return
    else:
        amount = await get_payment_amount()
        try:
            from app.bot.services.payment_service import call_platega_api, create_payment
            payment = await create_payment(user_id=user.id, amount=amount, currency="RUB")
            response = await call_platega_api(payment)
            payment_url = response.get("data", {}).get("paymentUrl")
            if not payment_url:
                await message.answer("Ошибка при создании платежа. Попробуйте позже.")
                return
        except Exception:
            await message.answer("Ошибка при создании платежа. Попробуйте позже.")
            return

        from app.bot.keyboards.payment import payment_keyboard
        await message.answer(
            f"Для продолжения игры необходимо оплатить участие — {amount // 100} ₽/мес.\n"
            "Нажмите кнопку для оплаты:",
            reply_markup=payment_keyboard(amount=amount, payment_url=payment_url),
        )


@payment_router.callback_query(PaymentInit.filter())
async def handle_payment_init(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Платёж инициализирован. Ожидание подтверждения...")
    await callback.answer()


@payment_router.callback_query(PaymentInit.filter())
async def handle_payment_success(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Оплата прошла успешно!")
    await callback.answer()
