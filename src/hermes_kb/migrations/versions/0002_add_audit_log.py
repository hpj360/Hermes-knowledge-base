"""add audit_log table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-25 08:00:00+00:00

M2-08: Audit log table. Records key write operations (login/import/delete/seed/ask sampled at 10%).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: str | Sequence[str] | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('auditlog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('target_type', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('target_id', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('user', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('meta_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('auditlog', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_auditlog_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_auditlog_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_auditlog_target_type'), ['target_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_auditlog_user'), ['user'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('auditlog', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_auditlog_user'))
        batch_op.drop_index(batch_op.f('ix_auditlog_target_type'))
        batch_op.drop_index(batch_op.f('ix_auditlog_created_at'))
        batch_op.drop_index(batch_op.f('ix_auditlog_action'))

    op.drop_table('auditlog')
