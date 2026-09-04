"""Tests for archetype scoring logic."""

import sys
from pathlib import Path

# Ensure src is on path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.archetype import ARCHETYPE_NAMES, calculate_archetype


def _make_answers(*letters: str) -> dict:
    """Build FSMContext-style data dict from answer letters."""
    return {f"q{i+1}_answer": letter for i, letter in enumerate(letters)}


class TestCalculateArchetype:
    """Tests for calculate_archetype scoring function."""

    def test_all_head_answers(self) -> None:
        """All 'a' answers should produce 'head' archetype."""
        data = _make_answers("a", "a", "a", "a")
        assert calculate_archetype(data) == "head"

    def test_all_whirlwind_answers(self) -> None:
        """All 'b' answers should produce 'whirlwind' archetype."""
        data = _make_answers("b", "b", "b", "b")
        assert calculate_archetype(data) == "whirlwind"

    def test_all_shell_answers(self) -> None:
        """All 'c' answers should produce 'shell' archetype."""
        data = _make_answers("c", "c", "c", "c")
        assert calculate_archetype(data) == "shell"

    def test_all_ghost_answers(self) -> None:
        """All 'd' answers should produce 'ghost' archetype."""
        data = _make_answers("d", "d", "d", "d")
        assert calculate_archetype(data) == "ghost"

    def test_mixed_answers(self) -> None:
        """Mixed answers should pick the highest-scoring archetype."""
        # 3x head (a) + 1x ghost (d) → head wins 6-2
        data = _make_answers("a", "a", "a", "d")
        assert calculate_archetype(data) == "head"

    def test_archetype_names(self) -> None:
        """ARCHETYPE_NAMES maps all 4 internal names to Russian display names."""
        assert ARCHETYPE_NAMES["head"] == "Голова"
        assert ARCHETYPE_NAMES["shell"] == "Панцирь"
        assert ARCHETYPE_NAMES["whirlwind"] == "Вихрь"
        assert ARCHETYPE_NAMES["ghost"] == "Призрак"
        assert len(ARCHETYPE_NAMES) == 4
