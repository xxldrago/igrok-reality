"""Scroll delivery keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks.scroll import ScrollCompletion


def completion_keyboard(scroll_id: str) -> InlineKeyboardMarkup:
    """Build the completion keyboard with a single 'Выполнить' button.

    Args:
        scroll_id: The UUID of the scroll to mark as completed.

    Returns:
        InlineKeyboardMarkup with one completion button.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="\u2705 Выполнить",
        callback_data=ScrollCompletion(scroll_id=scroll_id).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()
