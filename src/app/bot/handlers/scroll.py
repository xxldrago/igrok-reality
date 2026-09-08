"""Scroll delivery handlers — completion callback and report attachment."""

from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ContentType, Message

from app.bot.callbacks.scroll import ScrollCompletion
from app.bot.services.progress_service import (
    add_xp,
    create_completion,
    update_completion_report,
    update_leaderboard,
    update_streak,
)
from app.bot.states.completion import CompletionReportState

scroll_router = Router(name="scroll")


@scroll_router.callback_query(ScrollCompletion.filter())
async def handle_scroll_completion(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle scroll completion button press — award XP and update leaderboard."""
    scroll_id = callback.data.split(":")[-1]

    try:
        parsed_scroll_id = UUID(scroll_id)
    except ValueError:
        await callback.answer("Ошибка: неверный ID свитка.")
        return

    user_id = UUID(callback.from_user.id)

    completion = await create_completion(user_id=user_id, scroll_id=parsed_scroll_id)

    if completion is None:
        await callback.answer("\u0423\u0436\u0435 \u043e\u0442\u043c\u0435\u0447\u0435\u043d\u043e!")
        return

    new_xp = await add_xp(user_id=user_id, xp=completion.xp_awarded)
    await update_streak(user_id=user_id)
    await update_leaderboard(user_id=user_id, xp=new_xp)

    await callback.answer(f"+{completion.xp_awarded} XP! \u26a1")

    # Ask if user wants to attach a report
    await state.set_state(CompletionReportState.asking_for_report)
    await state.update_data(scroll_id=str(parsed_scroll_id), user_id=str(user_id))

    await callback.message.edit_text(
        "\u0421\u0432\u0438\u0442\u043e\u043a \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d! \u041e\u0442\u043b\u0438\u0447\u043d\u0430\u044f \u0440\u0430\u0431\u043e\u0442\u0430! \U0001f389\n\n"
        "Хотите добавить отчёт? Отправьте текст, фото или видео. "
        "Или нажмите /skip чтобы пропустить."
    )


@scroll_router.message(CompletionReportState.asking_for_report, Command("skip"))
async def skip_report(message: Message, state: FSMContext) -> None:
    """Skip report attachment."""
    await state.clear()
    await message.answer("Отчёт не добавлен. Продолжайте в том же духе!")


@scroll_router.message(CompletionReportState.asking_for_report)
async def handle_report_text(message: Message, state: FSMContext) -> None:
    """Handle text report."""
    data = await state.get_data()
    scroll_id = UUID(data["scroll_id"])
    user_id = UUID(data["user_id"])

    await update_completion_report(
        user_id=user_id,
        scroll_id=scroll_id,
        report_text=message.text or message.caption,
    )

    await state.clear()
    await message.answer("Отчёт сохранён. Спасибо!")


@scroll_router.message(
    CompletionReportState.asking_for_report,
    F.content_type.in_({ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT}),
)
async def handle_report_media(message: Message, state: FSMContext) -> None:
    """Handle photo/video/document report."""
    data = await state.get_data()
    scroll_id = UUID(data["scroll_id"])
    user_id = UUID(data["user_id"])

    file_id = None
    media_type = None

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    elif message.document:
        file_id = message.document.file_id
        media_type = "document"

    if file_id:
        await update_completion_report(
            user_id=user_id,
            scroll_id=scroll_id,
            report_media_url=file_id,
            report_media_type=media_type,
            report_text=message.caption,
        )

    await state.clear()
    await message.answer("Отчёт сохранён. Спасибо!")
