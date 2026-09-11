"""Breathing-day 3x /breath support: slot column on user_daily_commands

Revision ID: 20260914_breathing_slots
Revises: 20260913_broadcast_parse_mode
Create Date: 2026-09-14

On breathing days /breath can be completed 3 times (morning/day/evening).
The slot column distinguishes the repeats; all other commands use ''.

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260914_breathing_slots"
down_revision = "20260913_broadcast_parse_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_daily_commands",
        sa.Column("slot", sa.String(20), nullable=False, server_default=""),
    )
    op.drop_constraint("uq_user_day_command", "user_daily_commands", type_="unique")
    op.create_unique_constraint(
        "uq_user_day_command_slot",
        "user_daily_commands",
        ["user_id", "quest_day", "command", "slot"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_user_day_command_slot", "user_daily_commands", type_="unique")
    op.drop_column("user_daily_commands", "slot")
    op.create_unique_constraint(
        "uq_user_day_command",
        "user_daily_commands",
        ["user_id", "quest_day", "command"],
    )
