"""initial schema: cases table

Revision ID: 0001
Revises:
Create Date: 2026-05-12

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_cases_symbol", "cases", ["symbol"])
    op.create_index("ix_cases_user_id", "cases", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cases_user_id", table_name="cases")
    op.drop_index("ix_cases_symbol", table_name="cases")
    op.drop_table("cases")
