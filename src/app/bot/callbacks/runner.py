"""Callback data for running bot commands from inline buttons."""

from aiogram.filters.callback_data import CallbackData


class RunCommand(CallbackData, prefix="run"):
    """Run a slash command from an inline button (menu, /today).

    command: the slash command to execute (e.g. "/wakeup", "/today").
    """

    command: str
