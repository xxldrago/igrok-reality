"""Payment callback data factories."""

from aiogram.filters.callback_data import CallbackData


class PaymentInit(CallbackData, prefix="pay"):
    """Callback data for the payment initiation button."""

    amount: str


class TestPayment(CallbackData, prefix="testpay"):
    """Callback data for the test payment button (staging only).

    When pressed, emulate a successful Platega payment for the user
    without redirecting them to an external payment provider.
    """

    amount: str

