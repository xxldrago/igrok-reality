"""Progress handler — /progress and /profile commands for user stats display."""

from __future__ import annotations

from uuid import UUID

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.services.progress_service import get_full_profile, get_user_stats
from app.bot.services.user_service import get_user_by_telegram_id
from app.shared.config import settings

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


async def handle_profile(message: Message) -> None:
    """Handle /profile command — show full user profile."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    profile = await get_full_profile(user.id)

    lines = [
        "👤 Твой профиль",
        "",
        f"📋 Архетип: {profile['archetype_name']}",
        f"📅 {profile['quest_day']}",
        f"⚡ XP: {profile['xp']}",
        f"🔥 Серия: {profile['streak']} дней",
        f"✅ Выполнено: {profile['completions']} свитков",
    ]

    if profile["role"] != "player":
        role_display = {
            "curator": "Куратор",
            "leader": "Лидер",
            "specialist": "Специалист",
            "master": "Мастер",
        }
        lines.append(f"🎖 Роль: {role_display.get(profile['role'], profile['role'])}")

    lines.append(f"💳 {profile['payment_status']}")

    if profile["referral_code"]:
        link = f"https://t.me/{settings.BOT_USERNAME}?start={profile['referral_code']}"
        lines.append("")
        lines.append(f"🔗 Реферальная ссылка:\n{link}")

    await message.answer("\n".join(lines))


@progress_router.message(Command("profile"))
async def profile_handler(message: Message) -> None:
    """Register /profile command handler."""
    await handle_profile(message)
