"""add token fields to querylog

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-25 09:00:00+00:00

M2-10: Add token usage fields to QueryLog:
- prompt_tokens: input token count
- completion_tokens: output token count
- cost_cny: per-query cost (CNY)

All are nullable fields (backward compatible with old records), default 0.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite batch mode: ALTER TABLE in SQLite requires table rebuild
    # alembic batch_alter_table handles this automatically
    with op.batch_alter_table('querylog', schema=None) as batch_op:
        # Add new columns, all with defaults; old records auto-filled with 0
        batch_op.add_column(
            sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column(
                'completion_tokens', sa.Integer(), nullable=False, server_default='0'
            )
        )
        batch_op.add_column(
            sa.Column('cost_cny', sa.Float(), nullable=False, server_default='0.0')
        )


def downgrade() -> None:
    with op.batch_alter_table('querylog', schema=None) as batch_op:
        batch_op.drop_column('cost_cny')
        batch_op.drop_column('completion_tokens')
        batch_op.drop_column('prompt_tokens')
