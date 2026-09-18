"""Inline-button command runner — executes slash commands from menu//today buttons.

Single entry point: RunCommand(command="/wakeup") reuses the same core logic
as the text commands (via tg_id/reply shims), so buttons and typed commands
always behave identically.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.callbacks.runner import RunCommand
from app.bot.handlers.daily import (
    _handle_scroll_command,
    _resolve_breath,
    handle_report,
    handle_today,
)
from app.bot.handlers.help import handle_help
from app.bot.handlers.leaderboard import handle_leaderboard
from app.bot.handlers.payment import send_pay_prompt
from app.bot.handlers.progress import handle_progress
from app.bot.handlers.referral import referral_handler
from app.bot.services.user_service import get_user_by_telegram_id

run_router = Router(name="run")

# command -> (scroll_code, xp_override); /breath resolved separately (slots)
_SCROLL_COMMANDS: dict[str, tuple[str, int | None]] = {
    "/wakeup": ("rassvet", None),
    "/cold": ("ogne", None),
    "/scan": ("korni", 0),
    "/scanreport": ("korni", None),
    "/micro": ("sledy", None),
    "/focus": ("zrya", None),
    "/food": ("pitaniye", None),
    "/sleep": ("integratsiya", None),
}


@run_router.callback_query(RunCommand.filter())
async def handle_run(
    callback: CallbackQuery, state: FSMContext, callback_data: RunCommand
) -> None:
    """Execute a slash command from an inline button."""
    await callback.answer()
    cmd = callback_data.command
    tg_id = callback.from_user.id
    message = callback.message
    reply = message.answer

    if cmd in _SCROLL_COMMANDS:
        code, xp_override = _SCROLL_COMMANDS[cmd]
        await _handle_scroll_command(
            message, cmd, code, xp_override=xp_override, tg_id=tg_id, reply=reply
        )
    elif cmd == "/breath":
        user = await get_user_by_telegram_id(tg_id)
        code, slot = await _resolve_breath(user)
        await _handle_scroll_command(
            message, cmd, code, slot=slot, tg_id=tg_id, reply=reply
        )
    elif cmd == "/report":
        await handle_report(message, state, tg_id=tg_id, reply=reply)
    elif cmd == "/today":
        await handle_today(message, state, tg_id=tg_id, reply=reply)
    elif cmd == "/progress":
        await handle_progress(message, tg_id=tg_id, reply=reply)
    elif cmd == "/leaderboard":
        await handle_leaderboard(message, tg_id=tg_id, reply=reply)
    elif cmd == "/pay":
        user = await get_user_by_telegram_id(tg_id)
        if user is None:
            await reply("Сначала зарегистрируйтесь через /start.")
        else:
            await send_pay_prompt(message, user)
    elif cmd == "/referral":
        await referral_handler(message, tg_id=tg_id, reply=reply)
    elif cmd == "/help":
        await handle_help(message, state, reply=reply)
    else:
        await reply(f"Неизвестная команда {cmd}. Откройте /menu.")
