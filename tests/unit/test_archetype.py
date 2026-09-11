"""Tests for archetype scoring logic."""

import sys
import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path

# Ensure src is on path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.archetype import (
    ARCHETYPE_NAMES,
    DEFAULT_ARCHETYPE_SCORES,
    DEFAULT_INTRO,
    DEFAULT_QUESTIONS,
    DEFAULT_RESULTS,
    calculate_archetype,
    load_quiz_config,
)


def _make_answers(*letters: str) -> dict:
    """Build FSMContext-style data dict from answer letters."""
    return {f"q{i+1}_answer": letter for i, letter in enumerate(letters)}


class TestCalculateArchetype:
    """Tests for calculate_archetype scoring function."""

    @pytest.mark.asyncio
    async def test_all_head_answers(self) -> None:
        """All 'a' answers should produce 'head' archetype."""
        data = _make_answers("a", "a", "a", "a")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {
                1: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                2: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                3: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                4: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
            }
            assert await calculate_archetype(data) == "head"

    @pytest.mark.asyncio
    async def test_all_whirlwind_answers(self) -> None:
        """All 'b' answers should produce 'whirlwind' archetype."""
        data = _make_answers("b", "b", "b", "b")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {
                1: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                2: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                3: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                4: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
            }
            assert await calculate_archetype(data) == "whirlwind"

    @pytest.mark.asyncio
    async def test_all_shell_answers(self) -> None:
        """All 'c' answers should produce 'shell' archetype."""
        data = _make_answers("c", "c", "c", "c")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {
                1: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                2: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                3: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                4: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
            }
            assert await calculate_archetype(data) == "shell"

    @pytest.mark.asyncio
    async def test_all_ghost_answers(self) -> None:
        """All 'd' answers should produce 'ghost' archetype."""
        data = _make_answers("d", "d", "d", "d")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {
                1: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                2: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                3: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                4: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
            }
            assert await calculate_archetype(data) == "ghost"

    @pytest.mark.asyncio
    async def test_mixed_answers(self) -> None:
        """Mixed answers should pick the highest-scoring archetype."""
        # 3x head (a) + 1x ghost (d) → head wins 6-2
        data = _make_answers("a", "a", "a", "d")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {
                1: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                2: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                3: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
                4: {"a": {"head": 2}, "b": {"whirlwind": 2}, "c": {"shell": 2}, "d": {"ghost": 2}},
            }
            assert await calculate_archetype(data) == "head"

    def test_archetype_names(self) -> None:
        """ARCHETYPE_NAMES maps all 4 internal names to Russian display names."""
        assert ARCHETYPE_NAMES["head"] == "Голова"
        assert ARCHETYPE_NAMES["shell"] == "Панцирь"
        assert ARCHETYPE_NAMES["whirlwind"] == "Вихрь"
        assert ARCHETYPE_NAMES["ghost"] == "Призрак"
        assert len(ARCHETYPE_NAMES) == 4


CORRECT_SCORES = {
    1: {"a": {"head": 2}, "b": {"shell": 2}, "c": {"whirlwind": 2}, "d": {"ghost": 2}},
    2: {"a": {"head": 2}, "b": {"shell": 2}, "c": {"whirlwind": 2}, "d": {"ghost": 2}},
    3: {"a": {"head": 2}, "b": {"shell": 2}, "c": {"whirlwind": 2}, "d": {"ghost": 2}},
    4: {"a": {"head": 2}, "b": {"shell": 2}, "c": {"whirlwind": 2}, "d": {"ghost": 2}},
}


class TestSpecAlgorithm:
    """Tests for the ORЪ spec algorithm: majority wins, Q1 decides splits."""

    @pytest.mark.asyncio
    async def test_three_of_four_wins(self) -> None:
        """Example from spec: A, A, B, A → Голова (3 of 4)."""
        data = _make_answers("a", "a", "b", "a")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = CORRECT_SCORES
            assert await calculate_archetype(data) == "head"

    @pytest.mark.asyncio
    async def test_tie_two_two_q1_wins(self) -> None:
        """2-2 split → Q1 decides (b,b,a,a → shell, not head)."""
        data = _make_answers("b", "b", "a", "a")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = CORRECT_SCORES
            assert await calculate_archetype(data) == "shell"

    @pytest.mark.asyncio
    async def test_split_all_different_q1_wins(self) -> None:
        """1/1/1/1 split → Q1 decides (d,... → ghost)."""
        data = _make_answers("d", "a", "b", "c")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = CORRECT_SCORES
            assert await calculate_archetype(data) == "ghost"

    @pytest.mark.asyncio
    async def test_full_b_answers_give_shell(self) -> None:
        """All B answers → Панцирь (shell), per spec mapping."""
        data = _make_answers("b", "b", "b", "b")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = CORRECT_SCORES
            assert await calculate_archetype(data) == "shell"

    @pytest.mark.asyncio
    async def test_full_c_answers_give_whirlwind(self) -> None:
        """All C answers → Вихрь (whirlwind), per spec mapping."""
        data = _make_answers("c", "c", "c", "c")
        with patch("app.bot.services.archetype.load_archetype_scores", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = CORRECT_SCORES
            assert await calculate_archetype(data) == "whirlwind"

    @pytest.mark.asyncio
    async def test_default_scores_fallback_mapping(self) -> None:
        """Empty settings → DEFAULT_ARCHETYPE_SCORES with A=head,B=shell,C=whirlwind,D=ghost."""
        with patch("app.bot.services.archetype.get_setting", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = ""
            assert await calculate_archetype(_make_answers("b", "b", "b", "b")) == "shell"
            assert await calculate_archetype(_make_answers("c", "c", "c", "c")) == "whirlwind"

    def test_default_scores_map_letters_correctly(self) -> None:
        """Lock the spec letter mapping in DEFAULT_ARCHETYPE_SCORES."""
        for q in (1, 2, 3, 4):
            assert list(DEFAULT_ARCHETYPE_SCORES[q]["a"]) == ["head"]
            assert list(DEFAULT_ARCHETYPE_SCORES[q]["b"]) == ["shell"]
            assert list(DEFAULT_ARCHETYPE_SCORES[q]["c"]) == ["whirlwind"]
            assert list(DEFAULT_ARCHETYPE_SCORES[q]["d"]) == ["ghost"]


class TestQuizConfigFallback:
    """load_quiz_config must never return empty questions/results."""

    @pytest.mark.asyncio
    async def test_empty_settings_give_defaults(self) -> None:
        """Missing settings → DEFAULT_INTRO / DEFAULT_QUESTIONS / DEFAULT_RESULTS."""
        with patch("app.bot.services.archetype.get_setting", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = ""
            quiz = await load_quiz_config()
            assert quiz.intro == DEFAULT_INTRO
            assert len(quiz.questions) == 4
            assert len(quiz.results) == 4
            assert set(quiz.results) == {"head", "shell", "whirlwind", "ghost"}

    @pytest.mark.asyncio
    async def test_default_questions_match_spec(self) -> None:
        """Default questions carry spec headers and 4 options each."""
        assert DEFAULT_QUESTIONS[0].text.startswith("ВОПРОС 1.")
        assert DEFAULT_QUESTIONS[1].text.startswith("ВОПРОС 2.")
        assert DEFAULT_QUESTIONS[2].text.startswith("ВОПРОС 3.")
        assert DEFAULT_QUESTIONS[3].text.startswith("ВОПРОС 4.")
        for q in DEFAULT_QUESTIONS:
            assert [o["key"] for o in q.options] == ["a", "b", "c", "d"]

    @pytest.mark.asyncio
    async def test_default_results_have_all_archetypes(self) -> None:
        """Each default result contains its archetype header."""
        assert "ГОЛОВА" in DEFAULT_RESULTS["head"]
        assert "ПАНЦИРЬ" in DEFAULT_RESULTS["shell"]
        assert "ВИХРЬ" in DEFAULT_RESULTS["whirlwind"]
        assert "ПРИЗРАК" in DEFAULT_RESULTS["ghost"]
