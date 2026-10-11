"""Add groups.finish_notified_at for one-time finish reporting.

Revision ID: 20260927_group_finish
Revises: 20260926_access_until
Create Date: 2026-10-11

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260927_group_finish"
down_revision = "20260926_access_until"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("groups", sa.Column("finish_notified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("groups", "finish_notified_at")
