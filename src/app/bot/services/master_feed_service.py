"""Master feed service — forward player reports to Master's chat."""

from __future__ import annotations

import logging
from uuid import UUID

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.bot.services.archetype import ARCHETYPE_NAMES
from app.bot.services.scroll_service import get_scroll_content
from app.bot.services.settings_service import get_bot_token, get_master_channel_id
from app.shared.models.completion import UserCompletion
from app.shared.models.user import User

logger = logging.getLogger(__name__)


async def _send_card(
    user: User,
    header: str,
    body_lines: list[str],
    media_url: str | None = None,
    media_type: str | None = None,
) -> bool:
    """Send a formatted card to the master channel (best-effort)."""
    master_chat_id = await get_master_channel_id()
    if not master_chat_id:
        logger.warning(
            "master_channel_id not configured; skipping master feed for user %s", user.id
        )
        return False

    bot = Bot(token=await get_bot_token())
    try:
        archetype_name = ARCHETYPE_NAMES.get(user.archetype, user.archetype or "—")
        lines = [
            header,
            "",
            f"👤 Игрок: @{user.username or user.first_name}",
            f"📋 Архетип: {archetype_name}",
        ]
        for block in body_lines:
            lines.append("")
            lines.append(block)
        text = "\n".join(lines)

        if media_url and media_type:
            try:
                if media_type == "photo":
                    await bot.send_photo(master_chat_id, media_url, caption=text)
                elif media_type == "video":
                    await bot.send_video(master_chat_id, media_url, caption=text)
                elif media_type == "document":
                    await bot.send_document(master_chat_id, media_url, caption=text)
                else:
                    await bot.send_message(master_chat_id, text)
            except TelegramAPIError:
                # Fallback to text-only
                await bot.send_message(master_chat_id, text)
        else:
            await bot.send_message(master_chat_id, text)

        return True
    except TelegramAPIError as e:
        logger.error("Failed to send master feed card: %s", e)
        return False
    finally:
        await bot.session.close()


async def forward_report_to_master(
    completion: UserCompletion,
    user: User,
    scroll_day: int,
) -> bool:
    """Forward a player's report to the Master's chat.

    Returns True if sent successfully, False if config missing or send failed.
    """
    body = [f"📅 День {scroll_day} из 90"]
    if completion.report_text:
        body.append(f"📝 Текст:\n{completion.report_text}")
    return await _send_card(
        user=user,
        header="📥 Новый отчёт",
        body_lines=body,
        media_url=completion.report_media_url,
        media_type=completion.report_media_type,
    )


async def forward_support_request(user: User, reason: str) -> bool:
    """Forward a /help support appeal to the master channel (best-effort)."""
    try:
        return await _send_card(
            user=user,
            header="🆘 Обращение в поддержку",
            body_lines=[f"📝 Текст:\n{reason}"] if reason else [],
        )
    except Exception:
        logger.exception("forward_support_request failed for user %s", user.id)
        return False
