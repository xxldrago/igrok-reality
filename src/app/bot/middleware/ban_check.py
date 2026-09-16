"""Ban check middleware — blocks banned users from interacting with the bot."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from app.bot.services.user_service import get_user_by_telegram_id

logger = logging.getLogger(__name__)


class BanCheckMiddleware(BaseMiddleware):
    """Middleware that blocks all messages from banned users."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user is None:
            return await handler(event, data)

        user = await get_user_by_telegram_id(event.from_user.id)
        if user is not None and user.is_banned:
            await event.answer(
                "⛔ Ваш аккаунт заблокирован. Обратитесь к поддержке: /help"
            )
            return None

        return await handler(event, data)
