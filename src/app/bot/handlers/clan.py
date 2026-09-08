"""Clan handler — /clan commands for leaders and members."""

from __future__ import annotations

from uuid import UUID

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.services.clan_service import (
    create_clan,
    join_clan,
    leave_clan,
    get_user_clan,
    get_clan_progress,
    get_clan_members,
)
from app.bot.services.user_service import get_user_by_telegram_id
from app.bot.services.role_service import is_valid_role

clan_router = Router(name="clan")


async def handle_clan(message: Message) -> None:
    """Handle /clan command — show clan info or create/join."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    # Check if user has clan args
    args = message.text.split(maxsplit=2) if message.text else []
    if len(args) >= 2:
        subcmd = args[1].lower()
        if subcmd == "create" and len(args) >= 3:
            await handle_clan_create(message, user, args[2])
            return
        elif subcmd == "join" and len(args) >= 3:
            await handle_clan_join(message, user, args[2])
            return
        elif subcmd == "leave":
            await handle_clan_leave(message, user)
            return

    # Default: show clan info
    clan = await get_user_clan(user.id)
    if clan is None:
        await message.answer(
            "Вы не состоите в клане.\n"
            "Создайте клан: /clan create <название> (только для лидеров)\n"
            "Или вступите: /clan join <clan_id>"
        )
        return

    progress = await get_clan_progress(clan.id)
    members = await get_clan_members(clan.id)

    lines = [
        f"🏰 Клан: {clan.name}",
        f"👥 Участников: {len(members)}",
    ]
    if progress:
        lines.extend([
            f"⚡ Суммарный XP: {progress.total_xp}",
            f"📊 Средний XP: {progress.avg_xp:.0f}",
            f"🔥 Суммарная серия: {progress.total_streak}",
            f"📈 Средняя серия: {progress.avg_streak:.1f}",
        ])
    lines.append("")
    lines.append("Участники:")
    for m in members[:20]:
        name = f"@{m.username}" if m.username else m.first_name
        lines.append(f"  • {name} — ⚡{m.xp} 🔥{m.streak}")

    await message.answer("\n".join(lines))


async def handle_clan_create(message: Message, user, name: str) -> None:
    """Handle /clan create <name> — only leaders can create."""
    if user.role != "leader":
        await message.answer("Только лидеры могут создавать кланы")
        return

    clan = await create_clan(user.id, name)
    await message.answer(f"Клан '{clan.name}' создан! Вы автоматически вступили в него.")


async def handle_clan_join(message: Message, user, clan_id_str: str) -> None:
    """Handle /clan join <clan_id>."""
    try:
        clan_id = UUID(clan_id_str)
    except ValueError:
        await message.answer("Неверный ID клана")
        return

    if user.clan_id is not None:
        await message.answer("Вы уже состоите в клане. Сначала покиньте его: /clan leave")
        return

    success = await join_clan(user.id, clan_id)
    if success:
        await message.answer("Вы вступили в клан!")
    else:
        await message.answer("Не удалось вступить (клан не найден или уже в клане)")


async def handle_clan_leave(message: Message, user) -> None:
    """Handle /clan leave."""
    if user.clan_id is None:
        await message.answer("Вы не состоите в клане")
        return

    success = await leave_clan(user.id)
    if success:
        await message.answer("Вы покинули клан")
    else:
        await message.answer("Не удалось покинуть клан")


@clan_router.message(Command("clan"))
async def clan_handler(message: Message) -> None:
    """Register /clan command handler."""
    await handle_clan(message)