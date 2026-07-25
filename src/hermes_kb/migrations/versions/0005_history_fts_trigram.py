"""switch history_fts to trigram tokenizer

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-25 12:00:00+00:00

H2 性能优化：将 history_fts 从 unicode61 切换为 trigram 分词器。

根因：unicode61 对连续中文整体作为单 token，前缀匹配无法命中中间子串
（如 "中国白酒" 中搜索 "白酒" 不命中）。M2-07 暂用 LIKE 子串匹配兜底，
但 LIKE 全表扫描在 10w+ 行时性能不足。

trigram 分词器索引所有 3 字符子串，支持任意位置子串 MATCH：
- "中国白酒" 索引为 "中国白" + "国白酒"
- 搜索 "国白酒" 命中（trigram MATCH）
- 搜索 "白酒"（2 字）不命中 → API 层回退 LIKE

切换步骤：
1. 删除旧触发器（querylog_ai/ad/au）
2. 删除旧 history_fts 表（unicode61）
3. 用 trigram 重建 history_fts
4. 重建同名触发器（SQL 不变，仅表 tokenizer 变了）
5. 从 querylog 回填全部数据

注：chunks_fts 保持 unicode61 不变（chunk 检索场景不同，且 M0 已稳定）。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除旧触发器（避免重建表时触发器悬空引用）
    op.execute("DROP TRIGGER IF EXISTS querylog_au")
    op.execute("DROP TRIGGER IF EXISTS querylog_ad")
    op.execute("DROP TRIGGER IF EXISTS querylog_ai")
    # 2. 删除旧 history_fts 表（unicode61 分词器）
    op.execute("DROP TABLE IF EXISTS history_fts")
    # 3. 用 trigram 分词器重建（支持中文子串 MATCH）
    op.execute(
        "CREATE VIRTUAL TABLE history_fts USING fts5("
        "query, answer, log_id UNINDEXED, "
        "tokenize='trigram'"
        ")"
    )
    # 4. 重建同名触发器（SQL 与 0004 相同，仅表的 tokenizer 变了）
    op.execute(
        "CREATE TRIGGER querylog_ai AFTER INSERT ON querylog BEGIN "
        "INSERT INTO history_fts(query, answer, log_id) "
        "VALUES (new.query, new.answer, new.id); "
        "END"
    )
    op.execute(
        "CREATE TRIGGER querylog_ad AFTER DELETE ON querylog BEGIN "
        "DELETE FROM history_fts WHERE log_id = old.id; "
        "END"
    )
    op.execute(
        "CREATE TRIGGER querylog_au AFTER UPDATE ON querylog BEGIN "
        "DELETE FROM history_fts WHERE log_id = old.id; "
        "INSERT INTO history_fts(query, answer, log_id) "
        "VALUES (new.query, new.answer, new.id); "
        "END"
    )
    # 5. 从 querylog 全量回填（旧表已删除，需重建索引）
    op.execute(
        "INSERT INTO history_fts(query, answer, log_id) "
        "SELECT q.query, q.answer, q.id FROM querylog q"
    )


def downgrade() -> None:
    # 回滚到 unicode61（失去中文子串 MATCH 能力，但保留 FTS5 表结构）
    op.execute("DROP TRIGGER IF EXISTS querylog_au")
    op.execute("DROP TRIGGER IF EXISTS querylog_ad")
    op.execute("DROP TRIGGER IF EXISTS querylog_ai")
    op.execute("DROP TABLE IF EXISTS history_fts")
    op.execute(
        "CREATE VIRTUAL TABLE history_fts USING fts5("
        "query, answer, log_id UNINDEXED, "
        "tokenize='unicode61'"
        ")"
    )
    op.execute(
        "CREATE TRIGGER querylog_ai AFTER INSERT ON querylog BEGIN "
        "INSERT INTO history_fts(query, answer, log_id) "
        "VALUES (new.query, new.answer, new.id); "
        "END"
    )
    op.execute(
        "CREATE TRIGGER querylog_ad AFTER DELETE ON querylog BEGIN "
        "DELETE FROM history_fts WHERE log_id = old.id; "
        "END"
    )
    op.execute(
        "CREATE TRIGGER querylog_au AFTER UPDATE ON querylog BEGIN "
        "DELETE FROM history_fts WHERE log_id = old.id; "
        "INSERT INTO history_fts(query, answer, log_id) "
        "VALUES (new.query, new.answer, new.id); "
        "END"
    )
    op.execute(
        "INSERT INTO history_fts(query, answer, log_id) "
        "SELECT q.query, q.answer, q.id FROM querylog q"
    )
