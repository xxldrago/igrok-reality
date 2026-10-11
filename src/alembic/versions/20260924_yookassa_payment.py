"""Add yookassa_payment_id to payments.

Revision ID: 20260924_yookassa_payment
Revises: 20260922_admin_users
Create Date: 2026-10-11

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260924_yookassa_payment"
down_revision = "20260922_admin_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("yookassa_payment_id", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_payments_yookassa_payment_id", "payments", ["yookassa_payment_id"])


def downgrade() -> None:
    op.drop_constraint("uq_payments_yookassa_payment_id", "payments", type_="unique")
    op.drop_column("payments", "yookassa_payment_id")
