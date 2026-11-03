"""网关检索契约端点：GET /kb/search（供 hermes 主仓网关 /wb/kb/search 代理调用）。

契约（P2-1 补齐）：主仓 ``workbench/server_routes/kb.py::h_get_kb_search`` 会向上游
``{HERMES_KB_BASE_URL}/kb/search?q=...`` 发 GET 并原样转发响应。此前 kb 侧没有该
端点，导致主仓侧检索代理永远 502（契约期望与实现不对齐）。

本路由**不带 /api 前缀**（上游契约即 /kb/search 路径），仅做检索融合排序（BM25+
向量 RRF），不调用 LLM——供驾驶舱全局搜索/知识入口页消费，成本可控。
鉴权：由调用方（主仓网关）侧统一鉴权；本端点默认 loopback 服务面，kb 仓自身
前端不使用它（前端走 /api/ask）。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from hermes_kb.config import get_settings
from hermes_kb.retrieval import HybridRetriever, RetrievalHit

router = APIRouter()


def _hit_dict(hit: RetrievalHit) -> dict[str, str | float]:
    """把 RetrievalHit 压缩成网关响应条目（snippet 截断避免大响应体）。"""
    return {
        "doc_id": hit.doc_id,
        "title": hit.title,
        "snippet": hit.text[:400],
        "score": round(hit.score, 6),
        "source": hit.source,
    }


@router.get("/kb/search")
def gateway_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(8, ge=1, le=50),
) -> dict[str, object]:
    """知识检索（无 LLM 生成）：主仓网关 /wb/kb/search 的唯一上游契约。"""
    settings = get_settings()
    truncated = q[: settings.query_max_length].strip()
    if not truncated:
        # 局部改写 FastAPI Query 语义：主仓侧契约要求 strip 后非空（h_get_kb_search
        # 在向上游转发前已对 q 做 strip 校验），宽度保持 422 一致。
        raise HTTPException(status_code=422, detail="query 'q' must not be blank")

    retriever = HybridRetriever()
    hits = retriever.retrieve(truncated, top_k=top_k)
    results = [_hit_dict(hit) for hit in hits]
    return {
        "query": truncated,
        "results": results,
        "count": len(results),
        "engine": "kb/hybrid-rrf",
    }
