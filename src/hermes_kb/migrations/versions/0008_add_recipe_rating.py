"""add recipe_rating table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-29 23:30:00+00:00

V2-Task6: Recipe rating & tasting notes.
- UPSERT semantic: same (doc_id, user) keeps only one record
- score: 0-5 stars (0 = note only)
- comment: optional tasting note
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: str | Sequence[str] | None = '0007_recipe_difficulty_abv'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('reciperating',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('user', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['doc_id'], ['document.doc_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doc_id', 'user', name='uq_recipe_rating_doc_user')
    )
    with op.batch_alter_table('reciperating', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reciperating_doc_id'), ['doc_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_reciperating_user'), ['user'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('reciperating', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reciperating_user'))
        batch_op.drop_index(batch_op.f('ix_reciperating_doc_id'))

    op.drop_table('reciperating')
