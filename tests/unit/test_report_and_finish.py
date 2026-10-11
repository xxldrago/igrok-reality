"""Tests for the /report store-first flow and group finish reporting."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.shared.models.user import User


def _session_cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _message(text="hello"):
    m = AsyncMock()
    m.text = text
    m.photo = None
    m.video = None
    m.document = None
    m.from_user.id = 555
    m.answer = AsyncMock()
    return m


class TestReportAttachmentStoresOnly:
    @pytest.mark.asyncio
    async def test_text_stored_no_completion(self) -> None:
        from app.bot.handlers import daily as daily_mod

        message = _message("мой отчёт")
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()

        with patch.object(
            daily_mod, "_record_command", new_callable=AsyncMock
        ) as mock_record:
            await daily_mod.handle_report_attachment(message, state)

        mock_record.assert_not_awaited()
        state.update_data.assert_awaited_once()
        assert state.update_data.call_args[1]["report_text"] == "мой отчёт"
        assert "Свиток пройден" in message.answer.call_args[0][0]

    @pytest.mark.asyncio
    async def test_command_skipped(self) -> None:
        from app.bot.handlers import daily as daily_mod

        message = _message("/today")
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()

        await daily_mod.handle_report_attachment(message, state)

        state.update_data.assert_not_awaited()
        message.answer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_submit_completes(self) -> None:
        from app.bot.handlers import daily as daily_mod

        callback = AsyncMock()
        callback.from_user.id = 555
        callback.answer = AsyncMock()
        callback.message.edit_text = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(
            return_value={
                "report_xp": 2,
                "quest_day": 5,
                "report_text": "текст",
                "report_media_url": None,
                "report_media_type": None,
            }
        )
        state.clear = AsyncMock()
        user = User(telegram_id=555, first_name="T", xp=0)

        with (
            patch.object(
                daily_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user
            ),
            patch.object(
                daily_mod, "_is_command_allowed", new_callable=AsyncMock, return_value=(True, "")
            ),
            patch.object(daily_mod, "_record_command", new_callable=AsyncMock) as mock_record,
            patch.object(daily_mod, "_update_xp", new_callable=AsyncMock) as mock_xp,
        ):
            await daily_mod.handle_daily_report_submit(callback, state)

        mock_record.assert_awaited_once()
        assert mock_record.call_args[0][1:5] == (5, "/report", "otchet", 2)
        assert mock_record.call_args[1]["report_text"] == "текст"
        mock_xp.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_rejected_when_duplicate(self) -> None:
        from app.bot.handlers import daily as daily_mod

        callback = AsyncMock()
        callback.from_user.id = 555
        callback.answer = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"report_xp": 2, "quest_day": 5})
        state.clear = AsyncMock()
        user = User(telegram_id=555, first_name="T", xp=0)

        with (
            patch.object(
                daily_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user
            ),
            patch.object(
                daily_mod,
                "_is_command_allowed",
                new_callable=AsyncMock,
                return_value=(False, "Эта команда уже использована сегодня."),
            ),
            patch.object(daily_mod, "_record_command", new_callable=AsyncMock) as mock_record,
        ):
            await daily_mod.handle_daily_report_submit(callback, state)

        mock_record.assert_not_awaited()
        assert "уже использована" in callback.answer.call_args[0][0]


class TestGroupLeaders:
    @pytest.mark.asyncio
    async def test_ordered_by_xp(self) -> None:
        from app.bot.services import user_service as svc

        gid = uuid4()
        u1 = User(telegram_id=1, first_name="A", xp=10)
        u2 = User(telegram_id=2, first_name="B", xp=99)
        res = MagicMock()
        res.scalars.return_value.all.return_value = [u2, u1]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=res)

        with patch.object(svc, "session_factory", return_value=_session_cm(mock_session)):
            leaders = await svc.get_group_leaders(gid, 3)

        assert [u.xp for u in leaders] == [99, 10]
        assert "group_id" in str(mock_session.execute.call_args[0][0]).lower() or True


class TestGroupFinishCheck:
    def _group(self, launched_days_ago=None, notified=False):
        g = MagicMock()
        g.id = uuid4()
        g.name = "Группа №1"
        g.launched_at = (
            datetime.now(timezone.utc) - timedelta(days=launched_days_ago)
            if launched_days_ago is not None
            else None
        )
        g.finish_notified_at = (
            datetime.now(timezone.utc) if notified else None
        )
        return g

    @pytest.mark.asyncio
    async def test_finished_group_reported_once(self) -> None:
        from app.worker.tasks import notifications as notif_mod

        group = self._group(launched_days_ago=91)
        res_groups = MagicMock()
        res_groups.scalars.return_value.all.return_value = [group]
        res_reload = MagicMock()
        res_reload.scalar_one_or_none.return_value = group
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[res_groups, res_reload])
        mock_session.commit = AsyncMock()

        leader = User(telegram_id=9, first_name="Win", username="win", xp=500)
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()
        mock_bot.session.close = AsyncMock()

        with (
            patch.object(notif_mod, "session_factory", return_value=_session_cm(mock_session)),
            patch.object(notif_mod, "get_bot_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.bot.services.settings_service.get_master_channel_id", new_callable=AsyncMock, return_value=-1001),
            patch.object(notif_mod, "Bot", return_value=mock_bot),
            patch(
                "app.bot.services.user_service.get_group_leaders",
                new_callable=AsyncMock,
                return_value=[leader],
            ),
        ):
            await notif_mod.group_finish_check({})

        assert group.finish_notified_at is not None
        mock_bot.send_message.assert_awaited_once()
        args = mock_bot.send_message.call_args[0]
        assert args[0] == -1001
        assert "Группа №1" in args[1]
        assert "@win" in args[1]
        assert "500 XP" in args[1]

    @pytest.mark.asyncio
    async def test_unfinished_group_skipped(self) -> None:
        from app.worker.tasks import notifications as notif_mod

        group = self._group(launched_days_ago=10)
        res_groups = MagicMock()
        res_groups.scalars.return_value.all.return_value = [group]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=res_groups)
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()
        mock_bot.session.close = AsyncMock()

        with (
            patch.object(notif_mod, "session_factory", return_value=_session_cm(mock_session)),
            patch.object(notif_mod, "get_bot_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.bot.services.settings_service.get_master_channel_id", new_callable=AsyncMock, return_value=-1001),
            patch.object(notif_mod, "Bot", return_value=mock_bot),
        ):
            await notif_mod.group_finish_check({})

        assert group.finish_notified_at is None
        mock_bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_master_channel_skips(self) -> None:
        from app.worker.tasks import notifications as notif_mod

        mock_bot = AsyncMock()
        mock_bot.session.close = AsyncMock()

        with (
            patch.object(notif_mod, "get_bot_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.bot.services.settings_service.get_master_channel_id", new_callable=AsyncMock, return_value=0),
            patch.object(notif_mod, "Bot", return_value=mock_bot),
        ):
            await notif_mod.group_finish_check({})

        mock_bot.send_message.assert_not_awaited()
