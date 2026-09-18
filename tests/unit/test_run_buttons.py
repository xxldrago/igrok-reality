"""Tests for inline-button command execution (/menu, /today buttons)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.callbacks.runner import RunCommand
from app.bot.handlers import runner as runner_mod


def _callback(command: str):
    callback = AsyncMock()
    callback.from_user.id = 902227074
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    data = MagicMock()
    data.command = command
    return callback, data


def _user():
    user = MagicMock()
    user.id = uuid4()
    user.timezone = "Europe/Moscow"
    user.paid_at = "paid"
    user.started_at = MagicMock()
    user.role = "player"
    return user


@pytest.mark.asyncio
async def test_run_scroll_command_routes_with_tg_id() -> None:
    """run:/wakeup reaches the scroll core with the button presser's id."""
    callback, data = _callback("/wakeup")
    state = AsyncMock()
    with patch.object(
        runner_mod, "_handle_scroll_command", new_callable=AsyncMock
    ) as mock_core:
        await runner_mod.handle_run(callback, state, data)
    callback.answer.assert_awaited_once()
    kwargs = mock_core.call_args[1]
    assert kwargs["tg_id"] == 902227074
    assert mock_core.call_args[0][1] == "/wakeup"
    assert mock_core.call_args[0][2] == "rassvet"
    assert kwargs["xp_override"] is None


@pytest.mark.asyncio
async def test_run_scan_uses_zero_xp_override() -> None:
    """/scan keeps its +0 XP override through the button flow."""
    callback, data = _callback("/scan")
    state = AsyncMock()
    with patch.object(
        runner_mod, "_handle_scroll_command", new_callable=AsyncMock
    ) as mock_core:
        await runner_mod.handle_run(callback, state, data)
    assert mock_core.call_args[0][2] == "korni"
    assert mock_core.call_args[1]["xp_override"] == 0


@pytest.mark.asyncio
async def test_run_breath_resolves_slot() -> None:
    """/breath button resolves morning/day/evening like the command."""
    callback, data = _callback("/breath")
    state = AsyncMock()
    user = _user()
    with (
        patch.object(
            runner_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user
        ),
        patch.object(runner_mod, "_resolve_breath", new_callable=AsyncMock, return_value=("vetr_day", "day")),
        patch.object(
            runner_mod, "_handle_scroll_command", new_callable=AsyncMock
        ) as mock_core,
    ):
        await runner_mod.handle_run(callback, state, data)
    assert mock_core.call_args[0][2] == "vetr_day"
    assert mock_core.call_args[1]["slot"] == "day"


@pytest.mark.asyncio
async def test_run_simple_actions() -> None:
    """today/report/progress/leaderboard/referral/help route with tg_id+reply."""
    for cmd, target in (
        ("/today", "handle_today"),
        ("/report", "handle_report"),
        ("/progress", "handle_progress"),
        ("/leaderboard", "handle_leaderboard"),
        ("/referral", "referral_handler"),
    ):
        callback, data = _callback(cmd)
        state = AsyncMock()
        with patch.object(runner_mod, target, new_callable=AsyncMock) as mock_fn:
            await runner_mod.handle_run(callback, state, data)
        assert mock_fn.call_args[1]["tg_id"] == 902227074, cmd
        assert "reply" in mock_fn.call_args[1], cmd


@pytest.mark.asyncio
async def test_run_pay_and_unknown() -> None:
    """Pay prompts the looked-up user; unknown commands get a hint."""
    from app.bot.handlers import payment as pay_mod  # noqa: ensure importable

    callback, data = _callback("/pay")
    state = AsyncMock()
    user = _user()
    with (
        patch.object(runner_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user),
        patch.object(runner_mod, "send_pay_prompt", new_callable=AsyncMock) as mock_pay,
    ):
        await runner_mod.handle_run(callback, state, data)
    assert mock_pay.call_args[0][1] == user

    callback2, data2 = _callback("/nope")
    with patch.object(runner_mod, "_handle_scroll_command", new_callable=AsyncMock):
        await runner_mod.handle_run(callback2, state, data2)
    text = callback2.message.answer.call_args[0][0]
    assert "/menu" in text


@pytest.mark.asyncio
async def test_menu_builds_run_buttons() -> None:
    """handle_menu renders scroll + action buttons with run: callbacks."""
    from app.bot.handlers import help as help_mod

    user = _user()
    user.started_at = None  # no quest day → no scroll buttons, actions only
    message = AsyncMock()
    message.from_user.id = 902227074
    message.answer = AsyncMock()
    with patch.object(
        help_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user
    ):
        await help_mod.handle_menu(message)

    kwargs = message.answer.call_args[1]
    kb = kwargs["reply_markup"]
    callbacks = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert any(c.startswith("run:/today") for c in callbacks)
    assert any(c.startswith("run:/report") for c in callbacks)
    assert any(c.startswith("run:/pay") for c in callbacks)


@pytest.mark.asyncio
async def test_today_attaches_run_buttons() -> None:
    """handle_today attaches per-scroll run buttons."""
    from app.bot.handlers import daily as daily_mod

    user = _user()
    message = AsyncMock()
    message.from_user.id = 902227074
    message.answer = AsyncMock()
    state = AsyncMock()

    st = MagicMock()
    st.code = "rassvet"
    st.command = "/wakeup"
    st.name = "Рассвет"
    st.hour = 5
    st.minute = 0
    st.xp_reward = 5

    mock_session = AsyncMock()
    res_types = MagicMock()
    res_types.scalars.return_value.all.return_value = [st]
    res_cmds = MagicMock()
    res_cmds.all.return_value = []
    mock_session.execute = AsyncMock(side_effect=[res_cmds, res_types])
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(daily_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user),
        patch.object(daily_mod, "_get_quest_day", return_value=2),
        patch.object(daily_mod, "get_grace_period_hours", new_callable=AsyncMock, return_value=5),
        patch.object(daily_mod, "session_factory", return_value=cm),
    ):
        await daily_mod.handle_today(message, state)

    kwargs = message.answer.call_args[1]
    kb = kwargs["reply_markup"]
    callbacks = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "run:/wakeup" in callbacks
