"""add recipe structured fields

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-15 12:00:00+00:00

V6-Phase 2: Document table add structured recipe fields to support
structured filtering and the cocktail agent (search_recipes/get_recipe).

New columns (all with server_default for backward compat):
- base_spirit: base spirit identifier (gin/vodka/rum/whiskey/tequila/brandy/other), indexed
- abv: estimated weighted alcohol by volume (0.0-1.0 float)
- ingredients_json: structured ingredient list JSON text
  [{"name": "金酒", "measure": "45ml"}, ...]
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: str | Sequence[str] | None = '0012'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'document',
        sa.Column('base_spirit', sa.String(length=32), server_default='', nullable=True),
    )
    op.create_index('ix_document_base_spirit', 'document', ['base_spirit'])
    op.add_column(
        'document',
        sa.Column('abv', sa.Float(), server_default='0.0', nullable=True),
    )
    op.add_column(
        'document',
        sa.Column('ingredients_json', sa.Text(), server_default='[]', nullable=True),
    )


def downgrade() -> None:
    op.drop_column('document', 'ingredients_json')
    op.drop_column('document', 'abv')
    op.drop_index('ix_document_base_spirit', table_name='document')
    op.drop_column('document', 'base_spirit')
