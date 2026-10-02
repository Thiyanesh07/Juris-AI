"""add super_admin role, is_active, and last_login_at to users

Revision ID: c7e8f9a0b1c2
Revises: b8c4e1a2d3f0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7e8f9a0b1c2"
down_revision: str | None = "b8c4e1a2d3f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add super_admin to user_role enum if using PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'super_admin'")

    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_active")
