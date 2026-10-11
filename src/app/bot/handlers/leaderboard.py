"""Leaderboard handler — /leaderboard command (group-scoped)."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.leaderboard import LeaderboardRefresh, leaderboard_keyboard
from app.bot.services.settings_service import get_leaderboard_limit
from app.bot.services.user_service import (
    get_group_leaders,
    get_user_by_telegram_id,
)

leaderboard_router = Router(name="leaderboard")

MEDALS = {0: "🥇", 1: "🥈", 2: "🥉"}


def _display_name(user) -> str:
    """Human-readable name with @username fallback."""
    if getattr(user, "username", None):
        return f"{user.first_name} (@{user.username})"
    return user.first_name or "Игрок"


async def format_leaderboard_message(message: Message, tg_id: int | None = None) -> str:
    """Format the group leaderboard (top members of the user's quest group)."""
    tid = tg_id if tg_id is not None else message.from_user.id
    current_user = await get_user_by_telegram_id(tid)
    if current_user is None:
        return "Сначала зарегистрируйтесь через /start."
    if current_user.group_id is None:
        return (
            "🏆 Ты пока не в группе — таблица лидеров появится, "
            "когда тебя распределят в поток после оплаты."
        )

    limit = await get_leaderboard_limit()
    leaders = await get_group_leaders(current_user.group_id, limit)
    if not leaders:
        return "Пока нет данных. Выполняй свитки чтобы попасть в рейтинг!"

    lines = ["🏆 Лидеры твоей группы:\n"]
    for i, user in enumerate(leaders):
        medal = MEDALS.get(i, f"{i + 1}.")
        lines.append(f"{medal} {_display_name(user)} — {user.xp or 0} XP")

    # Show user's rank if not in top N
    ids = [u.id for u in leaders]
    if current_user.id not in ids:
        full = await get_group_leaders(current_user.group_id, 1000)
        rank = next((i for i, u in enumerate(full) if u.id == current_user.id), None)
        if rank is not None:
            lines.append(f"\nТы на позиции #{rank + 1} в группе")

    return "\n".join(lines)


async def handle_leaderboard(
    message: Message, tg_id: int | None = None, reply=None
) -> None:
    """Handle /leaderboard command — show the group leaders by XP."""
    tid = tg_id if tg_id is not None else message.from_user.id
    send = reply or message.answer
    text = await format_leaderboard_message(message, tg_id=tid)
    await send(text, reply_markup=leaderboard_keyboard())


async def handle_leaderboard_refresh(callback: CallbackQuery) -> None:
    """Handle leaderboard refresh button press."""
    text = await format_leaderboard_message(callback.message)
    await callback.message.edit_text(text, reply_markup=leaderboard_keyboard())
    await callback.answer()


@leaderboard_router.message(Command("leaderboard"))
async def leaderboard_handler(message: Message) -> None:
    """Register /leaderboard command handler."""
    await handle_leaderboard(message)


@leaderboard_router.callback_query(LeaderboardRefresh.filter())
async def leaderboard_refresh_handler(callback: CallbackQuery) -> None:
    """Register leaderboard refresh callback handler."""
    await handle_leaderboard_refresh(callback)
