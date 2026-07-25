"""add token fields to querylog

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-25 09:00:00+00:00

M2-10：QueryLog 新增 token 用量字段：
- prompt_tokens: 输入 token 数
- completion_tokens: 输出 token 数
- cost_cny: 单次问答成本（CNY）

均为可空字段（向后兼容旧记录），默认值 0。
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
    # SQLite batch mode：ALTER TABLE 在 SQLite 中需要重建表
    # alembic batch_alter_table 会自动处理
    with op.batch_alter_table('querylog', schema=None) as batch_op:
        # 新增字段，全部有默认值，旧记录自动填 0
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
