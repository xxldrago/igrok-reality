"""Scroll reports: requires_report + xp_reward on daily_scrolls, drop stale FK.

Revision ID: 20260917_scroll_reports
Revises: 20260916_add_is_banned
Create Date: 2026-09-17

- daily_scrolls.requires_report (bool, default True): whether the user must
  attach a report to complete the scroll.
- daily_scrolls.xp_reward (int, nullable): per-scroll XP override, NULL means
  "use the scroll type default".
- Drop user_completions_scroll_id_fkey: completions reference DailyScroll rows
  (new flow) as well as legacy Scroll rows, so a single-table FK is wrong.
  The application resolves the day from DailyScroll first, then Scroll.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260917_scroll_reports"
down_revision = "20260916_add_is_banned"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "daily_scrolls",
        sa.Column("requires_report", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "daily_scrolls",
        sa.Column("xp_reward", sa.Integer(), nullable=True),
    )
    op.drop_constraint(
        "user_completions_scroll_id_fkey", "user_completions", type_="foreignkey"
    )


def downgrade() -> None:
    op.create_foreign_key(
        "user_completions_scroll_id_fkey",
        "user_completions",
        "scrolls",
        ["scroll_id"],
        ["id"],
    )
    op.drop_column("daily_scrolls", "xp_reward")
    op.drop_column("daily_scrolls", "requires_report")
