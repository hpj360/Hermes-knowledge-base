"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-23 04:50:23.139751+00:00

First migration: create all SQLModel tables + FTS5 full-text virtual tables +
sync triggers + vector table.

Coverage (aligned with database.py original create_all + _init_fts + _init_vec_table):
- SQLModel tables: document / chunk / tag / documenttag / querylog / recipestats /
  ingredientsubstitute / missingingredientstats / recipevariant
- FTS5 virtual table: chunks_fts (unicode61 tokenizer)
- Triggers: chunk_ai / chunk_ad / chunk_au (sync chunk <-> chunks_fts)
- Vector table: chunk_vec (JSON array storage, Python-side cosine similarity)
- Index: idx_chunk_vec_doc_id

Note: table names follow SQLModel defaults (lowercase class name, no underscore),
e.g. documenttag / querylog, matching SQLModel.metadata; FTS5/triggers/vector
table use raw SQL via op.execute() (alembic autogenerate does not support
FTS5 virtual tables).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # === SQLModel tables (autogenerate-produced, matching metadata) ===
    op.create_table('document',
        sa.Column('doc_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('source_type', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('file_type', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('source_path', sqlmodel.sql.sqltypes.AutoString(length=512), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False),
        sa.Column('category', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('source_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('season', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=True),
        sa.Column('hidden', sa.Boolean(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('image_url', sqlmodel.sql.sqltypes.AutoString(length=512), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('doc_id')
    )
    with op.batch_alter_table('document', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_document_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_document_source'), ['source'], unique=False)
        batch_op.create_index(batch_op.f('ix_document_title'), ['title'], unique=False)

    op.create_table('ingredientsubstitute',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('substitute', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('canonical', 'substitute', name='uq_ingredient_substitute')
    )
    with op.batch_alter_table('ingredientsubstitute', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ingredientsubstitute_canonical'), ['canonical'], unique=False)

    op.create_table('missingingredientstats',
        sa.Column('canonical', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('missing_count', sa.Integer(), nullable=False),
        sa.Column('last_missing_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('canonical')
    )
    op.create_table('querylog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query', sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('citations', sa.Text(), nullable=True),
        sa.Column('model_used', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('feedback', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('querylog', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_querylog_created_at'), ['created_at'], unique=False)

    op.create_table('tag',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('color', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('tag', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tag_name'), ['name'], unique=True)

    op.create_table('chunk',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_id', sa.Text(), nullable=True),
        sa.Column('idx', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('char_start', sa.Integer(), nullable=False),
        sa.Column('char_end', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['doc_id'], ['document.doc_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('chunk', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_chunk_doc_id'), ['doc_id'], unique=False)

    op.create_table('documenttag',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_id', sa.Text(), nullable=True),
        sa.Column('tag_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['doc_id'], ['document.doc_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('documenttag', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_documenttag_doc_id'), ['doc_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_documenttag_tag_id'), ['tag_id'], unique=False)

    op.create_table('recipestats',
        sa.Column('doc_id', sa.Text(), nullable=False),
        sa.Column('match_count', sa.Integer(), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=False),
        sa.Column('weekly_match_count', sa.Integer(), nullable=False),
        sa.Column('last_matched_at', sa.DateTime(), nullable=True),
        sa.Column('last_viewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['doc_id'], ['document.doc_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('doc_id')
    )
    op.create_table('recipevariant',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('base_doc_id', sa.Text(), nullable=True),
        sa.Column('variant_doc_id', sa.Text(), nullable=True),
        sa.Column('variant_note', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['base_doc_id'], ['document.doc_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['variant_doc_id'], ['document.doc_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('recipevariant', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recipevariant_base_doc_id'), ['base_doc_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_recipevariant_variant_doc_id'), ['variant_doc_id'], unique=False)

    # === FTS5 virtual table + sync triggers (autogenerate does not support FTS5, raw SQL) ===
    # Matches database.py._init_fts exactly
    op.execute(
        "CREATE VIRTUAL TABLE chunks_fts USING fts5("
        "text, doc_id UNINDEXED, chunk_rowid UNINDEXED, "
        "tokenize='unicode61'"
        ")"
    )
    op.execute(
        "CREATE TRIGGER chunk_ai AFTER INSERT ON chunk BEGIN "
        "INSERT INTO chunks_fts(text, doc_id, chunk_rowid) "
        "VALUES (new.text, new.doc_id, new.id); "
        "END"
    )
    op.execute(
        "CREATE TRIGGER chunk_ad AFTER DELETE ON chunk BEGIN "
        "DELETE FROM chunks_fts WHERE chunk_rowid = old.id; "
        "END"
    )
    op.execute(
        "CREATE TRIGGER chunk_au AFTER UPDATE ON chunk BEGIN "
        "DELETE FROM chunks_fts WHERE chunk_rowid = old.id; "
        "INSERT INTO chunks_fts(text, doc_id, chunk_rowid) "
        "VALUES (new.text, new.doc_id, new.id); "
        "END"
    )

    # === Vector table chunk_vec (matches database.py._init_vec_table) ===
    # chunk_vec_ann (vec0 virtual table) + chunk_ad_vec trigger are NOT created here:
    # vec0 requires the sqlite-vec extension, loaded per-connection at runtime
    # (database.py event listener); alembic migration engine does not load it.
    # So chunk_vec_ann is created at runtime by database.py._init_vec_table via
    # CREATE VIRTUAL TABLE IF NOT EXISTS, ensuring the table is only built when
    # the extension is available.
    op.execute(
        "CREATE TABLE chunk_vec ("
        "chunk_rowid INTEGER PRIMARY KEY, "
        "doc_id TEXT REFERENCES document(doc_id) ON DELETE CASCADE, "
        "vec TEXT NOT NULL"
        ")"
    )
    op.execute(
        "CREATE INDEX idx_chunk_vec_doc_id ON chunk_vec(doc_id)"
    )


def downgrade() -> None:
    # === Vector table / triggers / FTS5 (reverse order) ===
    op.execute("DROP INDEX IF EXISTS idx_chunk_vec_doc_id")
    op.execute("DROP TABLE IF EXISTS chunk_vec")
    op.execute("DROP TRIGGER IF EXISTS chunk_au")
    op.execute("DROP TRIGGER IF EXISTS chunk_ad")
    op.execute("DROP TRIGGER IF EXISTS chunk_ai")
    op.execute("DROP TABLE IF EXISTS chunks_fts")

    # === SQLModel tables (reverse order, autogenerate-produced) ===
    with op.batch_alter_table('recipevariant', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recipevariant_variant_doc_id'))
        batch_op.drop_index(batch_op.f('ix_recipevariant_base_doc_id'))

    op.drop_table('recipevariant')
    op.drop_table('recipestats')
    with op.batch_alter_table('documenttag', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documenttag_tag_id'))
        batch_op.drop_index(batch_op.f('ix_documenttag_doc_id'))

    op.drop_table('documenttag')
    with op.batch_alter_table('chunk', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chunk_doc_id'))

    op.drop_table('chunk')
    with op.batch_alter_table('tag', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tag_name'))

    op.drop_table('tag')
    with op.batch_alter_table('querylog', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_querylog_created_at'))

    op.drop_table('querylog')
    op.drop_table('missingingredientstats')
    with op.batch_alter_table('ingredientsubstitute', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ingredientsubstitute_canonical'))

    op.drop_table('ingredientsubstitute')
    with op.batch_alter_table('document', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_document_title'))
        batch_op.drop_index(batch_op.f('ix_document_source'))
        batch_op.drop_index(batch_op.f('ix_document_category'))

    op.drop_table('document')
