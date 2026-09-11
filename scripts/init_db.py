"""Initialize database — create all tables and stamp alembic head.

Run: python -m scripts.init_db
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from app.shared.database import engine, session_factory
from app.shared.models import Base


async def init_db() -> None:
    """Create all tables and stamp alembic head."""
    print("Creating all tables...")

    async with engine.begin() as conn:
        # Create all tables from models
        await conn.run_sync(Base.metadata.create_all)
        print(f"Created {len(Base.metadata.sorted_tables)} tables")

        # Stamp alembic version as head
        await conn.execute(
            text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        # Get the head revision from migration files
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        current = result.scalar()

        if current:
            print(f"Alembic version already set: {current}")
        else:
            # Set to the last migration
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('20260909_add_scroll_types')")
            )
            print("Alembic version set to: 20260909_add_scroll_types")

    print("Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
