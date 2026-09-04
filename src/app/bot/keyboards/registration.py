"""Registration flow keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks.registration import ConsentCallback


def consent_keyboard() -> InlineKeyboardMarkup:
    """Build the consent approval keyboard with agree/decline buttons."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Я согласен",
        callback_data=ConsentCallback(action="agree"),
    )
    builder.button(
        text="Отказаться",
        callback_data=ConsentCallback(action="decline"),
    )
    builder.adjust(1)
    return builder.as_markup()
