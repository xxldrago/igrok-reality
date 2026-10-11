"""Add users.email for payment receipts.

Revision ID: 20260925_user_email
Revises: 20260924_yookassa_payment
Create Date: 2026-10-11

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260925_user_email"
down_revision = "20260924_yookassa_payment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "email")
