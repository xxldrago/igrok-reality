"""Tests for quest streams (cohorts 30-50), next-day start, emulate toggle."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services import stream_service as stream_mod


def _session_cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _one(value):
    """Result mock: scalar_one_or_none() -> value, scalar() -> value."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar.return_value = value
    r.scalars.return_value.all.return_value = []
    return r


def _scalar(value):
    return _one(value)


class TestStreamSettings:
    @pytest.mark.asyncio
    async def test_sizes_defaults(self) -> None:
        with patch.object(
            stream_mod, "get_setting", new_callable=AsyncMock, return_value=""
        ):
            assert await stream_mod.get_stream_sizes() == (30, 50)

    @pytest.mark.asyncio
    async def test_emulate_defaults_off(self) -> None:
        with patch.object(
            stream_mod, "get_setting", new_callable=AsyncMock, return_value=""
        ):
            assert await stream_mod.get_emulate_full_group() is False

    @pytest.mark.asyncio
    async def test_emulate_on(self) -> None:
        with patch.object(
            stream_mod, "get_setting", new_callable=AsyncMock, return_value="true"
        ):
            assert await stream_mod.get_emulate_full_group() is True

    def test_next_midnight(self) -> None:
        now = datetime(2026, 9, 20, 15, 30, tzinfo=timezone.utc)
        start = stream_mod.next_midnight(now)
        assert start.tzinfo is not None
        assert (start - now).total_seconds() > 0
        assert (start - now).total_seconds() <= 24 * 3600


def _row(*, one=None, scalar=None, all_rows=None):
    """Result mock with independent scalar_one_or_none/scalar/scalars().all()."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = one
    r.scalar.return_value = scalar
    r.scalars.return_value.all.return_value = all_rows if all_rows is not None else []
    return r


class TestAssignAndLaunch:
    def _user(self, paid=True):
        user = MagicMock()
        user.id = uuid4()
        user.paid_at = (
            datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc) if paid else None
        )
        user.stream_id = None
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

    @pytest.mark.asyncio
    async def test_launch_at_threshold(self) -> None:
        """30th paid member launches the stream; clock starts next midnight."""
        from app.shared.models.stream import Stream

        user = self._user()
        stream = Stream(number=1, status="gathering")
        stream.id = uuid4()

        mock_session = self._session(
            [
                _row(one=user),  # user lookup
                _row(one=stream),  # gathering stream found
                _row(scalar=10),  # member count < max
                _row(scalar=30),  # paid count >= min → launch
                _row(all_rows=[user]),  # launch members
                _row(one=None),  # no commands → set started_at
            ]
        )

        with (
            patch.object(
                stream_mod, "session_factory", return_value=_session_cm(mock_session)
            ),
            patch.object(
                stream_mod, "get_setting", new_callable=AsyncMock, return_value=""
            ),
        ):
            out = await stream_mod.assign_user_to_stream(user.id)

        assert out is stream
        assert stream.status == "launched"
        assert stream.launched_at is not None
        assert user.stream_id == stream.id
        assert user.started_at is not None
        # Next midnight, not now
        assert user.started_at > datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_no_launch_below_threshold(self) -> None:
        """29 paid members: stream stays gathering, no clock."""
        from app.shared.models.stream import Stream

        user = self._user()
        stream = Stream(number=1, status="gathering")
        stream.id = uuid4()

        mock_session = self._session(
            [
                _row(one=user),
                _row(one=stream),
                _row(scalar=10),
                _row(scalar=29),  # below min
            ]
        )

        with (
            patch.object(
                stream_mod, "session_factory", return_value=_session_cm(mock_session)
            ),
            patch.object(
                stream_mod, "get_setting", new_callable=AsyncMock, return_value=""
            ),
        ):
            out = await stream_mod.assign_user_to_stream(user.id)

        assert out is stream
        assert stream.status == "gathering"
        assert user.started_at is None

    @pytest.mark.asyncio
    async def test_emulate_launches_early(self) -> None:
        """Emulate toggle launches with a single paid member."""
        from app.shared.models.stream import Stream

        user = self._user()
        stream = Stream(number=2, status="gathering")
        stream.id = uuid4()

        async def fake_get_setting(key: str, default: str = "") -> str:
            return "true" if key == "emulate_full_group" else ""

        mock_session = self._session(
            [
                _row(one=user),
                _row(one=stream),
                _row(scalar=1),
                _row(scalar=1),  # only 1 paid, but emulate is on
                _row(all_rows=[user]),
                _row(one=None),
            ]
        )

        with (
            patch.object(
                stream_mod, "session_factory", return_value=_session_cm(mock_session)
            ),
            patch.object(
                stream_mod, "get_setting", new_callable=AsyncMock, side_effect=fake_get_setting
            ),
        ):
            out = await stream_mod.assign_user_to_stream(user.id)

        assert out is stream
        assert stream.status == "launched"

    @pytest.mark.asyncio
    async def test_full_stream_opens_new_one(self) -> None:
        """Member count at max → old stream closed, new gathering opened."""
        from app.shared.models.stream import Stream

        user = self._user()
        full = Stream(number=1, status="gathering")
        full.id = uuid4()

        mock_session = self._session(
            [
                _row(one=user),
                _row(one=full),
                _row(scalar=50),  # at max → close + new
                _row(scalar=1),  # current max number
                _row(scalar=0),  # paid in new stream
            ]
        )
        added = []
        mock_session.add = MagicMock(side_effect=lambda o: added.append(o))

        with (
            patch.object(
                stream_mod, "session_factory", return_value=_session_cm(mock_session)
            ),
            patch.object(
                stream_mod, "get_setting", new_callable=AsyncMock, return_value=""
            ),
        ):
            out = await stream_mod.assign_user_to_stream(user.id)

        assert full.status == "closed"
        assert out is not full
        assert out.number == 2
        assert out.status == "gathering"
        assert user.stream_id == out.id
