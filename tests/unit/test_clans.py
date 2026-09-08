"""Tests for clan service and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.bot.services.clan_service import (
    create_clan,
    join_clan,
    leave_clan,
    get_clan_members,
    get_clan_progress,
    get_user_clan,
    ClanProgress,
)
from app.shared.models.clan import Clan, ClanMember
from app.shared.models.user import User


@pytest.mark.asyncio
async def test_create_clan_sets_owner_clan_id() -> None:
    """create_clan creates clan and sets owner's clan_id."""
    owner_id = uuid4()
    owner = User(id=owner_id, telegram_id=123456, first_name="Leader")

    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=owner)
    session.execute.return_value = user_result

    import app.bot.services.clan_service as cs
    original_factory = cs.session_factory
    cs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        clan = await create_clan(owner_id, "Test Clan")

        assert clan.name == "Test Clan"
        assert clan.owner_id == owner_id
        session.flush.assert_called_once()
        session.commit.assert_called_once()
        # Owner's clan_id should be set
        assert owner.clan_id == clan.id
    finally:
        cs.session_factory = original_factory


@pytest.mark.asyncio
async def test_join_clan_adds_member() -> None:
    """join_clan adds user to clan and sets user.clan_id."""
    user_id = uuid4()
    clan_id = uuid4()
    user = User(id=user_id, telegram_id=123456, first_name="Member", clan_id=None)
    clan = Clan(id=clan_id, owner_id=uuid4(), name="Test Clan")

    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    # First call: clan query
    clan_result = MagicMock()
    clan_result.scalar_one_or_none = MagicMock(return_value=clan)

    # Second call: user query
    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)

    session.execute.side_effect = [clan_result, user_result]

    import app.bot.services.clan_service as cs
    original_factory = cs.session_factory
    cs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        result = await join_clan(user_id, clan_id)

        assert result is True
        assert user.clan_id == clan_id
        session.add.assert_called_once()
        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, ClanMember)
        assert added_obj.user_id == user_id
        assert added_obj.clan_id == clan_id
        session.commit.assert_called_once()
    finally:
        cs.session_factory = original_factory


@pytest.mark.asyncio
async def test_join_clan_fails_if_already_in_clan() -> None:
    """join_clan returns False if user already has clan_id."""
    user_id = uuid4()
    clan_id = uuid4()
    user = User(id=user_id, telegram_id=123456, first_name="Member", clan_id=uuid4())
    clan = Clan(id=clan_id, owner_id=uuid4(), name="Test Clan")

    session = AsyncMock()
    session.execute = AsyncMock()

    clan_result = MagicMock()
    clan_result.scalar_one_or_none = MagicMock(return_value=clan)

    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)

    session.execute.side_effect = [clan_result, user_result]

    import app.bot.services.clan_service as cs
    original_factory = cs.session_factory
    cs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        result = await join_clan(user_id, clan_id)
        assert result is False
    finally:
        cs.session_factory = original_factory


@pytest.mark.asyncio
async def test_get_clan_progress_calculates_aggregates() -> None:
    """get_clan_progress returns correct aggregate metrics."""
    clan_id = uuid4()
    clan = Clan(id=clan_id, owner_id=uuid4(), name="Test Clan")

    member1 = User(id=uuid4(), telegram_id=1, first_name="A", xp=100, streak=5, clan_id=clan_id)
    member2 = User(id=uuid4(), telegram_id=2, first_name="B", xp=200, streak=10, clan_id=clan_id)

    session = AsyncMock()
    session.execute = AsyncMock()

    clan_result = MagicMock()
    clan_result.scalar_one_or_none = MagicMock(return_value=clan)

    members_result = MagicMock()
    members_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[member1, member2])))

    session.execute.side_effect = [clan_result, members_result]

    import app.bot.services.clan_service as cs
    original_factory = cs.session_factory
    cs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        progress = await get_clan_progress(clan_id)

        assert progress.clan_id == clan_id
        assert progress.clan_name == "Test Clan"
        assert progress.member_count == 2
        assert progress.total_xp == 300
        assert progress.avg_xp == 150.0
        assert progress.total_streak == 15
        assert progress.avg_streak == 7.5
    finally:
        cs.session_factory = original_factory


@pytest.mark.asyncio
async def test_get_user_clan_returns_clan() -> None:
    """get_user_clan returns the clan the user belongs to."""
    user_id = uuid4()
    clan_id = uuid4()
    user = User(id=user_id, telegram_id=123456, first_name="Test", clan_id=clan_id)
    clan = Clan(id=clan_id, owner_id=uuid4(), name="Test Clan")

    session = AsyncMock()
    session.execute = AsyncMock()

    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)

    clan_result = MagicMock()
    clan_result.scalar_one_or_none = MagicMock(return_value=clan)

    session.execute.side_effect = [user_result, clan_result]

    import app.bot.services.clan_service as cs
    original_factory = cs.session_factory
    cs.session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=session),
        __aexit__=AsyncMock(return_value=None),
    )

    try:
        result = await get_user_clan(user_id)
        assert result is not None
        assert result.id == clan_id
    finally:
        cs.session_factory = original_factory