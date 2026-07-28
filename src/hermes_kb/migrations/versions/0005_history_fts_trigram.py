"""switch history_fts to trigram tokenizer

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-25 12:00:00+00:00

H2 performance optimization: switch history_fts from unicode61 to the trigram tokenizer.

Root cause: unicode61 treats consecutive CJK characters as a single token, so
prefix matching cannot hit a middle substring (e.g. searching "baijiu" inside
"Chinese baijiu" misses). M2-07 fell back to LIKE substring matching, but
LIKE full-table scans are too slow at 100k+ rows.

The trigram tokenizer indexes all 3-character substrings, supporting substring
MATCH at any position:
- A 4-char CJK string is indexed as two overlapping 3-char trigrams
- A 3-char search term hits via trigram MATCH
- A 2-char search term misses -> API layer falls back to LIKE

Switch steps:
1. Drop old triggers (querylog_ai/ad/au)
2. Drop old history_fts table (unicode61)
3. Rebuild history_fts with trigram
4. Recreate same-named triggers (SQL unchanged, only the table tokenizer differs)
5. Backfill all data from querylog

Note: chunks_fts keeps unicode61 unchanged (chunk retrieval has different
needs and has been stable since M0).
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
    # 1. Drop old triggers (avoid dangling references while rebuilding the table)
    op.execute("DROP TRIGGER IF EXISTS querylog_au")
    op.execute("DROP TRIGGER IF EXISTS querylog_ad")
    op.execute("DROP TRIGGER IF EXISTS querylog_ai")
    # 2. Drop old history_fts table (unicode61 tokenizer)
    op.execute("DROP TABLE IF EXISTS history_fts")
    # 3. Rebuild with trigram tokenizer (supports CJK substring MATCH)
    op.execute(
        "CREATE VIRTUAL TABLE history_fts USING fts5("
        "query, answer, log_id UNINDEXED, "
        "tokenize='trigram'"
        ")"
    )
    # 4. Recreate same-named triggers (SQL identical to 0004; only the table tokenizer changed)
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
    # 5. Full backfill from querylog (old table was dropped, index must be rebuilt)
    op.execute(
        "INSERT INTO history_fts(query, answer, log_id) "
        "SELECT q.query, q.answer, q.id FROM querylog q"
    )


def downgrade() -> None:
    # Roll back to unicode61 (loses CJK substring MATCH capability, but keeps the FTS5 table structure)
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
