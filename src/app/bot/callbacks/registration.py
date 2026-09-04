"""Registration flow callback data factories."""

from aiogram.filters.callback_data import CallbackData


class ConsentCallback(CallbackData, prefix="consent"):
    """Callback data for the consent approval buttons."""

    action: str  # "agree" or "decline"


class ArchetypeAnswer(CallbackData, prefix="arch"):
    """Callback data for archetype quiz answer buttons."""

    question: int  # question number (1-4)
    answer: str  # answer letter ("a", "b", "c", "d")
