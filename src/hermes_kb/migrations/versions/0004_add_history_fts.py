"""add history_fts for M2-07

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-25 10:00:00+00:00

M2-07：历史搜索与筛选——为 querylog.query / answer 建立 FTS5 全文索引。

- 新增 history_fts 虚拟表（unicode61 分词，按字索引中文）
- 新增 querylog_ai / querylog_ad / querylog_au 触发器同步索引
- 触发器用 log_id 列绑定 FTS5 与 querylog（不依赖 rowid 对齐）
- upgrade 结束后回填现有 querylog 数据到 history_fts

注：database.py._init_fts() 也会幂等创建同名虚拟表与触发器，
alembic 路径与 create_all 回退路径均保证最终一致。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # FTS5 虚拟表（alembic autogenerate 不支持，需手写 SQL）
    op.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS history_fts USING fts5("
        "query, answer, log_id UNINDEXED, "
        "tokenize='unicode61'"
        ")"
    )
    # 写入触发器：携带 log_id 用于 JOIN 回表
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS querylog_ai AFTER INSERT ON querylog BEGIN "
        "INSERT INTO history_fts(query, answer, log_id) "
        "VALUES (new.query, new.answer, new.id); "
        "END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS querylog_ad AFTER DELETE ON querylog BEGIN "
        "DELETE FROM history_fts WHERE log_id = old.id; "
        "END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS querylog_au AFTER UPDATE ON querylog BEGIN "
        "DELETE FROM history_fts WHERE log_id = old.id; "
        "INSERT INTO history_fts(query, answer, log_id) "
        "VALUES (new.query, new.answer, new.id); "
        "END"
    )
    # 回填现有 querylog 数据（旧库升级）
    op.execute(
        "INSERT INTO history_fts(query, answer, log_id) "
        "SELECT q.query, q.answer, q.id FROM querylog q "
        "LEFT JOIN history_fts f ON f.log_id = q.id "
        "WHERE f.log_id IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS querylog_au")
    op.execute("DROP TRIGGER IF EXISTS querylog_ad")
    op.execute("DROP TRIGGER IF EXISTS querylog_ai")
    # FTS5 虚拟表用 DROP TABLE 删除
    op.execute("DROP TABLE IF EXISTS history_fts")
