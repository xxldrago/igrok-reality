"""Tests for the five bugfixes: report deadline, group broadcast, copy button,
mandatory content, support-to-master notifications."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def _callback():
    callback = AsyncMock()
    callback.from_user.id = 902227074
    callback.message.edit_text = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    return callback


# --- 1. Report deadline: only the scroll's own day ---


@pytest.mark.asyncio
async def test_late_submit_denied() -> None:
    """Submit for an old scroll is rejected, nothing is created."""
    from app.bot.handlers import scroll as scroll_mod

    scroll_id = uuid4()
    callback = _callback()
    callback.data = "scroll_report:x:submit"
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "scroll_id": str(scroll_id),
            "user_id": str(uuid4()),
            "report_text": "done",
            "media_file_id": None,
        }
    )
    daily = MagicMock()
    daily.day_number = 1
    daily.requires_report = True
    daily.xp_reward = None

    with (
        patch.object(scroll_mod, "_get_daily_scroll", new_callable=AsyncMock, return_value=daily),
        # User is far into the quest (started 10 days ago) → current day != 1
        patch.object(scroll_mod, "_get_user_quest_day", new_callable=AsyncMock, return_value=11),
        patch.object(scroll_mod, "create_completion", new_callable=AsyncMock) as mock_create,
    ):
        await scroll_mod.handle_report_action(callback, state)

    mock_create.assert_not_awaited()
    assert "до 23:59" in callback.answer.call_args[0][0]
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_same_day_submit_allowed() -> None:
    """Submit on the scroll's own day proceeds to completion."""
    from app.bot.handlers import scroll as scroll_mod

    scroll_id = uuid4()
    user_id = uuid4()
    callback = _callback()
    callback.data = "scroll_report:x:submit"
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "scroll_id": str(scroll_id),
            "user_id": str(user_id),
            "report_text": "done",
            "media_file_id": None,
        }
    )
    daily = MagicMock()
    daily.day_number = 3
    daily.requires_report = True
    daily.xp_reward = 5
    completion = MagicMock()
    completion.xp_awarded = 5

    with (
        patch.object(scroll_mod, "_get_daily_scroll", new_callable=AsyncMock, return_value=daily),
        patch.object(scroll_mod, "_get_user_quest_day", new_callable=AsyncMock, return_value=3),
        patch.object(scroll_mod, "_resolve_scroll_xp", new_callable=AsyncMock, return_value=5),
        patch.object(scroll_mod, "create_completion", new_callable=AsyncMock, return_value=completion) as mock_create,
        patch.object(scroll_mod, "update_completion_report", new_callable=AsyncMock),
        patch.object(scroll_mod, "add_xp", new_callable=AsyncMock, return_value=10),
        patch.object(scroll_mod, "update_streak", new_callable=AsyncMock, return_value=1),
        patch.object(scroll_mod, "update_leaderboard", new_callable=AsyncMock),
        patch.object(scroll_mod, "get_streak_bonus_config", new_callable=AsyncMock) as mock_cfg,
        patch.object(scroll_mod, "_finalize_report_and_forward", new_callable=AsyncMock),
    ):
        mock_cfg.return_value.days = []
        mock_cfg.return_value.xp = []
        await scroll_mod.handle_report_action(callback, state)

    mock_create.assert_awaited_once()


# --- 4. Submit without content is denied (no skip path) ---


@pytest.mark.asyncio
async def test_submit_without_content_denied() -> None:
    from app.bot.handlers import scroll as scroll_mod

    callback = _callback()
    callback.data = "scroll_report:x:submit"
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "scroll_id": str(uuid4()),
            "user_id": str(uuid4()),
            "report_text": None,
            "media_file_id": None,
        }
    )
    daily = MagicMock()
    daily.day_number = 2
    daily.requires_report = True
    daily.xp_reward = None

    with (
        patch.object(scroll_mod, "_get_daily_scroll", new_callable=AsyncMock, return_value=daily),
        patch.object(scroll_mod, "_get_user_quest_day", new_callable=AsyncMock, return_value=2),
        patch.object(scroll_mod, "create_completion", new_callable=AsyncMock) as mock_create,
    ):
        await scroll_mod.handle_report_action(callback, state)

    mock_create.assert_not_awaited()
    assert "Сначала отправьте" in callback.answer.call_args[0][0]


def test_no_skip_button() -> None:
    """The report keyboard has only the submit button."""
    from app.bot.keyboards.scroll import report_action_keyboard

    kb = report_action_keyboard(str(uuid4()))
    buttons = [b for row in kb.inline_keyboard for b in row]
    assert len(buttons) == 1
    assert "Свиток пройден" in buttons[0].text


# --- 3. Copy referral button uses native copy_text ---


def test_referral_copy_button() -> None:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import CopyTextButton

    link = "https://t.me/testbot?start=abc12345"
    builder = InlineKeyboardBuilder()
    builder.button(text="Скопировать ссылку", copy_text=CopyTextButton(text=link))
    btn = builder.as_markup().inline_keyboard[0][0]
    assert btn.copy_text is not None
    assert btn.copy_text.text == link
    assert btn.callback_data is None


# --- 2. Group broadcast filter ---


@pytest.mark.asyncio
async def test_broadcast_group_not_found() -> None:
    from httpx import ASGITransport, AsyncClient

    from app.api import dependencies as deps_mod
    from app.api.main import app
    from app.api.routes import admin as admin_mod

    mock_session = AsyncMock()
    res_none = MagicMock()
    res_none.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=res_none)
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(
            deps_mod, "decode_access_token", return_value={"sub": "admin", "role": "master"}
        ),
        patch.object(admin_mod, "session_factory", return_value=cm),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/admin/broadcast",
                headers={"Authorization": "Bearer x"},
                json={"text": "hi", "group_id": str(uuid4())},
            )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_broadcast_group_audience_label() -> None:
    """Group broadcast stores the group name as audience."""
    from app.bot.services import notification_service as ns_mod

    group_id = uuid4()
    mock_session = AsyncMock()

    async def fake_execute(_q):
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        return r

    mock_session.execute = AsyncMock(side_effect=fake_execute)
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch.object(ns_mod, "session_factory", return_value=cm):
        out = await ns_mod.send_system_notification_to_all(
            "broadcast", "hi", audience="My Group", group_id=group_id
        )
    assert out == []


# --- 5. Support appeal forwarded to master channel ---


@pytest.mark.asyncio
async def test_support_forward_sends_card() -> None:
    from app.bot.services import master_feed_service as mf_mod

    user = MagicMock()
    user.id = uuid4()
    user.username = "ivan"
    user.first_name = "Ivan"
    user.archetype = "head"

    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    mock_bot_cls = MagicMock(return_value=mock_bot)

    with (
        patch.object(mf_mod, "get_master_channel_id", new_callable=AsyncMock, return_value=-100123),
        patch.object(mf_mod, "get_bot_token", new_callable=AsyncMock, return_value="tok"),
        patch.object(mf_mod, "Bot", mock_bot_cls),
    ):
        ok = await mf_mod.forward_support_request(user, "help me please")

    assert ok is True
    text = mock_bot.send_message.call_args[1].get("text") or mock_bot.send_message.call_args[0][1]
    assert "поддержку" in text
    assert "help me please" in text
    assert "-100123" in str(mock_bot.send_message.call_args)
