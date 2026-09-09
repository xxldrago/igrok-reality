"""Tests for daily command handlers — grace period, quest day logic, anti-dup."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.bot.handlers.daily import _get_quest_day


class _FakeUser:
    def __init__(self, started_at):
        self.started_at = started_at


def make_user(days_ago=0):
    """Create a fake user whose started_at is `days_ago` days from now (UTC)."""
    started = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - __import__("datetime").timedelta(days=days_ago)
    return _FakeUser(started_at=started)


class TestGetQuestDay:
    def test_day_1_at_noon(self):
        """Same-day, at 12:00 Moscow — day 1."""
        msk = ZoneInfo("Europe/Moscow")
        user = _FakeUser(
            started_at=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 1, 15, 12, 0, tzinfo=msk)
        day = _get_quest_day(user, "Europe/Moscow", now)
        assert day == 1

    def test_day_5_normal(self):
        """5 days since start, at noon — day 6 (Jan 10 = day 1)."""
        msk = ZoneInfo("Europe/Moscow")
        now = datetime(2026, 1, 15, 12, 0, tzinfo=msk)  # Moscow noon
        user = _FakeUser(
            started_at=datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)
        )
        day = _get_quest_day(user, "Europe/Moscow", now)
        assert day == 6

    def test_grace_period_3am_counts_previous_day(self):
        """3 AM counts as previous day (grace period)."""
        user = _FakeUser(
            started_at=datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)
        )
        # Moscow time 3 AM on 2026-01-15 = UTC 2026-01-14 00:00 (Moscow is UTC+3)
        # 3 AM Moscow on Jan 15 = 00:00 UTC Jan 15
        # Let's use Moscow timezone directly
        msk = ZoneInfo("Europe/Moscow")
        # 3 AM Moscow, Jan 15 2026
        now = datetime(2026, 1, 15, 3, 0, tzinfo=msk)
        # started Jan 10 00:00 UTC = Jan 10 03:00 Moscow
        started_msk = datetime(2026, 1, 10, 3, 0, tzinfo=msk)
        user.started_at = started_msk.astimezone(timezone.utc)
        # Effective date should be Jan 14 (grace period subtracts 1 day)
        # Jan 14 - Jan 10 + 1 = day 5
        day = _get_quest_day(user, "Europe/Moscow", now)
        # started Jan 10, effective Jan 14 -> delta 4, +1 = day 5
        assert day == 5

    def test_no_grace_at_6am(self):
        """6 AM is already the new day (no grace)."""
        user = _FakeUser(
            started_at=datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)
        )
        msk = ZoneInfo("Europe/Moscow")
        now = datetime(2026, 1, 15, 6, 0, tzinfo=msk)
        started_msk = datetime(2026, 1, 10, 3, 0, tzinfo=msk)
        user.started_at = started_msk.astimezone(timezone.utc)
        # Effective date is Jan 15 (6 AM, no grace)
        # Jan 15 - Jan 10 + 1 = day 6
        day = _get_quest_day(user, "Europe/Moscow", now)
        assert day == 6
