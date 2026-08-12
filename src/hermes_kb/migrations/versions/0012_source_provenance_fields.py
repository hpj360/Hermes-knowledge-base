# -*- coding: utf-8 -*-
"""add source provenance fields

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-12 12:00:00+00:00

V4-Phase: Document table add 4 source provenance columns for authoritative
data source integration.

New columns (all nullable with server_default for backward compat):
- source_authority: source institution/journal name (IWSR/WHO/J. Agric. Food Chem.)
- source_url: source link
- source_refreshed_at: data refresh timestamp
- source_license: license identifier (CC0/CC BY/open-access)
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: Union[str, Sequence[str], None] = '0011_feedback_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'document',
        sa.Column('source_authority', sa.String(length=128), server_default='', nullable=True),
    )
    op.add_column(
        'document',
        sa.Column('source_url', sa.String(length=512), nullable=True),
    )
    op.add_column(
        'document',
        sa.Column('source_refreshed_at', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'document',
        sa.Column('source_license', sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('document', 'source_license')
    op.drop_column('document', 'source_refreshed_at')
    op.drop_column('document', 'source_url')
    op.drop_column('document', 'source_authority')
