"""Master feed service — forward player reports to Master's chat."""

from __future__ import annotations

from uuid import UUID

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.bot.services.archetype import ARCHETYPE_NAMES
from app.bot.services.scroll_service import get_scroll_content
from app.bot.services.settings_service import get_bot_token, get_master_channel_id
from app.shared.models.completion import UserCompletion
from app.shared.models.user import User


async def forward_report_to_master(
    completion: UserCompletion,
    user: User,
    scroll_day: int,
) -> bool:
    """Forward a player's report to the Master's chat.

    Returns True if sent successfully, False if config missing or send failed.
    """
    master_chat_id = await get_master_channel_id()
    if not master_chat_id:
        # Config missing — log and skip (non-fatal)
        import logging
        logging.getLogger(__name__).warning(
            "master_channel_id not configured; skipping report forward for user %s", user.id
        )
        return False

    bot = Bot(token=await get_bot_token())
    try:
        archetype_name = ARCHETYPE_NAMES.get(user.archetype, user.archetype or "—")
        quest_day = f"День {scroll_day} из 90"

        lines = [
            "📥 Новый отчёт",
            "",
            f"👤 Игрок: @{user.username or user.first_name}",
            f"📋 Архетип: {archetype_name}",
            f"📅 {quest_day}",
        ]

        if completion.report_text:
            lines.append("")
            lines.append(f"📝 Текст:\n{completion.report_text}")

        text = "\n".join(lines)

        # Send media if present
        if completion.report_media_url and completion.report_media_type:
            try:
                if completion.report_media_type == "photo":
                    await bot.send_photo(
                        master_chat_id,
                        completion.report_media_url,
                        caption=text,
                    )
                elif completion.report_media_type == "video":
                    await bot.send_video(
                        master_chat_id,
                        completion.report_media_url,
                        caption=text,
                    )
                elif completion.report_media_type == "document":
                    await bot.send_document(
                        master_chat_id,
                        completion.report_media_url,
                        caption=text,
                    )
                else:
                    await bot.send_message(master_chat_id, text)
            except TelegramAPIError:
                # Fallback to text-only
                await bot.send_message(master_chat_id, text)
        else:
            await bot.send_message(master_chat_id, text)

        return True
    except TelegramAPIError as e:
        import logging
        logging.getLogger(__name__).error("Failed to forward report to Master: %s", e)
        return False
    finally:
        await bot.session.close()