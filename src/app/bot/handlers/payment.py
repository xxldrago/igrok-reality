"""Payment handlers — /pay command and payment flow."""

from __future__ import annotations

import logging
from uuid import UUID

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.bot.keyboards.payment import payment_keyboard, staging_payment_keyboard
from app.bot.callbacks.payment import TestPayment
from app.bot.services.payment_service import call_platega_api, create_payment
from app.bot.services.settings_service import get_payment_amount, get_payments_enabled
from app.shared.database import session_factory
from app.shared.models.user import User

logger = logging.getLogger(__name__)

payment_router = Router(name="payment")


async def send_pay_prompt(message: Message, user) -> None:
    """Send the payment prompt for continued play.

    Test mode (payments_enabled=false): «тестовая оплата» button that
    emulates success instantly. Live mode: Platega checkout URL button.
    Shared by /pay and the post-registration flow.
    """
    payments_enabled = await get_payments_enabled()
    amount = await get_payment_amount()

    if not payments_enabled:
        await message.answer(
            f"👛 Приём платежей выключен. Нажмите кнопку для тестовой оплаты {amount // 100}₽ — "
            "доступ будет выдан мгновенно.",
            reply_markup=staging_payment_keyboard(amount=amount),
        )
        return

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


@payment_router.callback_query(TestPayment.filter())
async def handle_test_pay(callback_query: CallbackQuery, callback_data: TestPayment) -> None:
    """Handle the 'Тестовая оплата' button (staging only).

    Emulates a successful Platega payment: creates a succeeded Payment row,
    grants channel access, and notifies the user — without external redirect.
    The user stays in the bot (no channel link required to proceed).
    """
    from app.bot.services.payment_service import record_test_payment
    from app.bot.services.user_service import get_user_by_telegram_id

    user = await get_user_by_telegram_id(callback_query.from_user.id)
    if user is None:
        await callback_query.answer("Сначала зарегистрируйтесь через /start.", show_alert=False)
        return

    amount = int(callback_data.amount)
    try:
        await record_test_payment(user_id=user.id, amount=amount)
    except Exception as e:
        logger.exception("test payment failed for user %s", user.id)
        await callback_query.answer(f"Ошибка: {e}", show_alert=True)
        return

    await callback_query.answer("✅ Тестовая оплата прошла! Доступ открыт.", show_alert=True)
    await callback_query.message.edit_text(  # type: ignore[union-attr]
        "Тестовая оплата прошла успешно! Доступ к квесту открыт.\n"
        "Ваши первые шаги:\n"
        "/today — задания на сегодня\n"
        "/report — отчёт о дне"
    )

