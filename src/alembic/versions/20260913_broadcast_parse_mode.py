"""Add parse_mode column to notifications

Revision ID: 20260913_broadcast_parse_mode
Revises: 20260912_broadcast_media_scheduling
Create Date: 2026-09-13

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260913_broadcast_parse_mode"
down_revision = "20260912_broadcast_media_scheduling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("parse_mode", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("notifications", "parse_mode")
