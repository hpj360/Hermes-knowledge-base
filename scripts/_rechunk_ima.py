#!/usr/bin/env python3
"""IMA 文档重新分片 + 重新向量化脚本。

在 _enrich_ima_content.py 之后运行：
1. 删除 IMA 文档的旧 chunks + chunk_vec
2. 用富化后的 content 重新分片
3. 重新生成 embeddings 并写入 chunk_vec

幂等：每次运行都会重建 chunks，可安全重复运行。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import text as sa_text
from sqlmodel import select

from hermes_kb.config import get_settings
from hermes_kb.database import _SQLITE_VEC_AVAILABLE, get_session
from hermes_kb.embedding import EmbeddingService
from hermes_kb.models import Chunk, Document
from hermes_kb.parser import DocumentParser
from hermes_kb.rag import _get_chunk_strategy


def main() -> int:
    settings = get_settings()
    parser = DocumentParser()
    embedder = EmbeddingService()
    category = "IMA资料"
    chunk_size, overlap = _get_chunk_strategy(category)
    print(f"分片策略：category={category}, chunk_size={chunk_size}, overlap={overlap}")
    print(f"Embedding provider: {settings.embedding_provider}")

    rechunked = 0
    total_chunks = 0
    skipped_hidden = 0

    with get_session() as s:
        docs = s.exec(select(Document).where(Document.source == "ima")).all()
        print(f"扫描 {len(docs)} 篇 IMA 文档...")

        for doc in docs:
            # 始终删除旧 chunks（含 chunk_vec 通过 CASCADE 或手动），
            # 确保隐藏文档的旧 chunks 也被清理（避免被检索召回）
            old_chunks = s.exec(select(Chunk).where(Chunk.doc_id == doc.doc_id)).all()
            for c in old_chunks:
                # 删除 chunk_vec JSON
                s.execute(
                    sa_text("DELETE FROM chunk_vec WHERE chunk_rowid = :rid"),
                    {"rid": c.id},
                )
                # 删除 chunk_vec_ann
                if _SQLITE_VEC_AVAILABLE:
                    try:
                        s.execute(
                            sa_text("DELETE FROM chunk_vec_ann WHERE rowid = :rid"),
                            {"rid": c.id},
                        )
                    except Exception:  # noqa: BLE001,S110 — 表可能不存在
                        pass
                s.delete(c)

            # 隐藏文档（如已标记的重复条目）不创建新 chunks，避免重复内容被检索
            if doc.hidden:
                doc.chunk_count = 0
                s.add(doc)
                skipped_hidden += 1
                continue

            # 重新分片
            chunks = parser.chunk(
                doc.content or "",
                chunk_size=chunk_size,
                overlap=overlap,
            )
            chunk_texts = [c[2] for c in chunks]
            vectors = embedder.embed(chunk_texts) if chunk_texts else []

            # 写入新 chunks
            for i, (start, end, text) in enumerate(chunks):
                c = Chunk(
                    doc_id=doc.doc_id,
                    idx=i,
                    text=text,
                    char_start=start,
                    char_end=end,
                )
                s.add(c)
                s.flush()
                rowid = c.id
                vec = vectors[i] if i < len(vectors) else [0.0] * embedder.dim
                # 写 chunk_vec JSON
                s.execute(
                    sa_text(
                        "INSERT INTO chunk_vec (chunk_rowid, doc_id, vec) "
                        "VALUES (:rowid, :doc_id, :vec)"
                    ),
                    {"rowid": rowid, "doc_id": doc.doc_id, "vec": json.dumps(vec)},
                )
                # 写 chunk_vec_ann
                if _SQLITE_VEC_AVAILABLE and len(vec) == settings.embedding_dim:
                    try:
                        import sqlite_vec
                        s.execute(
                            sa_text(
                                "INSERT INTO chunk_vec_ann(rowid, embedding) "
                                "VALUES (:rowid, :emb)"
                            ),
                            {
                                "rowid": rowid,
                                "emb": sqlite_vec.serialize_float32(vec),
                            },
                        )
                    except Exception:  # noqa: BLE001,S110
                        pass

            # 更新 doc.chunk_count
            doc.chunk_count = len(chunks)
            s.add(doc)
            rechunked += 1
            total_chunks += len(chunks)

        s.commit()

    print(f"重新分片完成：{rechunked} 篇文档，共 {total_chunks} 个 chunks"
          f"（{skipped_hidden} 篇隐藏文档跳过分片）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
