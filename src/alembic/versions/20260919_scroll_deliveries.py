"""Add scroll_deliveries table for delivery-message cleanup.

Revision ID: 20260919_scroll_deliveries
Revises: 20260918_broadcast_group
Create Date: 2026-09-19

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260919_scroll_deliveries"
down_revision = "20260918_broadcast_group"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scroll_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("quest_day", sa.Integer(), nullable=False, index=True),
        sa.Column("scroll_code", sa.String(30), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "quest_day", "scroll_code", name="uq_delivery_user_day_code"),
    )


def downgrade() -> None:
    op.drop_table("scroll_deliveries")
