"""Add users.access_until for 30-day access periods.

Revision ID: 20260926_access_until
Revises: 20260925_user_email
Create Date: 2026-10-11

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260926_access_until"
down_revision = "20260925_user_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("access_until", sa.DateTime(timezone=True), nullable=True))
    # Backfill: existing paid users get 30 days from their payment time
    op.execute(
        "UPDATE users SET access_until = paid_at + INTERVAL '30 days' "
        "WHERE paid_at IS NOT NULL AND access_until IS NULL"
    )


def downgrade() -> None:
    op.drop_column("users", "access_until")
