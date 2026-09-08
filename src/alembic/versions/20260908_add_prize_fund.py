"""Add prize_fund and prize_fund_payouts tables

Revision ID: 20260908_add_prize_fund
Revises: 20260908_add_groups_role_history_clans
Create Date: 2026-09-08

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260908_add_prize_fund"
down_revision = "20260908_add_groups_role_history_clans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prize_funds",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("total_amount", sa.Integer(), default=0, nullable=False),
        sa.Column("percent_rule", sa.String(20), default="xp", nullable=False),
        sa.Column("status", sa.String(20), default="open", nullable=False),
        sa.Column("distributed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "prize_fund_payouts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("prize_fund_id", UUID(as_uuid=True), sa.ForeignKey("prize_funds.id"), index=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("prize_fund_payouts")
    op.drop_table("prize_funds")