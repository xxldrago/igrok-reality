"""Add media + scheduling columns to notifications

Revision ID: 20260912_broadcast_media_scheduling
Revises: 20260909_add_scroll_types
Create Date: 2026-09-12

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260912_broadcast_media_scheduling"
down_revision = "20260909_add_scroll_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("media_url", sa.String(500), nullable=True))
    op.add_column("notifications", sa.Column("media_type", sa.String(20), nullable=True))
    op.add_column("notifications", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notifications", sa.Column("audience", sa.String(20), nullable=True))
    op.create_index("ix_notifications_scheduled_at", "notifications", ["scheduled_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_scheduled_at", table_name="notifications")
    op.drop_column("notifications", "audience")
    op.drop_column("notifications", "scheduled_at")
    op.drop_column("notifications", "media_type")
    op.drop_column("notifications", "media_url")
