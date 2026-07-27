# -*- coding: utf-8 -*-
"""add recipe metadata fields

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-27 12:00:00+00:00

M3: Document table add 4 structured metadata fields for recipe docs.

New columns (all nullable with server_default '' for backward compat):
- glassware: glass type (martini/rocks/highball...), indexed for filtering
- technique: mixing technique (build/stir/shake/blend/layer/muddle), indexed
- iba_category: IBA category (unforgettables/contemporary_classics/new_era_drinks), indexed
- flavor_profile: semicolon-separated flavor tags (no index, long string)

Indexes created for glassware/technique/iba_category only (flavor_profile is a
long semicolon-separated string, not used for exact-match filtering).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 4 columns (nullable with server_default '' for backward compat)
    op.add_column(
        'document',
        sa.Column('glassware', sa.String(length=64), server_default='', nullable=True),
    )
    op.add_column(
        'document',
        sa.Column('technique', sa.String(length=32), server_default='', nullable=True),
    )
    op.add_column(
        'document',
        sa.Column('iba_category', sa.String(length=32), server_default='', nullable=True),
    )
    op.add_column(
        'document',
        sa.Column('flavor_profile', sa.String(length=256), server_default='', nullable=True),
    )
    # Create indexes for filterable fields (flavor_profile excluded: long string)
    op.create_index('ix_document_glassware', 'document', ['glassware'], unique=False)
    op.create_index('ix_document_technique', 'document', ['technique'], unique=False)
    op.create_index('ix_document_iba_category', 'document', ['iba_category'], unique=False)


def downgrade() -> None:
    # Drop indexes first (avoid dangling references before dropping columns)
    op.drop_index('ix_document_iba_category', table_name='document')
    op.drop_index('ix_document_technique', table_name='document')
    op.drop_index('ix_document_glassware', table_name='document')
    # Drop columns (reverse order of upgrade)
    op.drop_column('document', 'flavor_profile')
    op.drop_column('document', 'iba_category')
    op.drop_column('document', 'technique')
    op.drop_column('document', 'glassware')
