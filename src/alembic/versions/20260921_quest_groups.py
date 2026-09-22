"""Quest groups replace streams + launch tracking on groups.

Revision ID: 20260921_quest_groups
Revises: 20260920_streams
Create Date: 2026-09-21

- streams table and users.stream_id never reached production, drop
  defensively (IF EXISTS) and keep users.quiz_answers.
- groups.owner_id becomes nullable (auto-created quest groups have no owner).
- groups.launched_at tracks quest-group launch (scrolls start after launch).
- Data: quest group #1 (launched) adopts all paid users without a group.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260921_quest_groups"
down_revision = "20260920_streams"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Column first (CASCADE drops its FK to streams), then the table itself.
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS stream_id CASCADE")
    op.execute("DROP TABLE IF EXISTS streams")
    op.alter_column("groups", "owner_id", existing_type=UUID(as_uuid=True),
                    nullable=True)
    op.add_column("groups", sa.Column("launched_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        "INSERT INTO groups (id, name, type, owner_id, max_members, launched_at) "
        "VALUES (gen_random_uuid(), 'Группа №1', 'quest', NULL, 50, now())"
    )
    op.execute(
        "UPDATE users SET group_id = (SELECT id FROM groups WHERE name = 'Группа №1' AND type = 'quest') "
        "WHERE paid_at IS NOT NULL AND group_id IS NULL"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users SET group_id = NULL WHERE group_id IN "
        "(SELECT id FROM groups WHERE type = 'quest' AND owner_id IS NULL)"
    )
    op.execute(
        "DELETE FROM groups WHERE type = 'quest' AND owner_id IS NULL"
    )
    op.drop_column("groups", "launched_at")
    op.alter_column("groups", "owner_id", existing_type=UUID(as_uuid=True),
                    nullable=False)
