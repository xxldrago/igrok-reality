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
async def referral_handler(
    message: Message, tg_id: int | None = None, reply=None
) -> None:
    """Handle /referral command — show user their unique referral link."""
    tid = tg_id if tg_id is not None else message.from_user.id
    send = reply or message.answer
    user = await get_user_by_telegram_id(tid)

    if user is None:
        await send("Сначала зарегистрируйтесь: /start")
        return

    # Ensure the user has a referral code (legacy users may not have one)
    code = await ensure_referral_code(user.id)

    link = f"https://t.me/{settings.BOT_USERNAME}?start={code}"
    text = (
        f"Ваша реферальная ссылка:\n{link}\n\n"
        "Поделитесь с друзьями! За каждого оплатившего реферала вы получаете комиссию."
    )

    from aiogram.types import CopyTextButton

    builder = InlineKeyboardBuilder()
    # Native Telegram copy button (copies to clipboard on tap).
    # The old callback_data="copy_ref:..." button had no handler and did nothing.
    builder.button(text="Скопировать ссылку", copy_text=CopyTextButton(text=link))
    keyboard = builder.as_markup()

    await send(text, reply_markup=keyboard)
