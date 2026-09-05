"""Scroll delivery callback data factories."""

from aiogram.filters.callback_data import CallbackData


class ScrollCompletion(CallbackData, prefix="scroll"):
    """Callback data for the scroll completion button."""

    scroll_id: str
