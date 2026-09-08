"""Tests for group model and service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.bot.services.group_service import (
    Group,
    GroupMember,
    get_user_group,
    get_group_members,
    create_group,
    assign_user_to_group,
)
from app.shared.models.user import User


@pytest.mark.asyncio
async def test_get_group_members_returns_members() -> None:
    """get_group_members returns member stats from users.group_id."""
    group_id = uuid4()
    user1_id = uuid4()
    user2_id = uuid4()

    user1 = User(
        id=user1_id,
        telegram_id=123456,
        first_name="Alice",
        username="alice",
        streak=5,
        is_active=True,
        group_id=group_id,
    )
    user2 = User(
        id=user2_id,
        telegram_id=789012,
        first_name="Bob",
        username=None,
        streak=3,
        is_active=False,
        group_id=group_id,
    )

    session = AsyncMock()
    session.execute = AsyncMock()
    result = MagicMock()
    result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[user1, user2])))
    session.execute.return_value = result

    import app.bot.services.group_service as gs
    original_factory = gs.session_factory
    gs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        members = await get_group_members(group_id)

        assert len(members) == 2
        assert members[0].first_name == "Alice"
        assert members[0].username == "alice"
        assert members[0].streak == 5
        assert members[0].is_active is True
        assert members[1].first_name == "Bob"
        assert members[1].username is None
        assert members[1].streak == 3
        assert members[1].is_active is False
    finally:
        gs.session_factory = original_factory


@pytest.mark.asyncio
async def test_assign_user_to_group_respects_capacity() -> None:
    """assign_user_to_group returns False when group is full."""
    group_id = uuid4()
    user_id = uuid4()

    group = Group(id=group_id, owner_id=uuid4(), type="curator", name="Test", max_members=1)
    user = User(id=user_id, telegram_id=123456, first_name="Test")

    session = AsyncMock()
    session.execute = AsyncMock()

    # First call: group query
    group_result = MagicMock()
    group_result.scalar_one_or_none = MagicMock(return_value=group)

    # Second call: count query
    count_result = MagicMock()
    count_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[User(id=uuid4())])))

    # Third call: user query
    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)

    session.execute.side_effect = [group_result, count_result, user_result]

    import app.bot.services.group_service as gs
    original_factory = gs.session_factory
    gs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        result = await assign_user_to_group(user_id, group_id)
        assert result is False  # Group is full (max=1, already 1 member)
    finally:
        gs.session_factory = original_factory


@pytest.mark.asyncio
async def test_create_group_sets_owner_group_id() -> None:
    """create_group creates group and sets owner's group_id."""
    owner_id = uuid4()
    owner = User(id=owner_id, telegram_id=123456, first_name="Owner")

    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    # User query for owner
    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=owner)
    session.execute.return_value = user_result

    import app.bot.services.group_service as gs
    original_factory = gs.session_factory
    gs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        group = await create_group(owner_id, "curator", "Test Group", 10)

        assert group.type == "curator"
        assert group.name == "Test Group"
        assert group.max_members == 10
        session.flush.assert_called_once()
        session.commit.assert_called_once()
        # Owner's group_id should be set
        assert owner.group_id == group.id
    finally:
        gs.session_factory = original_factory