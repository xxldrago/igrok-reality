"""Tests for /mygroup — own quest group display."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.handlers.team import mygroup_handler
from app.shared.models.group import Group
from app.shared.models.user import User


def _cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _user(group_id=None, role="player"):
    u = User(
        id=uuid4(),
        telegram_id=123,
        first_name="Test",
        archetype="head",
        role=role,
    )
    u.group_id = group_id
    return u


@pytest.mark.asyncio
async def test_mygroup_shows_own_quest_group() -> None:
    """Player with group_id sees their quest cohort, not 'no group'."""
    message = AsyncMock()
    message.from_user.id = 123
    message.answer = AsyncMock()

    gid = uuid4()
    group = Group(id=gid, name="Группа №1", type="quest", max_members=50)
    members = [_user(gid), _user(gid)]

    res_group = MagicMock()
    res_group.scalar_one_or_none.return_value = group
    res_members = MagicMock()
    res_members.scalars.return_value.all.return_value = members
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[res_group, res_members])

    with (
        patch("app.bot.handlers.team.get_user_by_telegram_id", return_value=_user(gid)),
        patch("app.bot.handlers.team.session_factory", return_value=_cm(mock_session)),
    ):
        await mygroup_handler(message)

    text = message.answer.call_args[0][0]
    assert "Группа №1" in text
    assert "нет назначенной группы" not in text


@pytest.mark.asyncio
async def test_mygroup_no_group_hint() -> None:
    """Player without any group still gets the Master hint."""
    message = AsyncMock()
    message.from_user.id = 123
    message.answer = AsyncMock()

    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=res)

    with (
        patch("app.bot.handlers.team.get_user_by_telegram_id", return_value=_user(None)),
        patch("app.bot.handlers.team.session_factory", return_value=_cm(mock_session)),
    ):
        await mygroup_handler(message)

    assert "нет назначенной группы" in message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_mygroup_mentor_owned_fallback() -> None:
    """Mentor without personal group sees the group they own."""
    message = AsyncMock()
    message.from_user.id = 123
    message.answer = AsyncMock()

    group = Group(id=uuid4(), name="Кураторская", type="curator", max_members=10)
    res_group = MagicMock()
    res_group.scalar_one_or_none.return_value = group
    res_members = MagicMock()
    res_members.scalars.return_value.all.return_value = []
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[res_group, res_members])

    with (
        patch(
            "app.bot.handlers.team.get_user_by_telegram_id",
            return_value=_user(None, role="curator"),
        ),
        patch("app.bot.handlers.team.session_factory", return_value=_cm(mock_session)),
    ):
        await mygroup_handler(message)

    assert "Кураторская" in message.answer.call_args[0][0]
