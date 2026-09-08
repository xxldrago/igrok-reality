"""Completion report flow FSM states."""

from aiogram.fsm.state import State, StatesGroup


class CompletionReportState(StatesGroup):
    """States for attaching a report after scroll completion.

    Flow: completed -> asking_for_report -> waiting_for_report
    """

    completed = State()
    asking_for_report = State()
    waiting_for_report = State()