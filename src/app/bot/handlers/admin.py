"""Admin panel handler — /admin command opens TMA admin panel via WebAppInfo."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.bot.services.user_service import get_user_by_telegram_id
from app.shared.config import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

ADMIN_ROLES = {"master", "leader", "curator"}
ALLOWED_PAGES = {"users", "scrolls", "payments", "settings", "audit"}
# Pages restricted to master only
MASTER_ONLY_PAGES = {"settings"}
# Pages restricted to master or leader
LEADER_PLUS_PAGES = {"audit"}

admin_handler_router = Router(name="admin")


def parse_admin_page(message_text: str) -> str | None:
    """Extract the page argument from /admin command text.

    Returns page name if valid, None otherwise.
    """
    parts = message_text.strip().split()
    # parts[0] is "/admin", parts[1] would be the page
    if len(parts) < 2:
        return None
    page = parts[1].lower()
    if page in ALLOWED_PAGES:
        return page
    return None


@admin_handler_router.message(Command("admin"))
async def handle_admin(message: Message, command: CommandObject) -> None:
    """Handle /admin [page] command — check role and show WebAppInfo button."""
    user = await get_user_by_telegram_id(message.from_user.id)

    if user is None:
        await message.answer("Вы не зарегистрированы. Начните с /start")
        return

    if user.role == "player":
        await message.answer(
            "У вас нет доступа к админ-панели. Обратитесь к Мастеру."
        )
        return

    # Parse optional page argument
    page = parse_admin_page(message.text)

    # Page-level role checks
    if page in MASTER_ONLY_PAGES and user.role != "master":
        await message.answer("Только Мастер может открывать настройки")
        return

    if page in LEADER_PLUS_PAGES and user.role not in {"master", "leader"}:
        await message.answer("Только Мастер или Лидер могут открывать аудит")
        return

    # Build WebAppInfo URL
    if page:
        webapp_url = f"{settings.TMA_WEBAPP_URL}/app/{page}"
    else:
        webapp_url = f"{settings.TMA_WEBAPP_URL}/app/"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть админ-панель",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ]
        ]
    )

    await message.answer(
        "Админ-панель доступна. Нажмите кнопку ниже:",
        reply_markup=keyboard,
    )
