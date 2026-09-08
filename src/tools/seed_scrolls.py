"""Seed database with scroll content from scrolls.json.

The JSON holds one entry per day (90 total). Each entry carries the 4 shared
sections (common_task, ritual, habits, micromovements) plus a per-archetype
``archetype_tasks`` map. Seeding is idempotent: scrolls are upserted by
day_number and their archetype tasks are upserted by (scroll, archetype_code).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.archetype import Archetype
from app.shared.models.scroll import Scroll
from app.shared.models.scroll_archetype_task import ScrollArchetypeTask

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SCROLLS_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scrolls.json")

# Canonical archetypes used to ensure the reference table is populated before
# seeding scroll archetype tasks. Kept in sync with the add_archetypes migration.
CANONICAL_ARCHETYPES: dict[str, str] = {
    "head": "Голова",
    "shell": "Панцирь",
    "whirlwind": "Вихрь",
    "ghost": "Призрак",
}


def load_scrolls_from_json() -> list[dict]:
    """Load scroll data from scrolls.json."""
    with open(SCROLLS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


async def ensure_archetypes(session) -> int:
    """Upsert the 4 canonical archetypes. Returns number of rows inserted."""
    inserted = 0
    for code, name in CANONICAL_ARCHETYPES.items():
        result = await session.execute(select(Archetype).where(Archetype.code == code))
        existing = result.scalar_one_or_none()
        if existing is None:
            session.add(Archetype(code=code, name=name))
            inserted += 1
    return inserted


async def seed_scrolls(reset: bool = False) -> int:
    """Upsert scrolls and their archetype tasks from JSON into the database.

    Args:
        reset: If True, delete all existing scrolls and archetype tasks first.

    Returns:
        Number of days (scrolls) processed.
    """
    scrolls_data = load_scrolls_from_json()

    async with session_factory() as session:
        if reset:
            logger.info("Resetting: deleting all existing scrolls and tasks...")
            result = await session.execute(select(ScrollArchetypeTask))
            for task in result.scalars().all():
                await session.delete(task)
            result = await session.execute(select(Scroll))
            for scroll in result.scalars().all():
                await session.delete(scroll)
            await session.commit()
            logger.info("Deleted existing scroll content.")

        inserted_archetypes = await ensure_archetypes(session)
        if inserted_archetypes:
            logger.info("Inserted %d missing archetypes.", inserted_archetypes)
            await session.commit()

        count = 0
        for i, entry in enumerate(scrolls_data):
            day_number = entry["day_number"]

            # Upsert the per-day scroll by day_number.
            result = await session.execute(
                select(Scroll).where(Scroll.day_number == day_number)
            )
            scroll = result.scalar_one_or_none()
            if scroll is None:
                scroll = Scroll(
                    day_number=day_number,
                    common_task=entry["common_task"],
                    ritual=entry["ritual"],
                    habits=entry["habits"],
                    micromovements=entry["micromovements"],
                )
                session.add(scroll)
                await session.flush()  # materialize scroll.id for the task fk
            else:
                scroll.common_task = entry["common_task"]
                scroll.ritual = entry["ritual"]
                scroll.habits = entry["habits"]
                scroll.micromovements = entry["micromovements"]

            # Upsert per-archetype tasks for this scroll.
            for archetype_code, task_text in entry["archetype_tasks"].items():
                result = await session.execute(
                    select(ScrollArchetypeTask).where(
                        ScrollArchetypeTask.scroll_id == scroll.id,
                        ScrollArchetypeTask.archetype_code == archetype_code,
                    )
                )
                task = result.scalar_one_or_none()
                if task is None:
                    session.add(
                        ScrollArchetypeTask(
                            scroll_id=scroll.id,
                            archetype_code=archetype_code,
                            task_text=task_text,
                        )
                    )
                else:
                    task.task_text = task_text

            count += 1

            if (i + 1) % 30 == 0:
                logger.info("Processed %d/%d days...", i + 1, len(scrolls_data))

        await session.commit()
        logger.info("Seeding complete: %d scroll days processed.", count)
        return count


def main() -> None:
    """CLI entry point for seed_scrolls."""
    parser = argparse.ArgumentParser(description="Seed scrolls into database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing scrolls before seeding",
    )
    args = parser.parse_args()

    import asyncio
    count = asyncio.run(seed_scrolls(reset=args.reset))
    print(f"Done: {count} scroll days seeded.")


if __name__ == "__main__":
    main()
