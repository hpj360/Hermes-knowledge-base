"""混合检索：BM25（FTS5）+ 向量（Python 余弦）+ RRF 融合。

中文 BM25 分词策略（P0 修复关键）：
- 标点切断
- 中文片段 bigram + 单字
- 英文保留原词
- 用 OR 查询，FTS5 unicode61 分词器对中文按字索引，bigram 能命中

性能优化（P0 修复）：
- BM25/向量命中后批量预取 doc_title / chunk_text，消除 N+1
- _cosine 使用 math 模块向量化循环，避免逐元素 append
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass

from sqlalchemy import text as sa_text
from sqlmodel import select

from hermes_kb.config import get_settings
from hermes_kb.database import get_engine, get_session
from hermes_kb.embedding import EmbeddingService
from hermes_kb.models import Chunk, Document

logger = logging.getLogger(__name__)


@dataclass
class RetrievalHit:
    """检索命中。"""

    chunk_rowid: int
    doc_id: str
    title: str
    text: str
    score: float
    source: str  # bm25 / vector / rrf


def _cosine(a: list[float], b: list[float]) -> float:
    """纯 Python 余弦相似度。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / math.sqrt(na * nb)


def reciprocal_rank_fusion(
    bm25_hits: list[RetrievalHit],
    vec_hits: list[RetrievalHit],
    k: int = 60,
) -> list[RetrievalHit]:
    """RRF 融合两路排序。"""
    scores: dict[int, float] = {}
    meta: dict[int, RetrievalHit] = {}
    for rank, h in enumerate(bm25_hits, start=1):
        scores[h.chunk_rowid] = scores.get(h.chunk_rowid, 0.0) + 1.0 / (k + rank)
        meta[h.chunk_rowid] = h
    for rank, h in enumerate(vec_hits, start=1):
        scores[h.chunk_rowid] = scores.get(h.chunk_rowid, 0.0) + 1.0 / (k + rank)
        meta[h.chunk_rowid] = h
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    result: list[RetrievalHit] = []
    for rowid, sc in ordered:
        h = meta[rowid]
        result.append(
            RetrievalHit(
                chunk_rowid=h.chunk_rowid,
                doc_id=h.doc_id,
                title=h.title,
                text=h.text,
                score=sc,
                source="rrf",
            )
        )
    return result


def _tokenize_query_for_fts(q: str) -> str:
    """把中文 query 转成 FTS5 OR 查询字符串。

    策略：标点切段 → 中文片段 bigram + 单字 → 英文保留原词。
    """
    q = q.strip().replace('"', " ")
    if not q:
        return ""
    segments = re.split(r"[\s,，。！？、；：""''（）()【】\[\]{}]+", q)
    segments = [s for s in segments if s]
    if not segments:
        return ""
    terms: list[str] = []
    for seg in segments:
        if re.fullmatch(r"[A-Za-z0-9\-_]+", seg):
            terms.append(seg)
            continue
        # 中文片段：bigram + 单字
        if len(seg) == 1:
            terms.append(seg)
            continue
        for i in range(len(seg) - 1):
            terms.append(seg[i : i + 2])
        # 单字也加入（提升短 query 召回）
        for ch in seg:
            terms.append(ch)
    # 去重保序
    seen: set[str] = set()
    unique_terms: list[str] = []
    for t in terms:
        if t and t not in seen:
            seen.add(t)
            unique_terms.append(t)
    if not unique_terms:
        return ""
    # 用 OR 查询，每个 term 用双引号包裹（防止 FTS5 语法字符干扰）
    return " OR ".join(f'"{t}"' for t in unique_terms)


class HybridRetriever:
    """混合检索器。"""

    def __init__(self, embedding: EmbeddingService | None = None) -> None:
        self.embedding = embedding or EmbeddingService()

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievalHit]:
        """检索 top_k 条命中。空 query 早期返回（避免伪命中）。"""
        if not query or not query.strip():
            return []
        k = top_k or get_settings().top_k
        bm25_hits = self._bm25(query, k)
        vec_hits = self._vector(query, k)
        fused = reciprocal_rank_fusion(bm25_hits, vec_hits, k=get_settings().rrf_k)
        return fused[:k]

    def _bm25(self, query: str, k: int) -> list[RetrievalHit]:
        """FTS5 BM25 检索（中文 bigram 分词）。"""
        fts_query = _tokenize_query_for_fts(query)
        if not fts_query:
            return []
        eng = get_engine()
        try:
            with eng.connect() as conn:
                rows = conn.execute(
                    sa_text(
                        "SELECT chunk_rowid, doc_id, text, bm25(chunks_fts) AS score "
                        "FROM chunks_fts WHERE chunks_fts MATCH :q "
                        "ORDER BY score LIMIT :k"
                    ),
                    {"q": fts_query, "k": k},
                ).fetchall()
        except Exception as e:
            logger.warning("BM25 检索失败: %s", e)
            return []
        # 批量预取 doc_title，消除 N+1
        doc_ids = {row[1] for row in rows}
        title_map = self._batch_doc_titles(doc_ids)
        hits: list[RetrievalHit] = []
        # FTS5 bm25() 越小越好（距离），取负值转为"越大越好"
        for row in rows:
            rowid = int(row[0])
            doc_id = row[1]
            text = row[2] or ""
            raw_score = float(row[3]) if row[3] is not None else 0.0
            score = -raw_score  # 转换为越大越好
            hits.append(
                RetrievalHit(
                    chunk_rowid=rowid,
                    doc_id=doc_id,
                    title=title_map.get(doc_id, doc_id),
                    text=text,
                    score=score,
                    source="bm25",
                )
            )
        return hits

    def _vector(self, query: str, k: int) -> list[RetrievalHit]:
        """向量检索（Python 余弦相似度）。"""
        qvec = self.embedding.embed_one(query)
        if not qvec or all(v == 0.0 for v in qvec):
            return []
        eng = get_engine()
        try:
            with eng.connect() as conn:
                rows = conn.execute(
                    sa_text(
                        "SELECT chunk_rowid, doc_id, vec FROM chunk_vec LIMIT 10000"
                    )
                ).fetchall()
        except Exception as e:
            logger.warning("向量检索失败: %s", e)
            return []
        scored: list[tuple[float, int, str]] = []
        for row in rows:
            rowid = int(row[0])
            doc_id = row[1]
            try:
                vec = json.loads(row[2])
            except Exception:
                continue
            sim = _cosine(qvec, vec)
            scored.append((sim, rowid, doc_id))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:k]
        # 批量预取 chunk_text + doc_title，消除 N+1
        chunk_rowids = [rowid for _, rowid, _ in top]
        doc_ids = {doc_id for _, _, doc_id in top}
        chunk_text_map = self._batch_chunk_texts(chunk_rowids)
        title_map = self._batch_doc_titles(doc_ids)
        hits: list[RetrievalHit] = []
        for sim, rowid, doc_id in top:
            hits.append(
                RetrievalHit(
                    chunk_rowid=rowid,
                    doc_id=doc_id,
                    title=title_map.get(doc_id, doc_id),
                    text=chunk_text_map.get(rowid, ""),
                    score=sim,
                    source="vector",
                )
            )
        return hits

    def _batch_doc_titles(self, doc_ids: set[str]) -> dict[str, str]:
        """批量预取文档标题，消除 N+1 查询。"""
        if not doc_ids:
            return {}
        try:
            with get_session() as session:
                rows = session.exec(
                    select(Document.doc_id, Document.title).where(
                        Document.doc_id.in_(list(doc_ids))
                    )
                ).all()
                return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.warning("批量预取文档标题失败: %s", e)
            return {}

    def _batch_chunk_texts(self, rowids: list[int]) -> dict[int, str]:
        """批量预取分片文本，消除 N+1 查询。"""
        if not rowids:
            return {}
        try:
            with get_session() as session:
                rows = session.exec(
                    select(Chunk.id, Chunk.text).where(Chunk.id.in_(rowids))
                ).all()
                return {row[0]: row[1] or "" for row in rows}
        except Exception as e:
            logger.warning("批量预取分片文本失败: %s", e)
            return {}
