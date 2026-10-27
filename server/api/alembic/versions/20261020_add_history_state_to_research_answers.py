"""Add persistent research state (mode, evidence, graph, reasoning) to research_answers and citations (Phase 3).

Revision ID: a1b2c3d4e5f7
Revises: f3a4b5c6d7e8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Extend research_answers with mode, evidence, graph, and reasoning state
    op.add_column(
        "research_answers",
        sa.Column("mode", sa.String(length=32), server_default="COMPREHENSIVE", nullable=False),
    )
    op.add_column(
        "research_answers",
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "research_answers",
        sa.Column("graph_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "research_answers",
        sa.Column("reasoning_steps_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "research_answers",
        sa.Column("citation_validation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # 2. Extend citations with chunk_id, marker, page ranges, citation_ref, and pdf_url
    op.add_column(
        "citations",
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "citations",
        sa.Column("marker", sa.Integer(), nullable=True),
    )
    op.add_column(
        "citations",
        sa.Column("page_start", sa.Integer(), nullable=True),
    )
    op.add_column(
        "citations",
        sa.Column("page_end", sa.Integer(), nullable=True),
    )
    op.add_column(
        "citations",
        sa.Column("citation_ref", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "citations",
        sa.Column("pdf_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("citations", "pdf_url")
    op.drop_column("citations", "citation_ref")
    op.drop_column("citations", "page_end")
    op.drop_column("citations", "page_start")
    op.drop_column("citations", "marker")
    op.drop_column("citations", "chunk_id")

    op.drop_column("research_answers", "citation_validation_json")
    op.drop_column("research_answers", "reasoning_steps_json")
    op.drop_column("research_answers", "graph_json")
    op.drop_column("research_answers", "evidence_json")
    op.drop_column("research_answers", "mode")
