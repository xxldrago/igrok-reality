"""Insert welcome_message setting into the database.

Uses DEFAULT_WELCOME_MESSAGE from settings_service (single source of truth).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.shared.database import session_factory
from app.shared.models.settings import Setting
from app.bot.services.settings_service import DEFAULT_WELCOME_MESSAGE


async def insert_welcome_message() -> None:
    """Insert or update welcome_message setting."""
    async with session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Setting).where(Setting.key == "welcome_message")
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = DEFAULT_WELCOME_MESSAGE
            print("Updated existing welcome_message")
        else:
            setting = Setting(key="welcome_message", value=DEFAULT_WELCOME_MESSAGE)
            session.add(setting)
            print("Inserted new welcome_message")

        await session.commit()
        print(f"Done! Message length: {len(DEFAULT_WELCOME_MESSAGE)} chars")


if __name__ == "__main__":
    asyncio.run(insert_welcome_message())
