"""Leaderboard keyboards."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class LeaderboardRefresh(CallbackData, prefix="lb"):
    """Callback data for the leaderboard refresh button."""

    pass


def leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Build the leaderboard keyboard with refresh button."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔄 Обновить",
        callback_data=LeaderboardRefresh(),
    )
    builder.adjust(1)
    return builder.as_markup()
