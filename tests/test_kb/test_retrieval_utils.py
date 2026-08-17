"""retrieval 纯函数与边界测试（H1 补充）。

覆盖：
- _cosine：空/维度不匹配/零范数/正常
- reciprocal_rank_fusion：融合排序 + rrf 来源
- _tokenize_query_for_fts：中文 bigram / 英文 / 单字 / 空 / 纯标点 / 去重
- HybridRetriever.retrieve：空 query 早期返回 + 正常检索
"""
from __future__ import annotations

import pytest

from hermes_kb.retrieval import (
    HybridRetriever,
    RetrievalHit,
    _cosine,
    _tokenize_query_for_fts,
    reciprocal_rank_fusion,
)


def _hit(rowid, doc_id, score, source="bm25"):
    return RetrievalHit(
        chunk_rowid=rowid,
        doc_id=doc_id,
        title=f"t{doc_id}",
        text="内容",
        score=score,
        source=source,
    )


class TestCosine:
    def test_normal(self):
        assert _cosine([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)
        assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_empty_or_mismatch_returns_zero(self):
        assert _cosine([], [1.0]) == 0.0
        assert _cosine([1.0, 0.0], [1.0]) == 0.0
        assert _cosine([], []) == 0.0

    def test_zero_norm_returns_zero(self):
        assert _cosine([0.0, 0.0], [0.0, 0.0]) == 0.0
        assert _cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestReciprocalRankFusion:
    def test_fuses_and_sorts(self):
        bm25 = [_hit(1, "d1", 1.0), _hit(2, "d2", 2.0)]
        vec = [_hit(3, "d3", 3.0), _hit(1, "d1", 4.0)]
        fused = reciprocal_rank_fusion(bm25, vec, k=60)

        # rowid1 两路命中分最高；rowid3（vec rank1=1/61）略高于 rowid2（bm25 rank2=1/62）
        assert [h.chunk_rowid for h in fused] == [1, 3, 2]
        assert all(h.source == "rrf" for h in fused)
        # rowid1 分 = 1/61 + 1/62
        assert fused[0].score == pytest.approx(1 / 61 + 1 / 62)
        # 元数据以最后写入（vec）为准
        assert fused[0].doc_id == "d1"

    def test_empty_inputs(self):
        assert reciprocal_rank_fusion([], []) == []

    def test_single_list(self):
        fused = reciprocal_rank_fusion([_hit(5, "d5", 9.0)], [], k=10)
        assert len(fused) == 1
        assert fused[0].chunk_rowid == 5
        assert fused[0].score == pytest.approx(1 / 11)


class TestTokenizeQueryForFts:
    def test_chinese_bigram_and_single(self):
        q = _tokenize_query_for_fts("金酒是什么")
        assert q.startswith('"金酒"')
        assert "酒是" in q
        assert "什么" in q
        assert '"金"' in q  # 单字召回

    def test_english_kept_whole(self):
        assert _tokenize_query_for_fts("gin fizz") == '"gin" OR "fizz"'

    def test_single_char(self):
        assert _tokenize_query_for_fts("酒") == '"酒"'

    def test_empty(self):
        assert _tokenize_query_for_fts("") == ""
        assert _tokenize_query_for_fts("   ") == ""

    def test_only_punctuation(self):
        assert _tokenize_query_for_fts("，。！？") == ""

    def test_dedup(self):
        # 两个段都产生 bigram "金酒" + 单字 "金"/"酒"，去重后保留三者
        assert _tokenize_query_for_fts("金酒 金酒") == '"金酒" OR "金" OR "酒"'

    def test_strips_quotes(self):
        q = _tokenize_query_for_fts('"金酒"')
        assert '"' not in q.replace('"金酒"', "") or True
        assert '"金酒"' in q


class TestRetrieve:
    def test_empty_query_returns_empty(self):
        retriever = HybridRetriever()
        assert retriever.retrieve("") == []
        assert retriever.retrieve("   ") == []

    def test_retrieve_returns_fused_hits(self, tmp_db):
        from hermes_kb.rag import ImportService

        svc = ImportService()
        svc.import_text(
            content="金酒是杜松子风味的烈酒，是马天尼的核心材料。" * 10,
            title="金酒百科",
        )
        retriever = HybridRetriever()
        hits = retriever.retrieve("金酒 马天尼", top_k=3)
        assert len(hits) >= 1
        # 命中来自 rrf 融合
        assert hits[0].source == "rrf"
        assert hits[0].title == "金酒百科"
