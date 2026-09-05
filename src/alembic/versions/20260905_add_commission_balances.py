"""Create commission_balances table.

Revision ID: a1b2c3d4e5f6
Revises: add_started_at_to_users
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "add_started_at_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create commission_balances table with per-user commission tracking."""
    op.create_table(
        "commission_balances",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            unique=True,
            index=True,
            nullable=False,
        ),
        sa.Column("total_earned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_pending", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_paid_out", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_commission_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop commission_balances table."""
    op.drop_table("commission_balances")
