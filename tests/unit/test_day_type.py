"""Tests for day type determination and grace period logic."""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.bot.services.day_type import (
    COMMAND_TO_SCROLL_CODE,
    get_day_type,
    get_available_scroll_codes,
    MEDITATION_DAYS,
    BREATHING_DAYS,
    AWARENESS_DAYS,
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
