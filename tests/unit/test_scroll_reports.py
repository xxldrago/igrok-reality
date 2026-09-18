"""Tests for scroll completion fixes: real user resolution, mandatory reports, XP."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.handlers import scroll as scroll_mod


def _callback():
    callback = AsyncMock()
    callback.from_user.id = 902227074
    callback.message.edit_text = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    return callback


def _user():
    user = MagicMock()
    user.id = uuid4()
    return user


def _scroll_uuid():
    return uuid4()


@pytest.mark.asyncio
async def test_completion_entry_resolves_real_user() -> None:
    """Entry stores the real DB user id, never UUID(telegram_id)."""
    user = _user()
    scroll_id = _scroll_uuid()
    callback = _callback()
    callback.data = f"scroll:{scroll_id}"
    state = AsyncMock()

    with patch.object(
        scroll_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user
    ):
        await scroll_mod.handle_scroll_completion(callback, state)

    state.update_data.assert_awaited_once()
    stored = state.update_data.call_args[1]
    assert stored["user_id"] == str(user.id)
    assert stored["user_id"] != str(902227074)


@pytest.mark.asyncio
async def test_completion_entry_rejects_unknown_user() -> None:
    """Unregistered telegram id gets a /start hint, no state set."""
    callback = _callback()
    callback.data = f"scroll:{_scroll_uuid()}"
    state = AsyncMock()

    with patch.object(
        scroll_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=None
    ):
        await scroll_mod.handle_scroll_completion(callback, state)

    callback.answer.assert_awaited_once()
    assert "/start" in callback.answer.call_args[0][0]
    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_skip_denied_when_report_required() -> None:
    """Skip without content is refused for requires_report scrolls."""
    callback = _callback()
    callback.data = "scroll_report:x:skip"
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "scroll_id": str(_scroll_uuid()),
            "user_id": str(uuid4()),
            "report_text": None,
            "media_file_id": None,
        }
    )
    daily = MagicMock()
    daily.day_number = 4
    daily.requires_report = True
    daily.xp_reward = None

    with (
        patch.object(scroll_mod, "_get_daily_scroll", new_callable=AsyncMock, return_value=daily),
        patch.object(scroll_mod, "_get_user_quest_day", new_callable=AsyncMock, return_value=4),
        patch.object(scroll_mod, "create_completion", new_callable=AsyncMock) as mock_create,
    ):
        await scroll_mod.handle_report_action(callback, state)

    mock_create.assert_not_awaited()
    assert "Сначала отправьте" in callback.answer.call_args[0][0]
    state.clear.assert_not_awaited()


@pytest.mark.asyncio
async def test_submit_uses_scroll_xp_override() -> None:
    """Submit passes the scroll XP override into the completion."""
    user_id = uuid4()
    scroll_id = _scroll_uuid()
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
    daily.day_number = 4
    daily.requires_report = True
    daily.xp_reward = 7
    completion = MagicMock()
    completion.xp_awarded = 7

    with (
        patch.object(scroll_mod, "_get_daily_scroll", new_callable=AsyncMock, return_value=daily),
        patch.object(scroll_mod, "_get_user_quest_day", new_callable=AsyncMock, return_value=4),
        patch.object(scroll_mod, "_resolve_scroll_xp", new_callable=AsyncMock, return_value=7),
        patch.object(scroll_mod, "create_completion", new_callable=AsyncMock, return_value=completion) as mock_create,
        patch.object(scroll_mod, "update_completion_report", new_callable=AsyncMock),
        patch.object(scroll_mod, "add_xp", new_callable=AsyncMock, return_value=107),
        patch.object(scroll_mod, "update_streak", new_callable=AsyncMock, return_value=3),
        patch.object(scroll_mod, "update_leaderboard", new_callable=AsyncMock),
        patch.object(scroll_mod, "get_streak_bonus_config", new_callable=AsyncMock) as mock_cfg,
        patch.object(scroll_mod, "_finalize_report_and_forward", new_callable=AsyncMock),
    ):
        mock_cfg.return_value.days = []
        mock_cfg.return_value.xp = []
        await scroll_mod.handle_report_action(callback, state)

    # create_completion got the override
    assert mock_create.call_args[1]["xp_override"] == 7
    assert "+7 XP" in callback.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_reports_endpoint_shape() -> None:
    """GET /reports returns items with user/day/media fields."""
    from httpx import ASGITransport, AsyncClient

    from app.api import dependencies as deps_mod
    from app.api.main import app
    from app.api.routes import admin as admin_mod
    from app.shared.models.user_daily_command import UserDailyCommand

    user_id = uuid4()
    user = MagicMock()
    user.id = user_id
    user.username = "ivan"
    user.first_name = "Ivan"
    user.archetype = "head"
    user.telegram_id = 111

    cmd = MagicMock(spec=UserDailyCommand)
    cmd.id = uuid4()
    cmd.user_id = user_id
    cmd.quest_day = 5
    cmd.command = "/report"
    cmd.xp_awarded = 2
    from datetime import datetime, timezone

    cmd.completed_at = datetime(2026, 9, 10, tzinfo=timezone.utc)
    cmd.report_text = "great day"
    cmd.report_media_url = None
    cmd.report_media_type = None
    cmd.slot = ""

    mock_session = AsyncMock()

    async def fake_execute(query):
        compiled = str(query)
        result = MagicMock()
        scalars = MagicMock()
        if "users" in compiled and "user_daily_commands" not in compiled and "user_completions" not in compiled:
            scalars.all.return_value = [user]
        elif "user_completions" in compiled:
            scalars.all.return_value = []
        elif "user_daily_commands" in compiled:
            scalars.all.return_value = [cmd]
        else:
            scalars.all.return_value = []
        result.scalars.return_value = scalars
        result.scalar_one_or_none.return_value = None
        return result

    mock_session.execute = AsyncMock(side_effect=fake_execute)
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
            r = await client.get(
                "/api/admin/reports", headers={"Authorization": "Bearer x"}
            )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    item = body["reports"][0]
    assert item["source"] == "daily"
    assert item["quest_day"] == 5
    assert item["text"] == "great day"
    assert item["username"] == "ivan"
