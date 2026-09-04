"""Registration flow callback data factories."""

from aiogram.filters.callback_data import CallbackData


class ConsentCallback(CallbackData, prefix="consent"):
    """Callback data for the consent approval buttons."""

    action: str  # "agree" or "decline"
