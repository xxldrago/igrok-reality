"""Payment keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def payment_keyboard(amount: int, payment_url: str) -> InlineKeyboardMarkup:
    """Build the payment keyboard with a URL button to Platega checkout.

    Args:
        amount: Payment amount in kopecks.
        payment_url: Platega payment page URL.

    Returns:
        InlineKeyboardMarkup with one payment button.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"Оплатить {amount // 100} ₽",
        url=payment_url,
    )
    builder.adjust(1)
    return builder.as_markup()
