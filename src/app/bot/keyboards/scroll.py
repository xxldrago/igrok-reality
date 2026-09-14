"""Scroll delivery keyboards."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks.scroll import ScrollCompletion


class ScrollReportAction(CallbackData, prefix="scroll_report"):
    """Callback data for the report submit/skip buttons shown while in FSM state.

    action: "submit" to complete with the stored report, "skip" to complete without.
    """

    scroll_id: str
    action: str


def completion_keyboard(scroll_id: str) -> InlineKeyboardMarkup:
    """Build the entry keyboard with a single 'Пройти свиток' button.

    Clicking it puts the user into the report FSM flow (report is not required
    to complete the scroll).

    Args:
        scroll_id: The UUID of the scroll to complete.

    Returns:
        InlineKeyboardMarkup with one entry button.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="\U0001F4DD Пройти свиток",
        callback_data=ScrollCompletion(scroll_id=scroll_id).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


def report_action_keyboard(scroll_id: str) -> InlineKeyboardMarkup:
    """Build the submit/skip keyboard shown while collecting the report.

    Args:
        scroll_id: The UUID of the scroll being completed.

    Returns:
        InlineKeyboardMarkup with 'Свиток пройден' and 'Пропустить отчёт' buttons.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="\u2705 Свиток пройден",
        callback_data=ScrollReportAction(scroll_id=scroll_id, action="submit").pack(),
    )
    builder.button(
        text="\u23ED Пропустить отчёт",
        callback_data=ScrollReportAction(scroll_id=scroll_id, action="skip").pack(),
    )
    builder.adjust(1)
    return builder.as_markup()