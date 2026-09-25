"""Callback data for running bot commands from inline buttons."""

from aiogram.filters.callback_data import CallbackData


class RunCommand(CallbackData, prefix="run"):
    """Run a slash command from an inline button (menu, /today).

    command: the slash command to execute (e.g. "/wakeup", "/today").
    """

    command: str


class InfoPage(CallbackData, prefix="info"):
    """Show an info page (privacy, agreement, contacts, pricing) from /menu.

    page: one of "privacy" | "agreement" | "contacts" | "pricing".
    """

    page: str
