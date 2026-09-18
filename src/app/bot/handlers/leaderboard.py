"""Leaderboard handler — /leaderboard command for top users display."""

from __future__ import annotations

from uuid import UUID

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.leaderboard import LeaderboardRefresh, leaderboard_keyboard
from app.bot.services.progress_service import get_leaderboard, get_user_rank
from app.bot.services.settings_service import get_leaderboard_limit
from app.bot.services.user_service import get_user_by_id, get_user_by_telegram_id

leaderboard_router = Router(name="leaderboard")

MEDALS = {0: "🥇", 1: "🥈", 2: "🥉"}


async def format_leaderboard_message(message: Message, tg_id: int | None = None) -> str:
    """Format leaderboard message with top users and medals."""
    tid = tg_id if tg_id is not None else message.from_user.id
    limit = await get_leaderboard_limit()
    leaderboard = await get_leaderboard(limit)

    if not leaderboard:
        return "Пока нет данных. Выполняй свитки чтобы попасть в рейтинг!"

    lines = ["🏆 Таблица лидеров:\n"]
    for i, entry in enumerate(leaderboard):
        user = await get_user_by_id(UUID(entry["user_id"]))
        name = user.first_name if user else "Неизвестный"
        medal = MEDALS.get(i, f"{i + 1}.")
        lines.append(f"{medal} {name} — {entry['xp']} XP")

    # Show user's rank if not in top N
    current_user = await get_user_by_telegram_id(tid)
    if current_user:
        rank = await get_user_rank(current_user.id)
        if rank is not None and rank >= limit:
            lines.append(f"\nТы на позиции #{rank + 1}")

    return "\n".join(lines)


async def handle_leaderboard(
    message: Message, tg_id: int | None = None, reply=None
) -> None:
    """Handle /leaderboard command — show top users by XP."""
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
