"""Add scroll_types, daily_scrolls, user_daily_commands tables

Revision ID: 20260909_add_scroll_types
Revises: 20260908_add_moderation
Create Date: 2026-09-09

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260909_add_scroll_types"
down_revision = "20260908_add_moderation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # scroll_types
    op.create_table(
        "scroll_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(30), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("command", sa.String(30), nullable=False),
        sa.Column("hour", sa.Integer(), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("requires_meditation", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_breathing_day_only", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_awareness_day_only", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # daily_scrolls
    op.create_table(
        "daily_scrolls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("day_number", sa.Integer(), nullable=False, index=True),
        sa.Column("scroll_type_id", UUID(as_uuid=True), sa.ForeignKey("scroll_types.id"), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("media_file_id", sa.String(200), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("day_number", "scroll_type_id", name="uq_daily_scroll_day_type"),
    )

    # user_daily_commands
    op.create_table(
        "user_daily_commands",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("quest_day", sa.Integer(), nullable=False, index=True),
        sa.Column("command", sa.String(30), nullable=False),
        sa.Column("scroll_type_id", UUID(as_uuid=True), sa.ForeignKey("scroll_types.id"), nullable=True),
        sa.Column("daily_scroll_id", UUID(as_uuid=True), sa.ForeignKey("daily_scrolls.id"), nullable=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_text", sa.Text(), nullable=True),
        sa.Column("report_media_url", sa.String(300), nullable=True),
        sa.Column("report_media_type", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "quest_day", "command", name="uq_user_day_command"),
    )


def downgrade() -> None:
    op.drop_table("user_daily_commands")
    op.drop_table("daily_scrolls")
    op.drop_table("scroll_types")
