"""Streams (cohorts 30-50) + users.stream_id + users.quiz_answers.

Revision ID: 20260920_streams
Revises: 20260919_scroll_deliveries
Create Date: 2026-09-20

Quest starts only when a stream gathers min_size paid users (default 30);
a stream caps at max_size (default 50), then a new one gathers.
Data migration: legacy stream #1 (launched) adopts all paid users.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "20260920_streams"
down_revision = "20260919_scroll_deliveries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "streams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("number", sa.Integer(), unique=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="gathering"),
        sa.Column("min_size", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("max_size", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("launched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.add_column("users", sa.Column("stream_id", UUID(as_uuid=True), sa.ForeignKey("streams.id"), nullable=True))
    op.create_index("ix_users_stream_id", "users", ["stream_id"])
    op.add_column("users", sa.Column("quiz_answers", sa.Text(), nullable=True))

    # Legacy stream #1 adopts all already-paid users (their quest keeps running).
    op.execute(
        "INSERT INTO streams (number, status, launched_at) "
        "VALUES (1, 'launched', now())"
    )
    op.execute(
        "UPDATE users SET stream_id = (SELECT id FROM streams WHERE number = 1) "
        "WHERE paid_at IS NOT NULL AND stream_id IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_users_stream_id", table_name="users")
    op.drop_column("users", "quiz_answers")
    op.drop_column("users", "stream_id")
    op.drop_table("streams")
