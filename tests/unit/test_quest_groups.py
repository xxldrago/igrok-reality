"""Tests for quest group gathering (auto cohorts 30-50), next-day start, emulate toggle."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services import quest_group_service as qg_mod


def _session_cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _row(*, one=None, scalar=None, all_rows=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = one
    r.scalar.return_value = scalar
    rows = all_rows if all_rows is not None else []
    r.scalars.return_value.all.return_value = rows
    r.all.return_value = rows
    return r


class TestGroupSettings:
    @pytest.mark.asyncio
    async def test_sizes_defaults(self) -> None:
        with patch.object(
            qg_mod, "get_setting", new_callable=AsyncMock, return_value=""
        ):
            assert await qg_mod.get_group_sizes() == (30, 50)

    @pytest.mark.asyncio
    async def test_emulate_defaults_off(self) -> None:
        with patch.object(
            qg_mod, "get_setting", new_callable=AsyncMock, return_value=""
        ):
            assert await qg_mod.get_emulate_full_group() is False

    @pytest.mark.asyncio
    async def test_emulate_on(self) -> None:
        with patch.object(
            qg_mod, "get_setting", new_callable=AsyncMock, return_value="true"
        ):
            assert await qg_mod.get_emulate_full_group() is True

    def test_next_midnight(self) -> None:
        now = datetime(2026, 9, 20, 15, 30, tzinfo=timezone.utc)
        start = qg_mod.next_midnight(now)
        assert start.tzinfo is not None
        assert start > now
        assert (start - now).total_seconds() <= 24 * 3600


class TestAssignAndLaunch:
    def _user(self, paid=True):
        user = MagicMock()
        user.id = uuid4()
        user.paid_at = (
            datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc) if paid else None
        )
        user.group_id = None
        user.started_at = None
        return user

    def _session(self, results):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=list(results))
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        return mock_session

    def _group(self, name="Группа №1"):
        from app.shared.models.group import Group

        group = Group(name=name, type="quest", owner_id=None, max_members=50)
        group.id = uuid4()
        return group

    @pytest.mark.asyncio
    async def test_launch_at_threshold(self) -> None:
        """30th paid member launches the group; clock starts next midnight."""
        user = self._user()
        group = self._group()

        mock_session = self._session(
            [
                _row(one=user),  # user lookup
                _row(one=group),  # gathering group found
                _row(scalar=10),  # member count < max
                _row(scalar=30),  # paid count >= min → launch
                _row(all_rows=[user]),  # launch members
                _row(one=None),  # no commands → set started_at
            ]
        )

        with (
            patch.object(
                qg_mod, "session_factory", return_value=_session_cm(mock_session)
            ),
            patch.object(
                qg_mod, "get_setting", new_callable=AsyncMock, return_value=""
            ),
        ):
            out = await qg_mod.assign_user_to_group(user.id)

        assert out is group
        assert group.launched_at is not None
        assert user.group_id == group.id
        assert user.started_at is not None
        assert user.started_at > datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_no_launch_below_threshold(self) -> None:
        """29 paid members: group stays gathering, no clock."""
        user = self._user()
        group = self._group()

        mock_session = self._session(
            [
                _row(one=user),
                _row(one=group),
                _row(scalar=10),
                _row(scalar=29),  # below min
            ]
        )

        with (
            patch.object(
                qg_mod, "session_factory", return_value=_session_cm(mock_session)
            ),
            patch.object(
                qg_mod, "get_setting", new_callable=AsyncMock, return_value=""
            ),
        ):
            out = await qg_mod.assign_user_to_group(user.id)

        assert out is group
        assert group.launched_at is None
        assert user.started_at is None

    @pytest.mark.asyncio
    async def test_emulate_launches_early(self) -> None:
        """Emulate toggle launches with a single paid member."""
        user = self._user()
        group = self._group("Группа №2")

        async def fake_get_setting(key: str, default: str = "") -> str:
            return "true" if key == "emulate_full_group" else ""

        mock_session = self._session(
            [
                _row(one=user),
                _row(one=group),
                _row(scalar=1),
                _row(scalar=1),  # only 1 paid, but emulate is on
                _row(all_rows=[user]),
                _row(one=None),
            ]
        )

        with (
            patch.object(
                qg_mod, "session_factory", return_value=_session_cm(mock_session)
            ),
            patch.object(
                qg_mod, "get_setting", new_callable=AsyncMock, side_effect=fake_get_setting
            ),
        ):
            out = await qg_mod.assign_user_to_group(user.id)

        assert out is group
        assert group.launched_at is not None

    @pytest.mark.asyncio
    async def test_full_group_opens_new_one(self) -> None:
        """Member count at max → new gathering group opened."""
        user = self._user()
        full = self._group("Группа №1")

        mock_session = self._session(
            [
                _row(one=user),
                _row(one=full),
                _row(scalar=50),  # at max → new group
                _row(all_rows=[]),  # existing quest names (none numbered)
                _row(scalar=0),  # paid in new group
            ]
        )
        added = []
        mock_session.add = MagicMock(side_effect=lambda o: added.append(o))

        with (
            patch.object(
                qg_mod, "session_factory", return_value=_session_cm(mock_session)
            ),
            patch.object(
                qg_mod, "get_setting", new_callable=AsyncMock, return_value=""
            ),
        ):
            out = await qg_mod.assign_user_to_group(user.id)

        assert out is not full
        assert out.name == "Группа №1"
        assert out.type == "quest"
        assert user.group_id == out.id
