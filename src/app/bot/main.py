"""Telegram bot process entrypoint."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.handlers.admin import admin_handler_router
from app.bot.handlers.clan import clan_router
from app.bot.handlers.daily import daily_router
from app.bot.handlers.help import help_router
from app.bot.handlers.leaderboard import leaderboard_router
from app.bot.handlers.payment import payment_router
from app.bot.handlers.progress import progress_router
from app.bot.handlers.referral import referral_router
from app.bot.handlers.registration import registration_router
from app.bot.handlers.runner import run_router
from app.bot.handlers.scroll import scroll_router
from app.bot.handlers.team import team_router
from app.bot.handlers.commission import router as commission_router
from app.bot.services.settings_service import get_bot_token
from app.shared.config import settings

logger = logging.getLogger(__name__)


async def _set_bot_commands(bot: Bot) -> None:
    """Set the Telegram command menu (☰ button) for all users."""
    from aiogram.types import BotCommand, BotCommandScopeDefault

    commands = [
        BotCommand(command="start", description="Регистрация / вход"),
        BotCommand(command="menu", description="Меню команд"),
        BotCommand(command="today", description="Свитки на сегодня"),
        BotCommand(command="progress", description="Мой прогресс"),
        BotCommand(command="leaderboard", description="Таблица лидеров"),
        BotCommand(command="referral", description="Реферальная ссылка"),
        BotCommand(command="mygroup", description="Моя группа"),
        BotCommand(command="myquests", description="Доп. квесты группы"),
        BotCommand(command="clans", description="Рейтинг кланов"),
        BotCommand(command="help", description="Помощь / связаться с куратором"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def main() -> None:
    """Start the Telegram bot with Redis-backed FSM storage."""
    logger.info(
        "Bot starting — environment=%s log_level=%s",
        settings.ENVIRONMENT,
        settings.LOG_LEVEL,
    )

    bot = Bot(token=await get_bot_token())
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)

    # Ban check middleware — blocks banned users from all commands
    from app.bot.middleware.ban_check import BanCheckMiddleware
    dp.message.middleware(BanCheckMiddleware())

    await _set_bot_commands(bot)

    dp.include_router(registration_router)
    dp.include_router(admin_handler_router)
    dp.include_router(scroll_router)
    dp.include_router(progress_router)
    dp.include_router(leaderboard_router)
    dp.include_router(payment_router)
    dp.include_router(referral_router)
    dp.include_router(team_router)
    dp.include_router(commission_router)
    dp.include_router(clan_router)
    dp.include_router(help_router)
    dp.include_router(run_router)
    dp.include_router(daily_router)

    logger.info("Dispatcher configured — polling started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
