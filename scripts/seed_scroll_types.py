"""Seed script for scroll_types table — populates the 9 scroll types.

Run: python -m scripts.seed_scroll_types
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.shared.database import session_factory
from app.shared.models.scroll_type import ScrollType


SCROLL_TYPES = [
    {
        "code": "rassvet",
        "name": "Свиток Рассвета",
        "command": "/wakeup",
        "hour": 5,
        "minute": 0,
        "xp_reward": 5,
        "description": "Утренние потягушки + рекомендация (вода с лимоном)",
        "requires_meditation": False,
        "is_breathing_day_only": False,
        "is_awareness_day_only": False,
        "sort_order": 1,
    },
    {
        "code": "ogne",
        "name": "Свиток Огня",
        "command": "/cold",
        "hour": 5,
        "minute": 5,
        "xp_reward": 5,
        "description": "Душ + самомассаж (контрастный душ)",
        "requires_meditation": False,
        "is_breathing_day_only": False,
        "is_awareness_day_only": False,
        "sort_order": 2,
    },
    {
        "code": "korni",
        "name": "Свиток Корней",
        "command": "/scan",
        "hour": 5,
        "minute": 10,
        "xp_reward": 5,
        "description": "Медитация (аудиогид) + вопрос недели",
        "requires_meditation": True,
        "is_breathing_day_only": False,
        "is_awareness_day_only": False,
        "sort_order": 3,
    },
    {
        "code": "vetr",
        "name": "Свиток Ветра",
        "command": "/breath",
        "hour": 8,
        "minute": 0,
        "xp_reward": 5,
        "description": "Дыхательная практика (3–5 минут)",
        "requires_meditation": False,
        "is_breathing_day_only": False,
        "is_awareness_day_only": False,
        "sort_order": 4,
    },
    {
        "code": "sledy",
        "name": "Свиток Следов",
        "command": "/micro",
        "hour": 12,
        "minute": 0,
        "xp_reward": 3,
        "description": "Микро-привычка (встраивание в быт)",
        "requires_meditation": False,
        "is_breathing_day_only": False,
        "is_awareness_day_only": False,
        "sort_order": 5,
    },
    {
        "code": "zrya",
        "name": "Свиток Зря",
        "command": "/focus",
        "hour": 16,
        "minute": 0,
        "xp_reward": 3,
        "description": "Теория дня (короткая вставка)",
        "requires_meditation": False,
        "is_breathing_day_only": False,
        "is_awareness_day_only": False,
        "sort_order": 6,
    },
    {
        "code": "pitaniye",
        "name": "Свиток Питания",
        "command": "/food",
        "hour": 16,
        "minute": 5,
        "xp_reward": 3,
        "description": "Рекомендации по питанию",
        "requires_meditation": False,
        "is_breathing_day_only": False,
        "is_awareness_day_only": False,
        "sort_order": 7,
    },
    {
        "code": "integratsiya",
        "name": "Интеграция Истока",
        "command": "/sleep",
        "hour": 21,
        "minute": 0,
        "xp_reward": 5,
        "description": "Ночная практика (перед сном)",
        "requires_meditation": False,
        "is_breathing_day_only": False,
        "is_awareness_day_only": False,
        "sort_order": 8,
    },
    {
        "code": "otchet",
        "name": "Отчёт о дне",
        "command": "/report",
        "hour": -1,  # Any time
        "minute": 0,
        "xp_reward": 2,
        "description": "Краткое сохранение дня",
        "requires_meditation": False,
        "is_breathing_day_only": False,
        "is_awareness_day_only": False,
        "sort_order": 9,
    },
]


async def seed_scroll_types() -> None:
    """Insert scroll types into the database."""
    async with session_factory() as session:
        for data in SCROLL_TYPES:
            # Check if already exists
            from sqlalchemy import select
            result = await session.execute(
                select(ScrollType).where(ScrollType.code == data["code"])
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                scroll_type = ScrollType(**data)
                session.add(scroll_type)
                print(f"  + {data['code']}: {data['name']} ({data['command']})")
            else:
                print(f"  = {data['code']}: already exists")

        await session.commit()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(seed_scroll_types())
