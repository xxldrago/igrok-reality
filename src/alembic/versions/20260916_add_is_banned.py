"""Add is_banned column to users table.

Revision ID: 20260916_add_is_banned
Revises: 20260916_specialist_quests
Create Date: 2026-09-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260916_add_is_banned"
down_revision = "20260916_specialist_quests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_banned", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_banned")
