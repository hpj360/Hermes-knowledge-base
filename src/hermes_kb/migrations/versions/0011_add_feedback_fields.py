# -*- coding: utf-8 -*-
"""add feedback_comment and feedback_tag to querylog

Revision ID: 0011_feedback_fields
Revises: 0009
Create Date: 2026-07-31 10:00:00+00:00

V5: 结构化反馈升级——在 querylog 表新增两列：
- feedback_comment: Text，用户提交的反馈评论（≤500 字，可空）
- feedback_tag: String(32)，问题标签（inaccurate/not_found/wrong_citation/other）

两列均带 server_default=''，向后兼容旧记录（自动填充空串）。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0011_feedback_fields'
down_revision: Union[str, Sequence[str], None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite batch mode: ALTER TABLE 在 SQLite 中需要表重建
    # alembic batch_alter_table 自动处理
    with op.batch_alter_table('querylog', schema=None) as batch_op:
        # 新增列，带空串默认值，向后兼容旧记录
        batch_op.add_column(
            sa.Column('feedback_comment', sa.Text(), nullable=False, server_default='')
        )
        batch_op.add_column(
            sa.Column('feedback_tag', sa.String(length=32), nullable=False, server_default='')
        )


def downgrade() -> None:
    with op.batch_alter_table('querylog', schema=None) as batch_op:
        batch_op.drop_column('feedback_tag')
        batch_op.drop_column('feedback_comment')
