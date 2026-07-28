"""add history_fts for M2-07

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-25 10:00:00+00:00

M2-07: History search and filtering -- build FTS5 full-text index for querylog.query / answer.

- Add history_fts virtual table (unicode61 tokenizer, per-character indexing for CJK)
- Add querylog_ai / querylog_ad / querylog_au triggers to sync the index
- Triggers bind FTS5 to querylog via the log_id column (no reliance on rowid alignment)
- After upgrade, backfill existing querylog rows into history_fts

Note: database.py._init_fts() also idempotently creates the same virtual table and
triggers; both the alembic path and the create_all fallback path converge to the
same final state.
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
    # FTS5 virtual table (alembic autogenerate does not support it, raw SQL required)
    op.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS history_fts USING fts5("
        "query, answer, log_id UNINDEXED, "
        "tokenize='unicode61'"
        ")"
    )
    # Insert triggers: carry log_id for JOIN back to the source table
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
    # Backfill existing querylog rows (upgrading an old DB)
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
    # FTS5 virtual table is dropped via DROP TABLE
    op.execute("DROP TABLE IF EXISTS history_fts")
