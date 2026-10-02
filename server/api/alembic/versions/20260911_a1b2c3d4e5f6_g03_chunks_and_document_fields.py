"""G03 — add file_hash/file_path to documents and create chunks table

Revision ID: a1b2c3d4e5f6
Revises: 3df761d401fe
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "3df761d401fe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── documents: add file_hash and file_path ──────────────────────────────
    op.add_column("documents", sa.Column("file_hash", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("file_path", sa.String(length=500), nullable=True))
    op.create_index(op.f("ix_documents_file_hash"), "documents", ["file_hash"], unique=False)

    # ── chunks table ────────────────────────────────────────────────────────
    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column(
            "hierarchy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("citation_ref", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_chunks_document_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_chunks_document_version_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.UniqueConstraint(
            "document_id",
            "document_version_id",
            "chunk_index",
            name="uq_chunks_doc_version_index",
        ),
    )
    op.create_index(op.f("ix_chunks_document_id"), "chunks", ["document_id"], unique=False)
    op.create_index(
        op.f("ix_chunks_document_version_id"), "chunks", ["document_version_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_chunks_document_version_id"), table_name="chunks")
    op.drop_index(op.f("ix_chunks_document_id"), table_name="chunks")
    op.drop_table("chunks")

    op.drop_index(op.f("ix_documents_file_hash"), table_name="documents")
    op.drop_column("documents", "file_path")
    op.drop_column("documents", "file_hash")
