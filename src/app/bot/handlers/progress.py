"""Progress handler — /progress command for user stats display."""

from __future__ import annotations

from uuid import UUID

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.services.progress_service import get_user_stats
from app.bot.services.user_service import get_user_by_telegram_id

progress_router = Router(name="progress")


async def handle_progress(message: Message) -> None:
    """Handle /progress command — show user's XP, streak, and completions count."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    stats = await get_user_stats(user.id)
    text = (
        f"Твой прогресс:\n"
        f"⚡ XP: {stats['xp']}\n"
        f"🔥 Серия: {stats['streak']} дней\n"
        f"✅ Выполнено: {stats['completions']} свитков"
    )
    await message.answer(text)


@progress_router.message(Command("progress"))
async def progress_handler(message: Message) -> None:
    """Register /progress command handler."""
    await handle_progress(message)
