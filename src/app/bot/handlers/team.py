"""Team handler — /myteam, /mygroup, /myquests commands for mentors and players."""

from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.bot.services.team_service import MENTOR_ROLES, get_group_members
from app.bot.services.user_service import get_user_by_telegram_id
from app.shared.database import session_factory
from app.shared.models.group import Group
from app.shared.models.specialist_quest import SpecialistQuest
from app.shared.models.user import User

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


@team_router.message(Command("mygroup"))
async def mygroup_handler(message: Message) -> None:
    """Show users in the assigned Group model (curator/specialist)."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    if user.role not in MENTOR_ROLES:
        await message.answer("Команда недоступна")
        return

    # Find the group owned by this user
    async with session_factory() as session:
        result = await session.execute(
            select(Group).where(Group.owner_id == user.id)
        )
        group = result.scalar_one_or_none()

    if group is None:
        await message.answer("У вас нет назначенной группы. Обратитесь к Мастеру.")
        return

    # Get members of this group
    async with session_factory() as session:
        members_result = await session.execute(
            select(User).where(User.group_id == group.id)
        )
        members = list(members_result.scalars().all())

    if not members:
        await message.answer(f"Группа «{group.name}» пока пуста.")
        return

    lines = [f"👥 Группа «{group.name}» ({len(members)}/{group.max_members}):"]
    for m in members:
        payment = "💳" if m.is_active else "🚫"
        name = m.first_name
        if m.username:
            name = f"@{m.username}"
        lines.append(f"  • {name} — 🔥 {m.streak} {payment}")

    await message.answer("\n".join(lines))


@team_router.message(Command("myquests"))
async def myquests_handler(message: Message) -> None:
    """Show specialist quests assigned to the user's group."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    if user.group_id is None:
        await message.answer("Вы не состоите в группе с доп. квестами.")
        return

    today = datetime.now(timezone.utc).date()
    # Find user's quest day based on started_at
    if user.started_at:
        started = user.started_at.replace(tzinfo=timezone.utc)
        delta = (today - started.date()).days
        quest_day = min(delta + 1, 90)
    else:
        await message.answer("Квест ещё не начат.")
        return

    async with session_factory() as session:
        result = await session.execute(
            select(SpecialistQuest).where(
                SpecialistQuest.group_id == user.group_id,
                SpecialistQuest.day_number == quest_day,
            )
        )
        quests = list(result.scalars().all())

    if not quests:
        await message.answer("Доп. квестов на сегодня нет.")
        return

    lines = [f"📋 Доп. квесты (день {quest_day}):"]
    for q in quests:
        lines.append(f"\n🔹 *{q.title}*\n{q.content}")
        if q.media_file_id:
            lines.append(f"📎 Вложение: {q.media_file_id}")

    await message.answer("\n".join(lines), parse_mode="Markdown")
