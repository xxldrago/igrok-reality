"""Inline and reply keyboards for the Telegram bot."""

from app.bot.keyboards.registration import (
    ARCHETYPE_QUESTIONS,
    archetype_keyboard,
    consent_keyboard,
)
from app.bot.keyboards.scroll import completion_keyboard

__all__ = [
    "ARCHETYPE_QUESTIONS",
    "archetype_keyboard",
    "completion_keyboard",
    "consent_keyboard",
]
