"""Scroll delivery handlers — completion callback."""

from __future__ import annotations

from uuid import UUID

from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.callbacks.scroll import ScrollCompletion
from app.bot.services.progress_service import (
    add_xp,
    create_completion,
    update_leaderboard,
)

scroll_router = Router(name="scroll")


@scroll_router.callback_query(ScrollCompletion.filter())
async def handle_scroll_completion(callback: CallbackQuery) -> None:
    """Handle scroll completion button press — award XP and update leaderboard."""
    scroll_id = callback.data.split(":")[-1]

    try:
        parsed_scroll_id = UUID(scroll_id)
    except ValueError:
        await callback.answer("Ошибка: неверный ID свитка.")
        return

    user_id = UUID(callback.from_user.id)

    completion = await create_completion(user_id=user_id, scroll_id=parsed_scroll_id)

    if completion is None:
        await callback.answer("\u0423\u0436\u0435 \u043e\u0442\u043c\u0435\u0447\u0435\u043d\u043e!")
        return

    new_xp = await add_xp(user_id=user_id, xp=completion.xp_awarded)
    await update_leaderboard(user_id=user_id, xp=new_xp)

    await callback.answer(f"+{completion.xp_awarded} XP! \u26a1")
    await callback.message.edit_text(
        "\u0421\u0432\u0438\u0442\u043e\u043a \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d! \u041e\u0442\u043b\u0438\u0447\u043d\u0430\u044f \u0440\u0430\u0431\u043e\u0442\u0430! \U0001f389"
    )
