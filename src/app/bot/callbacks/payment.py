"""Payment callback data factories."""

from aiogram.filters.callback_data import CallbackData


class PaymentInit(CallbackData, prefix="pay"):
    """Callback data for the payment initiation button."""

    amount: str
