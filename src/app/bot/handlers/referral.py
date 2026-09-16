"""Referral handler — /referral command for viewing and sharing referral link."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.services.user_service import (
    ensure_referral_code,
    get_user_by_telegram_id,
)
from app.shared.config import settings

referral_router = Router(name="referral")


@referral_router.message(Command("referral"))
async def referral_handler(message: Message) -> None:
    """Handle /referral command — show user their unique referral link."""
    user = await get_user_by_telegram_id(message.from_user.id)

    if user is None:
        await message.answer("Сначала зарегистрируйтесь: /start")
        return

    # Ensure the user has a referral code (legacy users may not have one)
    code = await ensure_referral_code(user.id)

    link = f"https://t.me/{settings.BOT_USERNAME}?start={code}"
    text = (
        f"Ваша реферальная ссылка:\n{link}\n\n"
        "Поделитесь с друзьями! За каждого оплатившего реферала вы получаете комиссию."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="Скопировать ссылку", callback_data=f"copy_ref:{code}")
    keyboard = builder.as_markup()

    await message.answer(text, reply_markup=keyboard)
