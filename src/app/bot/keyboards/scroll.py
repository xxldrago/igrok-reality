"""Scroll delivery keyboards."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks.runner import RunCommand
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
        text="📝 Начать отчёт",
        callback_data=ScrollCompletion(scroll_id=scroll_id).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


def today_keyboard(
    available_codes: list[str],
    types_map: dict,
    done_pairs: set[tuple[str, str]],
) -> InlineKeyboardMarkup:
    """Build per-scroll run buttons for /today (done state included).

    Args:
        available_codes: Scroll type codes available today.
        types_map: code -> scroll type (name, command).
        done_pairs: {(command, slot)} already completed today.
    """
    slot_by_code = {"vetr": "morning", "vetr_day": "day", "vetr_evening": "evening"}
    builder = InlineKeyboardBuilder()
    for code in available_codes:
        st = types_map.get(code)
        if st is None:
            continue
        mark = "✅" if (st.command, slot_by_code.get(code, "")) in done_pairs else "⬜"
        builder.button(
            text=f"{mark} {st.name}",
            callback_data=RunCommand(command=st.command).pack(),
        )
    builder.adjust(1)
    return builder.as_markup()


def report_action_keyboard(scroll_id: str) -> InlineKeyboardMarkup:
    """Build the submit keyboard shown while collecting the report.

    A scroll counts as passed only after attached content + submit;
    there is no skip path.

    Args:
        scroll_id: The UUID of the scroll being completed.

    Returns:
        InlineKeyboardMarkup with the 'Свиток пройден' button.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="\u2705 Свиток пройден",
        callback_data=ScrollReportAction(scroll_id=scroll_id, action="submit").pack(),
    )
    builder.adjust(1)
    return builder.as_markup()