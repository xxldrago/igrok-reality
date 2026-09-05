"""Referral handler — /referral command for viewing and sharing referral link."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.services.user_service import get_user_by_telegram_id
from app.shared.config import settings

referral_router = Router(name="referral")


@referral_router.message(Command("referral"))
async def referral_handler(message: Message) -> None:
    """Handle /referral command — show user their unique referral link."""
    user = await get_user_by_telegram_id(message.from_user.id)

    if user is None:
        await message.answer("Сначала зарегистрируйтесь: /start")
        return

    if user.referral_code is None:
        await message.answer("У вас нет реферального кода")
        return

    link = f"https://t.me/{settings.BOT_USERNAME}?start={user.referral_code}"
    text = (
        f"Ваша реферальная ссылка:\n{link}\n\n"
        "Поделитесь с друзьями! За каждого оплатившего реферала вы получаете комиссию."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="Скопировать ссылку", callback_data=f"copy_ref:{user.referral_code}")
    keyboard = builder.as_markup()

    await message.answer(text, reply_markup=keyboard)
