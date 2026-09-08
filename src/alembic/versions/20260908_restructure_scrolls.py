"""Restructure scrolls to 5-section schema and create scroll_archetype_tasks.

Revision ID: restructure_scrolls
Revises: add_archetypes
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "restructure_scrolls"
down_revision: Union[str, None] = "add_archetypes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Restructure scrolls to per-day 5-section rows and create the tasks table.

    Data migration strategy: existing rows are per-day×archetype and cannot be
    reliably decomposed into 5 sections from a single ``text`` column, so they are
    dropped and re-seeded by src/tools/seed_scrolls.py (authoritative data source).
    """
    op.drop_constraint(
        "scrolls_day_number_archetype_key", "scrolls", type_="unique"
    )
    op.drop_column("scrolls", "archetype")
    op.drop_column("scrolls", "text")

    # Existing per-archetype rows (4 per day) cannot map to a single per-day row
    # with the new NOT NULL columns; delete them so the day_number unique
    # constraint holds. Content is rebuildable via the seed script.
    scrolls_table = sa.table("scrolls", sa.column("id", sa.types.Uuid()))
    op.execute("DELETE FROM scrolls")

    op.add_column("scrolls", sa.Column("common_task", sa.Text(), nullable=False, server_default=""))
    op.add_column("scrolls", sa.Column("ritual", sa.Text(), nullable=False, server_default=""))
    op.add_column("scrolls", sa.Column("habits", sa.Text(), nullable=False, server_default=""))
    op.add_column("scrolls", sa.Column("micromovements", sa.Text(), nullable=False, server_default=""))
    op.add_column("scrolls", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))

    op.create_unique_constraint(
        "scrolls_day_number_key", "scrolls", ["day_number"]
    )

    op.create_table(
        "scroll_archetype_tasks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scroll_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scrolls.id"),
            nullable=False,
        ),
        sa.Column("archetype_code", sa.String(50), nullable=False),
        sa.Column("task_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("scroll_id", "archetype_code"),
    )
    op.create_index(
        "ix_scroll_archetype_tasks_scroll_id",
        "scroll_archetype_tasks",
        ["scroll_id"],
    )


def downgrade() -> None:
    """Reverse: drop tasks table and restore old single-text scroll schema."""
    op.drop_index(
        "ix_scroll_archetype_tasks_scroll_id", table_name="scroll_archetype_tasks"
    )
    op.drop_table("scroll_archetype_tasks")

    op.drop_constraint("scrolls_day_number_key", "scrolls", type_="unique")
    op.drop_column("scrolls", "published_at")
    op.drop_column("scrolls", "micromovements")
    op.drop_column("scrolls", "habits")
    op.drop_column("scrolls", "ritual")
    op.drop_column("scrolls", "common_task")

    op.add_column("scrolls", sa.Column("text", sa.Text(), nullable=False, server_default=""))
    op.add_column("scrolls", sa.Column("archetype", sa.String(50), nullable=False, server_default="head"))
    op.create_unique_constraint(
        "scrolls_day_number_archetype_key", "scrolls", ["day_number", "archetype"]
    )
