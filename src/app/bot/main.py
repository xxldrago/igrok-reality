"""Telegram bot process entrypoint."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.shared.config import settings

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the Telegram bot."""
    logger.info("Bot starting...")

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # TODO: Register routers here in later phases

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
