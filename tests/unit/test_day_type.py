"""Tests for day type determination and grace period logic."""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.bot.services.day_type import (
    get_day_type,
    get_available_scroll_codes,
    get_breathing_slot,
    COMMAND_TO_SCROLL_CODE,
    MEDITATION_DAYS,
    BREATHING_DAYS,
    AWARENESS_DAYS,
    BREATHING_SLOTS,
)


class TestGetDayType:
    def test_day_1_is_meditation(self):
        dt = get_day_type(1)
        assert dt.is_meditation is True
        assert dt.max_xp == 36

    def test_day_2_is_normal(self):
        dt = get_day_type(2)
        assert dt.is_meditation is False
        assert dt.is_breathing is False
        assert dt.is_awareness is False
        assert dt.max_xp == 31

    def test_day_7_is_breathing(self):
        dt = get_day_type(7)
        assert dt.is_breathing is True
        assert dt.max_xp == 20

    def test_day_6_is_awareness(self):
        dt = get_day_type(6)
        assert dt.is_awareness is True
        assert dt.max_xp == 8

    def test_day_8_is_meditation(self):
        dt = get_day_type(8)
        assert dt.is_meditation is True

    def test_meditation_days_set(self):
        assert 1 in MEDITATION_DAYS
        assert 8 in MEDITATION_DAYS
        assert 15 in MEDITATION_DAYS
        assert 85 in MEDITATION_DAYS
        assert 2 not in MEDITATION_DAYS

    def test_breathing_days_set(self):
        assert 7 in BREATHING_DAYS
        assert 14 in BREATHING_DAYS
        assert 84 in BREATHING_DAYS
        assert 1 not in BREATHING_DAYS

    def test_awareness_days_set(self):
        assert 6 in AWARENESS_DAYS
        assert 13 in AWARENESS_DAYS
        assert 83 in AWARENESS_DAYS
        assert 1 not in AWARENESS_DAYS

    def test_day_90_max_xp(self):
        dt = get_day_type(90)
        assert dt.max_xp == 31  # Day 90 is normal (not meditation/breath/awareness)


class TestGetAvailableScrollCodes:
    def test_normal_day(self):
        codes = get_available_scroll_codes(2)
        assert "rassvet" in codes
        assert "ogne" in codes
        assert "vetr" in codes
        assert "sledy" in codes
        assert "zrya" in codes
        assert "pitaniye" in codes
        assert "integratsiya" in codes
        assert "otchet" in codes
        assert "korni" not in codes  # no meditation on day 2

    def test_meditation_day_includes_korni(self):
        codes = get_available_scroll_codes(1)
        assert "korni" in codes

    def test_awareness_day_reduced(self):
        codes = get_available_scroll_codes(6)
        assert set(codes) == {"zrya", "otchet"}

    def test_breathing_day_set(self):
        codes = get_available_scroll_codes(7)
        assert codes == ["vetr", "vetr_day", "vetr_evening", "zrya", "otchet"]


class TestBreathingSlots:
    def test_slot_boundaries(self):
        assert get_breathing_slot(8) == "morning"
        assert get_breathing_slot(11) == "morning"
        assert get_breathing_slot(12) == "day"
        assert get_breathing_slot(14) == "day"
        assert get_breathing_slot(17) == "day"
        assert get_breathing_slot(18) == "evening"
        assert get_breathing_slot(21) == "evening"

    def test_slots_cover_all_codes(self):
        assert [code for _, code in BREATHING_SLOTS] == ["vetr", "vetr_day", "vetr_evening"]

    def test_command_to_scroll_mapping(self):
        assert COMMAND_TO_SCROLL_CODE["/wakeup"] == "rassvet"
        assert COMMAND_TO_SCROLL_CODE["/cold"] == "ogne"
        assert COMMAND_TO_SCROLL_CODE["/scan"] == "korni"
        assert COMMAND_TO_SCROLL_CODE["/scanreport"] == "korni"
        assert COMMAND_TO_SCROLL_CODE["/breath"] == "vetr"
        assert COMMAND_TO_SCROLL_CODE["/micro"] == "sledy"
        assert COMMAND_TO_SCROLL_CODE["/focus"] == "zrya"
        assert COMMAND_TO_SCROLL_CODE["/food"] == "pitaniye"
        assert COMMAND_TO_SCROLL_CODE["/sleep"] == "integratsiya"
        assert COMMAND_TO_SCROLL_CODE["/report"] == "otchet"


class TestBreathingGate:
    """_is_command_allowed on breathing days (spec 3.3)."""

    def _session(self, scroll_type, existing=None):
        from unittest.mock import AsyncMock, MagicMock

        mock_session = AsyncMock()
        res_type = MagicMock()
        res_type.scalar_one_or_none.return_value = scroll_type
        res_dup = MagicMock()
        res_dup.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(side_effect=[res_type, res_dup])
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_session)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    def _scroll_type(self, code: str, breathing_only: bool = False):
        from app.shared.models.scroll_type import ScrollType

        return ScrollType(
            code=code,
            name=code,
            command="/breath" if "vetr" in code else "/x",
            hour=8,
            is_breathing_day_only=breathing_only,
        )

    @pytest.mark.asyncio
    async def test_breathing_day_rejects_wakeup(self):
        from unittest.mock import patch
        from uuid import uuid4
        from app.bot.handlers import daily as daily_mod

        cm = self._session(self._scroll_type("rassvet"))
        with patch.object(daily_mod, "session_factory", return_value=cm):
            allowed, reason = await daily_mod._is_command_allowed(
                uuid4(), 7, "/wakeup", "rassvet"
            )
            assert allowed is False
            assert "дыхания" in reason

    @pytest.mark.asyncio
    async def test_breathing_day_allows_vetr_slots(self):
        from unittest.mock import patch
        from uuid import uuid4
        from app.bot.handlers import daily as daily_mod

        for code, slot in (("vetr", "morning"), ("vetr_day", "day"), ("vetr_evening", "evening")):
            cm = self._session(self._scroll_type(code, breathing_only=(code != "vetr")))
            with patch.object(daily_mod, "session_factory", return_value=cm):
                allowed, _ = await daily_mod._is_command_allowed(
                    uuid4(), 7, "/breath", code, slot=slot
                )
                assert allowed is True, code

    @pytest.mark.asyncio
    async def test_breathing_extra_rejected_off_day(self):
        from unittest.mock import patch
        from uuid import uuid4
        from app.bot.handlers import daily as daily_mod

        cm = self._session(self._scroll_type("vetr_day", breathing_only=True))
        with patch.object(daily_mod, "session_factory", return_value=cm):
            allowed, reason = await daily_mod._is_command_allowed(
                uuid4(), 2, "/breath", "vetr_day", slot="day"
            )
            assert allowed is False
            assert "дыхания" in reason
