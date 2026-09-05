"""Seed database with scroll content from scrolls.json."""

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
from app.shared.models.scroll import Scroll

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SCROLLS_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scrolls.json")


def load_scrolls_from_json() -> list[dict]:
    """Load scroll data from scrolls.json."""
    with open(SCROLLS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_scrolls(reset: bool = False) -> int:
    """Upsert scrolls from JSON into the database.

    Args:
        reset: If True, delete all existing scrolls before seeding.

    Returns:
        Number of scrolls inserted/updated.
    """
    scrolls_data = load_scrolls_from_json()

    async with session_factory() as session:
        if reset:
            logger.info("Resetting: deleting all existing scrolls...")
            result = await session.execute(select(Scroll))
            existing = result.scalars().all()
            for scroll in existing:
                await session.delete(scroll)
            await session.commit()
            logger.info(f"Deleted {len(existing)} existing scrolls.")

        count = 0
        batch_size = 50
        batch: list[Scroll] = []

        for i, entry in enumerate(scrolls_data):
            day_number = entry["day_number"]
            archetype = entry["archetype"]
            text = entry["text"]

            # Check if scroll already exists
            result = await session.execute(
                select(Scroll).where(
                    Scroll.day_number == day_number,
                    Scroll.archetype == archetype,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.text = text
            else:
                scroll = Scroll(
                    day_number=day_number,
                    archetype=archetype,
                    text=text,
                )
                session.add(scroll)
                batch.append(scroll)

            count += 1

            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(scrolls_data)} scrolls...")

            if len(batch) >= batch_size:
                await session.commit()
                batch = []

        await session.commit()
        logger.info(f"Seeding complete: {count} scrolls processed.")
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
    print(f"Done: {count} scrolls seeded.")


if __name__ == "__main__":
    main()
