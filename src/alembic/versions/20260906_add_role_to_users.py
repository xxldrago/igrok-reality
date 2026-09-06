"""Add role column to users table.

Revision ID: add_role_to_users
Revises: a1b2c3d4e5f6
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_role_to_users"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role column to users table with default 'player'."""
    op.add_column(
        "users",
        sa.Column("role", sa.String(50), nullable=False, server_default="player"),
    )


def downgrade() -> None:
    """Remove role column from users table."""
    op.drop_column("users", "role")
