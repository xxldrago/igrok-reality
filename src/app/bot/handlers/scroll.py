"""Scroll delivery handlers — report-first completion flow.

Flow:
1. User clicks '📝 Пройти свиток' → entries report FSM (waiting_for_report).
2. User sends report content (text / photo / video / document) → stored in FSM state.
3. User clicks '✅ Свиток пройден' → completion created with the attached
   report, XP awarded, report forwarded to Master. Without attached content
   the scroll is NOT counted; reports are accepted only on the scroll's own
   quest day (until 23:59 local time).
"""

from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ContentType, Message

from app.bot.callbacks.scroll import ScrollCompletion
from app.bot.keyboards.scroll import ScrollReportAction, report_action_keyboard
from app.bot.services.master_feed_service import forward_report_to_master
from app.bot.services.user_service import get_user_by_telegram_id
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
    "Без отчёта свиток не засчитается."
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

    # Resolve the real user — never fabricate a UUID from the telegram id.
    db_user = await get_user_by_telegram_id(callback.from_user.id)
    if db_user is None:
        await callback.answer("Сначала зарегистрируйтесь через /start.")
        return
    user_id = db_user.id

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

    # Load the daily scroll for report/XP policy (None for legacy rows).
    daily_scroll = await _get_daily_scroll(scroll_id)

    # Deadline: reports are accepted only on the scroll's own quest day
    # (grace-aware, i.e. until 23:59 local time). Late submits are rejected.
    scroll_day = await _resolve_scroll_day(scroll_id, daily_scroll)
    if scroll_day is None:
        await callback.answer("Свиток не найден.")
        await state.clear()
        return
    current_day = await _get_user_quest_day(user_id)
    if current_day == 0 or scroll_day != current_day:
        await callback.answer(
            "Отчёт принимается только в день свитка (до 23:59).",
            show_alert=True,
        )
        await state.clear()
        return

    # A scroll counts as passed only with attached content + submit.
    has_content = bool(data.get("report_text") or data.get("media_file_id"))
    if not has_content:
        await callback.answer(
            "Сначала отправьте текст или файл отчёта, затем нажмите «✅ Свиток пройден».",
            show_alert=True,
        )
        return  # keep the state so the user can attach the report

    # Effective XP: per-scroll override → scroll type default → legacy weights.
    xp_override = await _resolve_scroll_xp(daily_scroll)

    # Build the completion, awarding XP.
    completion = await create_completion(
        user_id=user_id, scroll_id=scroll_id, xp_override=xp_override
    )
    if completion is None:
        await callback.answer("\u0423\u0436\u0435 \u043e\u0442\u043c\u0435\u0447\u0435\u043d\u043e!")
        await state.clear()
        return

    # Attach the report (content is guaranteed by the check above).
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

    # Remove the passed scroll's delivery message from the chat.
    try:
        from app.bot.services.delivery_service import delete_delivery_message

        scroll_code = await _resolve_scroll_code(daily_scroll)
        if scroll_code is not None:
            await delete_delivery_message(
                callback.bot,
                callback.from_user.id,
                user_id,
                scroll_day,
                scroll_code,
            )
    except Exception:
        import logging

        logging.getLogger(__name__).warning(
            "delivery cleanup failed for user %s", user_id
        )

    # Forward the report to Master (content is mandatory, always attached).
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


async def _get_user_quest_day(user_id: UUID) -> int:
    """Current grace-aware quest day of a user (0 when unknown/not started)."""
    from sqlalchemy import select

    from app.bot.services.day_type import get_current_quest_day
    from app.bot.services.settings_service import get_grace_period_hours
    from app.shared.database import session_factory
    from app.shared.models.user import User
    from app.shared.config import settings

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return 0
        tz_name = user.timezone or settings.TZ
        grace = await get_grace_period_hours()
        return get_current_quest_day(user.started_at, tz_name, grace)


async def _resolve_scroll_day(scroll_id: UUID, daily_scroll) -> int | None:
    """Quest day of a scroll: DailyScroll first, legacy Scroll fallback."""
    if daily_scroll is not None:
        return daily_scroll.day_number
    from sqlalchemy import select

    from app.shared.database import session_factory
    from app.shared.models.scroll import Scroll

    async with session_factory() as session:
        result = await session.execute(select(Scroll).where(Scroll.id == scroll_id))
        scroll = result.scalar_one_or_none()
        return scroll.day_number if scroll is not None else None


async def _resolve_scroll_code(daily_scroll) -> str | None:
    """Scroll type code for delivery-row lookup (None for legacy rows)."""
    if daily_scroll is None:
        return None
    from sqlalchemy import select

    from app.shared.database import session_factory
    from app.shared.models.scroll_type import ScrollType

    async with session_factory() as session:
        result = await session.execute(
            select(ScrollType).where(ScrollType.id == daily_scroll.scroll_type_id)
        )
        scroll_type = result.scalar_one_or_none()
        return scroll_type.code if scroll_type is not None else None


async def _get_daily_scroll(scroll_id: UUID):
    """Load a DailyScroll by id (None for legacy Scroll rows)."""
    from sqlalchemy import select

    from app.shared.database import session_factory
    from app.shared.models.daily_scroll import DailyScroll

    async with session_factory() as session:
        result = await session.execute(
            select(DailyScroll).where(DailyScroll.id == scroll_id)
        )
        return result.scalar_one_or_none()


async def _resolve_scroll_xp(daily_scroll) -> int | None:
    """Effective XP for a completion: scroll override → type default → None (legacy weights)."""
    if daily_scroll is None:
        return None
    if daily_scroll.xp_reward is not None:
        return daily_scroll.xp_reward
    from sqlalchemy import select

    from app.shared.database import session_factory
    from app.shared.models.scroll_type import ScrollType

    async with session_factory() as session:
        result = await session.execute(
            select(ScrollType).where(ScrollType.id == daily_scroll.scroll_type_id)
        )
        scroll_type = result.scalar_one_or_none()
        if scroll_type is not None:
            return scroll_type.xp_reward
    return None


async def _finalize_report_and_forward(
    user_id: UUID,
    scroll_id: UUID,
) -> None:
    """Helper: load the completion + user + scroll and forward the report to Master's chat."""
    import logging

    from app.shared.database import session_factory
    from app.shared.models.completion import UserCompletion
    from app.shared.models.daily_scroll import DailyScroll
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

        # Completions reference DailyScroll rows (current flow) or legacy Scroll rows.
        day_number: int | None = None
        daily_result = await session.execute(
            select(DailyScroll).where(DailyScroll.id == scroll_id)
        )
        daily = daily_result.scalar_one_or_none()
        if daily is not None:
            day_number = daily.day_number
        else:
            scroll_result = await session.execute(
                select(Scroll).where(Scroll.id == scroll_id)
            )
            scroll = scroll_result.scalar_one_or_none()
            if scroll is not None:
                day_number = scroll.day_number

        if completion and user and day_number is not None:
            await forward_report_to_master(completion, user, day_number)
        else:
            logging.getLogger(__name__).warning(
                "report forward skipped: completion=%s user=%s day=%s",
                bool(completion),
                bool(user),
                day_number,
            )