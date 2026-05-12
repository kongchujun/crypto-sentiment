"""x_posts table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-12

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "x_posts",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("author_handle", sa.String(length=64), nullable=False),
        sa.Column("author_name", sa.String(length=128), nullable=True),
        sa.Column(
            "verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("likes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "retweets", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "replies", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("quotes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_x_posts_symbol_created_at",
        "x_posts",
        ["symbol", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_x_posts_symbol_created_at", table_name="x_posts")
    op.drop_table("x_posts")
