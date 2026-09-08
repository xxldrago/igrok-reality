"""Add groups, role_history, clans tables and user foreign keys

Revision ID: 20260908_add_groups_role_history_clans
Revises: 20260908_add_completion_report
Create Date: 2026-09-08

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260908_add_groups_role_history_clans"
down_revision = "20260908_add_completion_report"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # groups table
    op.create_table(
        "groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("max_members", sa.Integer(), default=10, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # role_history table
    op.create_table(
        "role_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("old_role", sa.String(50), nullable=False),
        sa.Column("new_role", sa.String(50), nullable=False),
        sa.Column("changed_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # clans table
    op.create_table(
        "clans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # clan_members table
    op.create_table(
        "clan_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("clan_id", UUID(as_uuid=True), sa.ForeignKey("clans.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Add group_id and clan_id to users
    op.add_column("users", sa.Column("group_id", UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=True))
    op.add_column("users", sa.Column("clan_id", UUID(as_uuid=True), sa.ForeignKey("clans.id"), nullable=True))

    # Create index on users.group_id for faster lookups
    op.create_index("ix_users_group_id", "users", ["group_id"])
    op.create_index("ix_users_clan_id", "users", ["clan_id"])


def downgrade() -> None:
    op.drop_index("ix_users_clan_id", table_name="users")
    op.drop_index("ix_users_group_id", table_name="users")
    op.drop_column("users", "clan_id")
    op.drop_column("users", "group_id")
    op.drop_table("clan_members")
    op.drop_table("clans")
    op.drop_table("role_history")
    op.drop_table("groups")