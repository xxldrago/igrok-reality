"""Payment keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks.payment import PaymentInit


def payment_keyboard(amount: int) -> InlineKeyboardMarkup:
    """Build the payment keyboard with a single 'Оплатить' button.

    Args:
        amount: Payment amount in kopecks.

    Returns:
        InlineKeyboardMarkup with one payment button.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"Оплатить {amount // 100} ₽",
        callback_data=PaymentInit(amount=str(amount)).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()
