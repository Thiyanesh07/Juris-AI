"""add password_hash to users for email login

Revision ID: b8c4e1a2d3f0
Revises: a1b2c3d4e5f6
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8c4e1a2d3f0"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
