"""Seed archetype quiz config (intro, questions, results, scores) into settings.

Run: docker compose run --rm bot python -m scripts.seed_quiz_config
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select

from app.bot.services.archetype import (
    DEFAULT_ARCHETYPE_SCORES,
    DEFAULT_INTRO,
    DEFAULT_QUESTIONS,
    DEFAULT_RESULTS,
)
from app.shared.database import session_factory
from app.shared.models.settings import Setting


async def _upsert(session, key: str, value: str) -> str:
    """Insert or update a setting, return 'inserted' or 'updated'."""
    result = await session.execute(select(Setting).where(Setting.key == key))
    existing = result.scalar_one_or_none()
    if existing:
        existing.value = value
        return "updated"
    session.add(Setting(key=key, value=value))
    return "inserted"


async def seed_quiz_config() -> None:
    """Write quiz config settings from code defaults."""
    questions = [
        {"text": q.text, "options": q.options} for q in DEFAULT_QUESTIONS
    ]
    scores = {str(k): v for k, v in DEFAULT_ARCHETYPE_SCORES.items()}
    payload = {
        "quiz_intro": DEFAULT_INTRO,
        "quiz_questions": json.dumps(questions, ensure_ascii=False),
        "quiz_results": json.dumps(DEFAULT_RESULTS, ensure_ascii=False),
        "archetype_scores": json.dumps(scores, ensure_ascii=False),
    }

    async with session_factory() as session:
        for key, value in payload.items():
            action = await _upsert(session, key, value)
            print(f"{action}: {key} ({len(value)} chars)")
        await session.commit()
    print("Quiz config seeded!")


if __name__ == "__main__":
    asyncio.run(seed_quiz_config())
