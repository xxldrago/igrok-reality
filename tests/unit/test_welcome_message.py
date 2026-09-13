"""Tests for ORЪ default texts: welcome message chunking and quiz defaults."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.handlers.registration import split_message
from app.bot.services.archetype import (
    DEFAULT_ARCHETYPE_SCORES,
    DEFAULT_INTRO,
    DEFAULT_QUESTIONS,
    DEFAULT_RESULTS,
)
from app.bot.services.settings_service import DEFAULT_WELCOME_MESSAGE


class TestWelcomeMessage:
    def test_contains_key_markers(self) -> None:
        assert "ОРЪ" in DEFAULT_WELCOME_MESSAGE
        assert "Начни сегодня." in DEFAULT_WELCOME_MESSAGE
        assert "ТРИ ТРИЛОГИИ" in DEFAULT_WELCOME_MESSAGE

    def test_chunks_fit_telegram_limit(self) -> None:
        chunks = split_message(DEFAULT_WELCOME_MESSAGE)
        assert len(chunks) >= 2  # 5291 chars > 4096 limit
        assert all(len(c) <= 4000 for c in chunks)

    def test_split_short_text_passthrough(self) -> None:
        assert split_message("hello") == ["hello"]

    def test_split_preserves_content(self) -> None:
        text = "para one\n\npara two\n\npara three"
        chunks = split_message(text, limit=20)
        assert all(len(c) <= 20 for c in chunks)
        assert "\n\n".join(chunks) == text


class TestQuizDefaults:
    def test_intro_matches_spec(self) -> None:
        assert "ПРЕЖДЕ ЧЕМ ТЫ ПОЛУЧИШЬ СВОЙ ПЕРВЫЙ СВИТОК" in DEFAULT_INTRO
        assert "Начинаем..." in DEFAULT_INTRO

    def test_four_questions_with_abcd(self) -> None:
        assert len(DEFAULT_QUESTIONS) == 4
        for q in DEFAULT_QUESTIONS:
            assert [o["key"] for o in q.options] == ["a", "b", "c", "d"]

    def test_question_headers(self) -> None:
        assert "ВОПРОС 1" in DEFAULT_QUESTIONS[0].text
        assert "ВОПРОС 4" in DEFAULT_QUESTIONS[3].text

    def test_results_all_archetypes(self) -> None:
        assert set(DEFAULT_RESULTS) == {"head", "shell", "whirlwind", "ghost"}
        assert "ТВОЙ АРХЕТИП: ГОЛОВА" in DEFAULT_RESULTS["head"]
        assert "ТВОЙ АРХЕТИП: ПАНЦИРЬ" in DEFAULT_RESULTS["shell"]
        assert "ТВОЙ АРХЕТИП: ВИХРЬ" in DEFAULT_RESULTS["whirlwind"]
        assert "ТВОЙ АРХЕТИП: ПРИЗРАК" in DEFAULT_RESULTS["ghost"]

    def test_scoring_maps_abcd(self) -> None:
        for q in (1, 2, 3, 4):
            assert list(DEFAULT_ARCHETYPE_SCORES[q]["a"]) == ["head"]
            assert list(DEFAULT_ARCHETYPE_SCORES[q]["b"]) == ["shell"]
            assert list(DEFAULT_ARCHETYPE_SCORES[q]["c"]) == ["whirlwind"]
            assert list(DEFAULT_ARCHETYPE_SCORES[q]["d"]) == ["ghost"]
