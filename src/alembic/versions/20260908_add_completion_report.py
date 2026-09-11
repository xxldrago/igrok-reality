"""Add report fields to user_completions

Revision ID: 20260908_add_completion_report
Revises: 20260908_restructure_scrolls
Create Date: 2026-09-08

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260908_add_completion_report"
down_revision = "restructure_scrolls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_completions",
        sa.Column("report_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "user_completions",
        sa.Column("report_media_url", sa.String(255), nullable=True),
    )
    op.add_column(
        "user_completions",
        sa.Column("report_media_type", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_completions", "report_text")
    op.drop_column("user_completions", "report_media_url")
    op.drop_column("user_completions", "report_media_type")