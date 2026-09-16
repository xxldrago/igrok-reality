"""Add specialist_quests table for specialist additional quests.

Revision ID: 20260916_specialist_quests
Revises: 20260914_breathing_slots
Create Date: 2026-09-16

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260916_specialist_quests"
down_revision = "20260914_breathing_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "specialist_quests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id"), nullable=False, index=True),
        sa.Column("specialist_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("media_file_id", sa.String(256), nullable=True),
        sa.Column("xp_reward", sa.Integer(), server_default="10"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("specialist_quests")
