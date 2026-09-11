"""Lock scroll seed coverage — codes in sync, full 90-day schedule (no DB)."""

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root (scripts pkg)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts.seed_daily_scrolls import TEMPLATES  # noqa: E402
from scripts.seed_scroll_types import SCROLL_TYPES  # noqa: E402
from app.bot.services.day_type import get_available_scroll_codes  # noqa: E402


def test_codes_in_sync() -> None:
    """Type codes, content templates and schedule codes must match exactly."""
    type_codes = {t["code"] for t in SCROLL_TYPES}
    assert len(type_codes) == 9
    assert set(TEMPLATES) == type_codes

    used: set[str] = set()
    for day in range(1, 91):
        used.update(get_available_scroll_codes(day))
    assert used <= type_codes, f"schedule uses unknown codes: {used - type_codes}"


def test_full_schedule_coverage() -> None:
    """Every day 1-90 has scrolls; totals locked: 65x8 + 13x9 + 12x2 = 661."""
    sizes = collections.Counter()
    total = 0
    for day in range(1, 91):
        codes = get_available_scroll_codes(day)
        assert len(codes) > 0, f"day {day} has no scrolls"
        assert len(codes) == len(set(codes)), f"day {day} has duplicates"
        sizes[len(codes)] += 1
        total += len(codes)

    assert sizes == {8: 65, 9: 13, 2: 12}, f"unexpected day mix: {dict(sizes)}"
    assert total == 661, f"unexpected total: {total}"


def test_awareness_days_are_reduced_by_design() -> None:
    """Awareness days (6, 13, ...) intentionally have only zrya + otchet."""
    assert get_available_scroll_codes(6) == ["zrya", "otchet"]
    assert get_available_scroll_codes(13) == ["zrya", "otchet"]
