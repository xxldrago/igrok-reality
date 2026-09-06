"""Admin panel handler — /admin command opens TMA admin panel via WebAppInfo."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, Message, WebAppInfo

from app.bot.services.user_service import get_user_by_telegram_id
from app.shared.config import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

ADMIN_ROLES = {"master", "leader", "curator"}

admin_handler_router = Router(name="admin")


@admin_handler_router.message(Command("admin"))
async def handle_admin(message: Message) -> None:
    """Handle /admin command — check role and show WebAppInfo button."""
    user = await get_user_by_telegram_id(message.from_user.id)

    if user is None:
        await message.answer("Вы не зарегистрированы. Начните с /start")
        return

    if user.role == "player":
        await message.answer(
            "У вас нет доступа к админ-панели. Обратитесь к Мастеру."
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть админ-панель",
                    web_app=WebAppInfo(url=f"{settings.TMA_WEBAPP_URL}/app/"),
                )
            ]
        ]
    )

    await message.answer(
        "Админ-панель доступна. Нажмите кнопку ниже:",
        reply_markup=keyboard,
    )
