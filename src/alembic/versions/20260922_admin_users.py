"""Admin users table for multiple panel accounts.

Revision ID: 20260922_admin_users
Revises: 20260921_quest_groups
Create Date: 2026-09-22

Seeds the row from the legacy single-admin settings override when present.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260922_admin_users"
down_revision = "20260921_quest_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(64), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="master"),
        sa.Column("telegram", sa.String(100), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    # Adopt the legacy single-admin credentials (if an override was saved).
    op.execute(
        "INSERT INTO admin_users (username, password_hash, role) "
        "SELECT u.value, h.value, 'master' FROM "
        "(SELECT value FROM settings WHERE key = 'admin_username') u, "
        "(SELECT value FROM settings WHERE key = 'admin_password_hash') h "
        "ON CONFLICT (username) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("admin_users")
