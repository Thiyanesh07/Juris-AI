"""Add server-side, single-use OAuth transactions.

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth_transactions",
        sa.Column("state_digest", sa.String(length=64), nullable=False),
        sa.Column("session_binding", sa.String(length=64), nullable=False),
        sa.Column("intent", sa.String(length=16), nullable=False),
        sa.Column("return_to", sa.String(length=2048), nullable=True),
        sa.Column("redirect_uri", sa.String(length=2048), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("state_digest", name="pk_oauth_transactions"),
    )
    op.create_index(
        "ix_oauth_transactions_expires_at",
        "oauth_transactions",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_oauth_transactions_expires_at", table_name="oauth_transactions")
    op.drop_table("oauth_transactions")
