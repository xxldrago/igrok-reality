"""Callback data factories for the Telegram bot."""

from app.bot.callbacks.registration import ArchetypeAnswer, ConsentCallback
from app.bot.callbacks.scroll import ScrollCompletion

__all__ = ["ArchetypeAnswer", "ConsentCallback", "ScrollCompletion"]
