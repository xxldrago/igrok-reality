"""Tests for delivery-message bookkeeping and expiry cleanup."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services import delivery_service as dl_mod


def _session_cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_record_delivery_inserts() -> None:
    """New triple inserts a row and commits."""
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=res)

    with patch.object(dl_mod, "session_factory", return_value=_session_cm(mock_session)):
        await dl_mod.record_delivery(uuid4(), 5, "rassvet", 123)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    row = mock_session.add.call_args[0][0]
    assert row.message_id == 123
    assert row.quest_day == 5


@pytest.mark.asyncio
async def test_record_delivery_updates_existing() -> None:
    """Existing triple updates message_id instead of duplicating."""
    existing = MagicMock()
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=res)

    with patch.object(dl_mod, "session_factory", return_value=_session_cm(mock_session)):
        await dl_mod.record_delivery(uuid4(), 5, "rassvet", 999)

    mock_session.add.assert_not_called()
    assert existing.message_id == 999
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_delivery_message_deletes_row() -> None:
    """Found row: telegram message deleted, row removed, True returned."""
    row = MagicMock()
    row.message_id = 321
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = row
    mock_session.execute = AsyncMock(return_value=res)
    mock_bot = AsyncMock()

    with patch.object(dl_mod, "session_factory", return_value=_session_cm(mock_session)):
        ok = await dl_mod.delete_delivery_message(mock_bot, 111, uuid4(), 5, "rassvet")

    assert ok is True
    mock_bot.delete_message.assert_awaited_once_with(chat_id=111, message_id=321)
    mock_session.delete.assert_awaited_once_with(row)


@pytest.mark.asyncio
async def test_delete_delivery_message_missing_row() -> None:
    """No row: bot untouched, False returned."""
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=res)
    mock_bot = AsyncMock()

    with patch.object(dl_mod, "session_factory", return_value=_session_cm(mock_session)):
        ok = await dl_mod.delete_delivery_message(mock_bot, 111, uuid4(), 5, "rassvet")

    assert ok is False
    mock_bot.delete_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_deletes_only_expired() -> None:
    """Rows with quest_day < current day are deleted, others kept."""
    old_row = MagicMock()
    old_row.user_id = uuid4()
    old_row.quest_day = 3
    old_row.scroll_code = "rassvet"
    fresh_row = MagicMock()
    fresh_row.user_id = old_row.user_id
    fresh_row.quest_day = 10
    fresh_row.scroll_code = "ogne"

    user = MagicMock()
    user.id = old_row.user_id
    user.telegram_id = 111
    user.timezone = "Europe/Moscow"
    user.started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    mock_session = AsyncMock()
    calls = {"n": 0}

    async def fake_execute(_q):
        calls["n"] += 1
        r = MagicMock()
        if calls["n"] == 1:
            # First query: all delivery rows
            r.scalars.return_value.all.return_value = [old_row, fresh_row]
        else:
            # Second query: users
            r.scalars.return_value.all.return_value = [user]
        return r

    mock_session.execute = AsyncMock(side_effect=fake_execute)
    deleted_calls: list = []

    async def fake_delete(bot, telegram_id, user_id, quest_day, scroll_code):
        deleted_calls.append((quest_day, scroll_code))
        return True

    import app.bot.services.day_type as day_mod
    import app.bot.services.settings_service as settings_mod

    with (
        patch.object(dl_mod, "session_factory", return_value=_session_cm(mock_session)),
        patch.object(dl_mod, "delete_delivery_message", new_callable=AsyncMock, side_effect=fake_delete),
        patch.object(day_mod, "get_current_quest_day", return_value=10),
        patch.object(settings_mod, "get_grace_period_hours", new_callable=AsyncMock, return_value=5),
        patch.object(settings_mod, "get_bot_token", new_callable=AsyncMock, return_value="tok"),
        patch("aiogram.Bot"),
    ):
        out = await dl_mod.cleanup_expired_deliveries({})

    assert out == {"deleted": 1, "failed": 0}
    assert deleted_calls == [(3, "rassvet")]
