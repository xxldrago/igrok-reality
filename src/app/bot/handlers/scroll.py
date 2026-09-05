"""Scroll delivery handlers — completion callback."""

from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.callbacks.scroll import ScrollCompletion

scroll_router = Router(name="scroll")


@scroll_router.callback_query(ScrollCompletion.filter())
async def handle_scroll_completion(callback: CallbackQuery) -> None:
    """Handle scroll completion button press — acknowledge and edit message."""
    await callback.answer("\u041e\u0442\u043c\u0435\u0447\u0435\u043d\u043e! \u2705")
    await callback.message.edit_text(
        "\u0421\u0432\u0438\u0442\u043e\u043a \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d! \u041e\u0442\u043b\u0438\u0447\u043d\u0430\u044f \u0440\u0430\u0431\u043e\u0442\u0430! \U0001f389"
    )
