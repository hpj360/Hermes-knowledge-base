"""add recipe difficulty and abv_bucket fields

Revision ID: 0007_recipe_difficulty_abv
Revises: 0006
Create Date: 2026-07-27 13:00:00+00:00

M3+: Document table add 2 fields for recipe difficulty and ABV bucket.

New columns (nullable=False with server_default '' for backward compat):
- difficulty: making difficulty (easy/medium/hard), indexed for filtering
- abv_bucket: ABV strength bucket (low/medium/high/strong), indexed

Both fields are indexed for filtering use cases.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0007_recipe_difficulty_abv'
down_revision: str | Sequence[str] | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add 2 columns (nullable=False with server_default '' for backward compat)
    op.add_column(
        'document',
        sa.Column('difficulty', sa.String(length=16), server_default='', nullable=False),
    )
    op.add_column(
        'document',
        sa.Column('abv_bucket', sa.String(length=16), server_default='', nullable=False),
    )
    # Create indexes for filterable fields
    op.create_index('ix_document_difficulty', 'document', ['difficulty'], unique=False)
    op.create_index('ix_document_abv_bucket', 'document', ['abv_bucket'], unique=False)


def downgrade() -> None:
    # Drop indexes first (avoid dangling references before dropping columns)
    op.drop_index('ix_document_abv_bucket', table_name='document')
    op.drop_index('ix_document_difficulty', table_name='document')
    # Drop columns (reverse order of upgrade)
    op.drop_column('document', 'abv_bucket')
    op.drop_column('document', 'difficulty')
