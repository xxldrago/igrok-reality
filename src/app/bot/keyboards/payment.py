"""Payment keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks.payment import PaymentInit


def payment_keyboard(amount: int, payment_url: str | None = None) -> InlineKeyboardMarkup:
    """Build the 'Оплатить' button.

    Args:
        amount: Payment amount in kopecks.
        payment_url: Provider checkout URL. When None, a stub button is
            built that fires PaymentInit (answered with a 'coming soon' notice).

    Returns:
        InlineKeyboardMarkup with one payment button.
    """
    builder = InlineKeyboardBuilder()
    if payment_url:
        builder.button(text=f"Оплатить {amount // 100} ₽", url=payment_url)
    else:
        builder.button(
            text=f"Оплатить {amount // 100} ₽",
            callback_data=PaymentInit(amount=str(amount)).pack(),
        )
    builder.adjust(1)
    return builder.as_markup()
