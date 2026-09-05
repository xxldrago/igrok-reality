"""Telegram bot process entrypoint."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.handlers.leaderboard import leaderboard_router
from app.bot.handlers.payment import payment_router
from app.bot.handlers.progress import progress_router
from app.bot.handlers.referral import referral_router
from app.bot.handlers.registration import registration_router
from app.bot.handlers.scroll import scroll_router
from app.shared.config import settings

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the Telegram bot with Redis-backed FSM storage."""
    logger.info(
        "Bot starting — environment=%s log_level=%s",
        settings.ENVIRONMENT,
        settings.LOG_LEVEL,
    )

    bot = Bot(token=settings.BOT_TOKEN)
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)

    dp.include_router(registration_router)
    dp.include_router(scroll_router)
    dp.include_router(progress_router)
    dp.include_router(leaderboard_router)
    dp.include_router(payment_router)
    dp.include_router(referral_router)

    logger.info("Dispatcher configured — polling started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
