"""Create archetypes reference table.

Revision ID: add_archetypes
Revises: add_role_to_users
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_archetypes"
down_revision: Union[str, None] = "add_role_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the archetypes reference table and seed the 4 canonical rows."""
    op.create_table(
        "archetypes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
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
    op.create_index("ix_archetypes_code", "archetypes", ["code"])

    archetypes_table = sa.table(
        "archetypes",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String(50)),
        sa.column("name", sa.String(100)),
        sa.column("description", sa.Text()),
    )
    op.bulk_insert(
        archetypes_table,
        [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "code": "head",
                "name": "Голова",
                "description": (
                    "Архетип Голова — рациональный стратег. Основан на логике, "
                    "планировании и интеллектуальном поиске решений. Сильная сторона — "
                    "анализ и систематизация."
                ),
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "code": "shell",
                "name": "Панцирь",
                "description": (
                    "Архетип Панцирь — надёжный защитник и опора. Ценит стабильность, "
                    "порядок и последовательность. Сильная сторона — выносливость и "
                    "устойчивость к трудностям."
                ),
            },
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "code": "whirlwind",
                "name": "Вихрь",
                "description": (
                    "Архетип Вихрь — энергичный исследователь. Движется быстро, берётся "
                    "за многое, вдохновляется новизной. Сильная сторона — инициативность "
                    "и способность к быстрой адаптации."
                ),
            },
            {
                "id": "44444444-4444-4444-4444-444444444444",
                "code": "ghost",
                "name": "Призрак",
                "description": (
                    "Архетип Призрак — интуитивный наблюдатель. Чувствует тонкие "
                    "энергии и скрытые закономерности. Сильная сторона — интуиция и "
                    "способность видеть неочевидное."
                ),
            },
        ],
    )


def downgrade() -> None:
    """Drop the archetypes reference table."""
    op.drop_index("ix_archetypes_code", table_name="archetypes")
    op.drop_table("archetypes")
