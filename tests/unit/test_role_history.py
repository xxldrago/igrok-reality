"""Tests for role history service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.bot.services.role_service import (
    change_role,
    get_role_history,
    is_valid_role,
    VALID_ROLES,
)
from app.shared.models.role_history import RoleHistory
from app.shared.models.user import User


def test_is_valid_role() -> None:
    """is_valid_role checks against VALID_ROLES."""
    assert is_valid_role("player")
    assert is_valid_role("curator")
    assert is_valid_role("leader")
    assert is_valid_role("specialist")
    assert is_valid_role("master")
    assert not is_valid_role("invalid")
    assert VALID_ROLES == frozenset({"player", "curator", "leader", "specialist", "master"})


@pytest.mark.asyncio
async def test_change_role_records_history() -> None:
    """change_role updates user.role and creates RoleHistory entry."""
    user_id = uuid4()
    old_role = "player"
    new_role = "curator"
    changed_by = uuid4()

    user = User(id=user_id, telegram_id=123456, first_name="Test", role=old_role)

    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)
    session.execute.return_value = user_result

    import app.bot.services.role_service as rs
    original_factory = rs.session_factory
    rs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        result = await change_role(user_id, new_role, changed_by)

        assert result is True
        assert user.role == new_role
        session.add.assert_called_once()
        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, RoleHistory)
        assert added_obj.user_id == user_id
        assert added_obj.old_role == old_role
        assert added_obj.new_role == new_role
        assert added_obj.changed_by_id == changed_by
        session.commit.assert_called_once()
    finally:
        rs.session_factory = original_factory


@pytest.mark.asyncio
async def test_change_role_no_change_when_same() -> None:
    """change_role returns True without writing history if role unchanged."""
    user_id = uuid4()
    user = User(id=user_id, telegram_id=123456, first_name="Test", role="curator")

    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)
    session.execute.return_value = user_result

    import app.bot.services.role_service as rs
    original_factory = rs.session_factory
    rs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        result = await change_role(user_id, "curator")

        assert result is True
        session.add.assert_not_called()
        session.commit.assert_not_called()  # No commit when no change
    finally:
        rs.session_factory = original_factory


@pytest.mark.asyncio
async def test_change_role_rejects_invalid_role() -> None:
    """change_role returns False for invalid role."""
    user_id = uuid4()
    user = User(id=user_id, telegram_id=123456, first_name="Test", role="player")

    session = AsyncMock()
    session.execute = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)
    session.execute.return_value = user_result

    import app.bot.services.role_service as rs
    original_factory = rs.session_factory
    rs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        result = await change_role(user_id, "invalid_role")
        assert result is False
    finally:
        rs.session_factory = original_factory


@pytest.mark.asyncio
async def test_get_role_history_returns_sorted() -> None:
    """get_role_history returns history entries ordered newest first."""
    user_id = uuid4()
    history1 = RoleHistory(id=uuid4(), user_id=user_id, old_role="player", new_role="curator")
    history2 = RoleHistory(id=uuid4(), user_id=user_id, old_role="curator", new_role="leader")

    session = AsyncMock()
    session.execute = AsyncMock()
    result = MagicMock()
    result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[history1, history2])))
    session.execute.return_value = result

    import app.bot.services.role_service as rs
    original_factory = rs.session_factory
    rs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        history = await get_role_history(user_id)
        assert len(history) == 2
    finally:
        rs.session_factory = original_factory