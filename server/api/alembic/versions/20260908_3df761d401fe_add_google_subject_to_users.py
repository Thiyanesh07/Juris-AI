"""add Google OAuth subject to users

Revision ID: 3df761d401fe
Revises: ca941e9f2e4e
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3df761d401fe"
down_revision: str | None = "ca941e9f2e4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_subject", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_users_google_subject"), "users", ["google_subject"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_google_subject"), table_name="users")
    op.drop_column("users", "google_subject")
