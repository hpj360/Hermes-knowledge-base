"""add users and invite_code tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-29 12:00:00+00:00

V3-Task9/10: 多用户协作支持。
- users 表：username/password_hash/role/invited_by/is_active
- invite_code 表：owner 生成的一次性邀请码
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=True),
        sa.Column('role', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('invited_by', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username', name='uq_user_username')
    )
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_username'), ['username'], unique=False)
        batch_op.create_index(batch_op.f('ix_user_role'), ['role'], unique=False)

    op.create_table('invitecode',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('role', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('created_by', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('used_by', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_invite_code')
    )
    with op.batch_alter_table('invitecode', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invitecode_code'), ['code'], unique=False)
        batch_op.create_index(batch_op.f('ix_invitecode_created_by'), ['created_by'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('invitecode', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invitecode_created_by'))
        batch_op.drop_index(batch_op.f('ix_invitecode_code'))
    op.drop_table('invitecode')

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_role'))
        batch_op.drop_index(batch_op.f('ix_user_username'))
    op.drop_table('user')
