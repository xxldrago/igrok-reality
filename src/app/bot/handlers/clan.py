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
    get_all_clans_progress,
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
        f"⚔️ Клан «{clan.name}»",
        f"👥 Участников: {len(members)}",
        f"🔥 Общий XP: {progress.total_xp}",
        f"📊 Средний XP: {progress.avg_xp:.0f}",
        f"🔗 Средний streak: {progress.avg_streak:.0f}",
    ]

    await message.answer("\n".join(lines))


async def handle_clan_create(message: Message, user, name: str) -> None:
    """Create a new clan."""
    if user.role not in ("leader", "master"):
        await message.answer("Только Лидер может создавать кланы")
        return

    clan = await create_clan(user.id, name)
    await message.answer(f"⚔️ Клан «{clan.name}» создан!\nВаш ID клана: `{clan.id}`")


async def handle_clan_join(message: Message, user, clan_id_str: str) -> None:
    """Join an existing clan."""
    try:
        clan_id = UUID(clan_id_str)
    except ValueError:
        await message.answer("Неверный формат ID клана")
        return

    ok = await join_clan(user.id, clan_id)
    if ok:
        await message.answer("Вы вступили в клан!")
    else:
        await message.answer("Не удалось вступить в клан. Проверьте ID.")


async def handle_clan_leave(message: Message, user) -> None:
    """Leave current clan."""
    ok = await leave_clan(user.id)
    if ok:
        await message.answer("Вы покинули клан.")
    else:
        await message.answer("Вы не состоите в клане.")


@clan_router.message(Command("clans"))
async def clans_ranking_handler(message: Message) -> None:
    """Handle /clans command — show clan ranking by XP."""
    clans = await get_all_clans_progress()

    if not clans:
        await message.answer("Пока нет кланов. Создайте первый: /clan create <название>")
        return

    # Sort by total XP descending
    clans.sort(key=lambda c: c.total_xp, reverse=True)

    lines = ["⚔️ Рейтинг кланов:\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, clan in enumerate(clans):
        medal = medals[i] if i < 3 else f"  {i+1}."
        lines.append(
            f"{medal} «{clan.clan_name}» — "
            f"👥 {clan.member_count} | "
            f"🔥 {clan.total_xp} XP | "
            f"📊 {clan.avg_xp:.0f} средн."
        )

    await message.answer("\n".join(lines))
