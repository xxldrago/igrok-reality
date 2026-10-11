"""Scroll delivery callback data factories."""

from aiogram.filters.callback_data import CallbackData


class ScrollCompletion(CallbackData, prefix="scroll"):
    """Callback data for the scroll completion button."""

    scroll_id: str


class DailyReportSubmit(CallbackData, prefix="daily_report"):
    """Callback data for the /report flow submit button (no fields)."""
