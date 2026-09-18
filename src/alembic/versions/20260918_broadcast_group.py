"""Broadcast to groups: widen notifications.audience for group names.

Revision ID: 20260918_broadcast_group
Revises: 20260917_scroll_reports
Create Date: 2026-09-18

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260918_broadcast_group"
down_revision = "20260917_scroll_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "notifications",
        "audience",
        existing_type=sa.String(20),
        type_=sa.String(100),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "notifications",
        "audience",
        existing_type=sa.String(100),
        type_=sa.String(20),
        existing_nullable=True,
    )
