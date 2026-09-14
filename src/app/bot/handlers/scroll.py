"""Scroll delivery handlers — report-first completion flow.

Flow:
1. User clicks '📝 Пройти свиток' → entries report FSM (waiting_for_report).
2. User sends report content (text / photo / video / document) → stored in FSM state.
3. User clicks '✅ Свиток пройден' → completion created with stored report, XP awarded, report forwarded to Master.
   Or clicks '⏭ Пропустить отчёт' → completion created without report, XP awarded.
"""

from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ContentType, Message

from app.bot.callbacks.scroll import ScrollCompletion
from app.bot.keyboards.scroll import ScrollReportAction, report_action_keyboard
from app.bot.services.master_feed_service import forward_report_to_master
from app.bot.services.progress_service import (
    add_xp,
    create_completion,
    update_completion_report,
    update_leaderboard,
    update_streak,
)
from app.shared.models.scroll import Scroll
from app.bot.services.settings_service import get_streak_bonus_config
from app.bot.states.completion import CompletionReportState

scroll_router = Router(name="scroll")

REPORT_PROMPT = (
    "\U0001F4DD Передайте отчёт по свитку.\n\n"
    "Пришлите текст, фото, видео или файл и нажмите «\u2705 Свиток пройден».\n"
    "Если отчёта нет — нажмите «\u23ED Пропустить отчёт»."
)


@scroll_router.callback_query(ScrollCompletion.filter())
async def handle_scroll_completion(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle 'Пройти свиток' button press — enter the report FSM (report is optional).

    Does NOT create the completion yet; that happens on submit/skip.
    """
    scroll_id = callback.data.split(":")[-1]

    try:
        parsed_scroll_id = UUID(scroll_id)
    except ValueError:
        await callback.answer("Ошибка: неверный ID свитка.")
        return

    user_id = UUID(callback.from_user.id)

    # Enter report-entry state.
    await state.set_state(CompletionReportState.waiting_for_report)
    await state.update_data(
        scroll_id=str(parsed_scroll_id),
        user_id=str(user_id),
        report_text=None,
        media_type=None,
        media_file_id=None,
    )

    await callback.answer()
    await callback.message.edit_text(
        REPORT_PROMPT,
        reply_markup=report_action_keyboard(str(parsed_scroll_id)),
    )


@scroll_router.callback_query(ScrollReportAction.filter())
async def handle_report_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle 'Свиток пройден' (submit) or 'Пропустить отчёт' (skip)."""
    action = callback.data.split(":")[-1]

    data = await state.get_data()
    scroll_id_str = data.get("scroll_id")
    user_id_str = data.get("user_id")

    if not scroll_id_str or not user_id_str:
        await callback.answer("Сессия истекла. Попробуйте ещё раз.")
        await state.clear()
        return

    try:
        scroll_id = UUID(scroll_id_str)
        user_id = UUID(user_id_str)
    except ValueError:
        await callback.answer("Ошибка: неверные данные сессии.")
        await state.clear()
        return

    # Build the completion, awarding XP.
    completion = await create_completion(user_id=user_id, scroll_id=scroll_id)
    if completion is None:
        await callback.answer("\u0423\u0436\u0435 \u043e\u0442\u043c\u0435\u0447\u0435\u043d\u043e!")
        await state.clear()
        return

    # Attach report if user chose to submit and provided content.
    if action == "submit":
        report_text = data.get("report_text") or None
        media_file_id = data.get("media_file_id") or None
        media_type = data.get("media_type") or None
        await update_completion_report(
            user_id=user_id,
            scroll_id=scroll_id,
            report_text=report_text,
            report_media_url=media_file_id,
            report_media_type=media_type,
        )

    new_xp = await add_xp(user_id=user_id, xp=completion.xp_awarded)
    new_streak = await update_streak(user_id=user_id)
    await update_leaderboard(user_id=user_id, xp=new_xp)

    # Check for streak bonus notification
    bonus_msg = ""
    bonus_config = await get_streak_bonus_config()
    bonus_thresholds = dict(zip(bonus_config.days, bonus_config.xp))
    if new_streak in bonus_thresholds:
        bonus_msg = f"\n\n🎉 Поздравляем! Серия {new_streak} дней — бонус +{bonus_thresholds[new_streak]} XP!"

    await callback.answer(f"+{completion.xp_awarded} XP! \u26a1{bonus_msg}")

    await callback.message.edit_text(
        "\u0421\u0432\u0438\u0442\u043e\u043a \u043f\u0440\u043e\u0439\u0434\u0435\u043d! \u041e\u0442\u043b\u0438\u0447\u043d\u0430\u044f \u0440\u0430\u0431\u043e\u0442\u0430! \U0001f389"
        f"{bonus_msg}"
    )

    await state.clear()

    # Forward report to Master if a report was attached.
    if action == "submit":
        await _finalize_report_and_forward(user_id, scroll_id)


@scroll_router.message(
    CompletionReportState.waiting_for_report,
    F.content_type == ContentType.TEXT,
)
async def handle_report_text(message: Message, state: FSMContext) -> None:
    """Store text report content and show confirmation with action buttons."""
    data = await state.get_data()
    scroll_id = data.get("scroll_id")

    if not scroll_id:
        await message.answer("Сессия истекла. Попробуйте ещё раз.")
        await state.clear()
        return

    await state.update_data(report_text=message.text)

    await message.answer(
        "\U0001F4CC Отчёт (текст) сохранён. Можете дополнить или нажмите «\u2705 Свиток пройден».",
        reply_markup=report_action_keyboard(scroll_id),
    )


@scroll_router.message(
    CompletionReportState.waiting_for_report,
    F.content_type.in_({ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT}),
)
async def handle_report_media(message: Message, state: FSMContext) -> None:
    """Store media report content (photo/video/document) and show confirmation."""
    data = await state.get_data()
    scroll_id = data.get("scroll_id")

    if not scroll_id:
        await message.answer("Сессия истекла. Попробуйте ещё раз.")
        await state.clear()
        return

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
        await state.update_data(
            media_file_id=file_id,
            media_type=media_type,
            report_text=message.caption or data.get("report_text"),
        )

    await message.answer(
        "\U0001F4CC Отчёт (медиа) сохранён. Можете дополнить или нажмите «\u2705 Свиток пройден».",
        reply_markup=report_action_keyboard(scroll_id),
    )


async def _finalize_report_and_forward(
    user_id: UUID,
    scroll_id: UUID,
) -> None:
    """Helper: load the completion + user + scroll and forward the report to Master's chat."""
    from app.shared.database import session_factory
    from app.shared.models.completion import UserCompletion
    from app.shared.models.user import User
    from sqlalchemy import select

    async with session_factory() as session:
        result = await session.execute(
            select(UserCompletion)
            .where(UserCompletion.user_id == user_id, UserCompletion.scroll_id == scroll_id)
        )
        completion = result.scalar_one_or_none()

        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        scroll_result = await session.execute(
            select(Scroll).where(Scroll.id == scroll_id)
        )
        scroll = scroll_result.scalar_one_or_none()

        if completion and user and scroll:
            await forward_report_to_master(completion, user, scroll.day_number)