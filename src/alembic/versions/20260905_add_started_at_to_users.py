"""Add started_at column to users table.

Revision ID: add_started_at_to_users
Revises:
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_started_at_to_users"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable started_at column to users table."""
    op.add_column("users", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove started_at column from users table."""
    op.drop_column("users", "started_at")
