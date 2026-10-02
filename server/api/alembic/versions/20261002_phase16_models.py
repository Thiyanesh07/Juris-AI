"""Add SystemSetting and ValidationItem tables (Phase 16).

Revision ID: 20261002_phase16_models
Revises: 20260928_c7e8f9a0b1c2_add_super_admin_role_and_user_fields
Create Date: 2026-10-02 14:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, None] = 'c7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('section', sa.String(length=50), nullable=False),
        sa.Column('config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_by_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_section'), 'system_settings', ['section'], unique=True)

    op.create_table(
        'validation_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('item_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('proposed_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('evidence_text', sa.Text(), nullable=True),
        sa.Column('source_document_id', sa.Uuid(), nullable=True),
        sa.Column('source_chunk_id', sa.String(length=100), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('reviewer_id', sa.Uuid(), nullable=True),
        sa.Column('decision_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_validation_items_item_type'), 'validation_items', ['item_type'], unique=False)
    op.create_index(op.f('ix_validation_items_status'), 'validation_items', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_validation_items_status'), table_name='validation_items')
    op.drop_index(op.f('ix_validation_items_item_type'), table_name='validation_items')
    op.drop_table('validation_items')
    op.drop_index(op.f('ix_system_settings_section'), table_name='system_settings')
    op.drop_table('system_settings')
