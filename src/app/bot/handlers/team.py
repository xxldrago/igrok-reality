"""Team handler — /myteam command for curators and mentors."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.services.team_service import MENTOR_ROLES, get_group_members
from app.bot.services.user_service import get_user_by_telegram_id

team_router = Router(name="team")


@team_router.message(Command("myteam"))
async def myteam_handler(message: Message) -> None:
    """Handle /myteam command — show group members for curators/mentors."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    if user.role not in MENTOR_ROLES:
        await message.answer("Команда недоступна")
        return

    members = await get_group_members(user.id)

    if not members:
        await message.answer("У вас пока нет участников в команде")
        return

    lines = [f"👥 Ваша команда ({len(members)}):"]
    for m in members:
        payment = "💳" if m.is_active else "🚫"
        name = m.first_name
        if m.username:
            name = f"@{m.username}"
        lines.append(f"  • {name} — 🔥 {m.streak} {payment}")

    await message.answer("\n".join(lines))
