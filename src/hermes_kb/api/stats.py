"""M2-10 / M2-11：统计端点。

提供：
- GET /api/stats/tokens：累计 token 数 + 成本 + 按模型分组统计（管理员）
- GET /api/stats/tokens/recent：最近 N 条问答的 token 明细（管理员）
- GET /api/stats/dashboard：基础运营指标仪表盘（管理员）

M2-11 仪表盘指标：
- 文档数 / 分片数 / 总字符数
- 问答数 / 今日问答数 / 平均延迟
- token 用量 / 累计成本
- 反馈分布（赞 / 踩 / 无）
- 准确率（基于反馈：赞 / (赞 + 踩)）
- Top N 热门文档（按 match_count 排序）
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlmodel import select

from hermes_kb.api.audit import require_admin  # 复用管理员校验
from hermes_kb.database import get_session
from hermes_kb.models import Document, QueryLog, RecipeStats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/tokens", dependencies=[Depends(require_admin)])
async def token_stats() -> dict[str, Any]:
    """累计 token 用量 + 成本统计（管理员）。

    返回：
    - total_prompt_tokens / total_completion_tokens / total_tokens
    - total_cost_cny
    - by_model: [{model, count, prompt_tokens, completion_tokens, cost_cny}]
    """
    with get_session() as session:
        # 总量
        totals = session.exec(
            select(
                func.coalesce(func.sum(QueryLog.prompt_tokens), 0).label(
                    "prompt"
                ),
                func.coalesce(func.sum(QueryLog.completion_tokens), 0).label(
                    "completion"
                ),
                func.coalesce(func.sum(QueryLog.cost_cny), 0.0).label("cost"),
                func.count(QueryLog.id).label("count"),
            )
        ).first()
        # 按模型分组
        by_model_rows = session.exec(
            select(
                QueryLog.model_used,
                func.count(QueryLog.id).label("count"),
                func.coalesce(func.sum(QueryLog.prompt_tokens), 0).label(
                    "prompt"
                ),
                func.coalesce(func.sum(QueryLog.completion_tokens), 0).label(
                    "completion"
                ),
                func.coalesce(func.sum(QueryLog.cost_cny), 0.0).label("cost"),
            )
            .group_by(QueryLog.model_used)
            .order_by(func.sum(QueryLog.cost_cny).desc())
        ).all()
        return {
            "total_prompt_tokens": int(totals.prompt or 0),
            "total_completion_tokens": int(totals.completion or 0),
            "total_tokens": int((totals.prompt or 0) + (totals.completion or 0)),
            "total_cost_cny": round(float(totals.cost or 0.0), 6),
            "total_queries": int(totals.count or 0),
            "by_model": [
                {
                    "model": row.model_used,
                    "count": int(row.count or 0),
                    "prompt_tokens": int(row.prompt or 0),
                    "completion_tokens": int(row.completion or 0),
                    "cost_cny": round(float(row.cost or 0.0), 6),
                }
                for row in by_model_rows
            ],
        }


@router.get("/tokens/recent", dependencies=[Depends(require_admin)])
async def recent_token_usage(
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    """最近 N 条问答的 token 明细（管理员）。

    按 created_at 倒序，返回最近 limit 条记录的 token 用量。
    """
    with get_session() as session:
        logs = session.exec(
            select(QueryLog)
            .order_by(QueryLog.created_at.desc())
            .limit(limit)
        ).all()
        return {
            "total": len(logs),
            "limit": limit,
            "items": [
                {
                    "id": log.id,
                    "query": log.query,
                    "model_used": log.model_used,
                    "prompt_tokens": log.prompt_tokens,
                    "completion_tokens": log.completion_tokens,
                    "total_tokens": log.prompt_tokens + log.completion_tokens,
                    "cost_cny": round(float(log.cost_cny or 0.0), 6),
                    "latency_ms": log.latency_ms,
                    "created_at": log.created_at.isoformat()
                    if log.created_at
                    else None,
                }
                for log in logs
            ],
        }


# ---------------------------------------------------------------------------
# M2-11：仪表盘（基础运营指标）
# ---------------------------------------------------------------------------
@router.get("/dashboard", dependencies=[Depends(require_admin)])
async def dashboard(
    top_n: int = Query(default=10, ge=1, le=50, description="热门文档数量"),
) -> dict[str, Any]:
    """M2-11：基础运营指标仪表盘（管理员）。

    返回 5 项核心指标 + 热门文档：
    - 文档数 / 分片数 / 总字符数
    - 问答数 / 今日问答数 / 平均延迟
    - token 用量 / 累计成本
    - 反馈分布（赞 / 踩 / 无）
    - 准确率（赞 / (赞 + 踩)）
    - top_documents：按 match_count 倒序的前 N 篇文档

    设计：所有指标在单次请求内查完，避免前端多次往返；
    查询使用聚合 SQL，O(n) 扫描，10w 条数据 < 100ms。
    """
    # 今日零点（UTC），用于 "今日问答数"
    # 注意：QueryLog.created_at 由 _now_utc() 写入（无时区），此处用 naive UTC 对齐
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )

    with get_session() as session:
        # 1. 文档 / 分片 / 字符数
        doc_stats = session.exec(
            select(
                func.count(Document.doc_id).label("doc_count"),
                func.coalesce(func.sum(Document.chunk_count), 0).label(
                    "chunk_count"
                ),
                func.coalesce(
                    func.sum(func.char_length(Document.content)), 0
                ).label("total_chars"),
            )
        ).first()

        # 2. 问答数 / 今日问答数 / 平均延迟
        query_stats = session.exec(
            select(
                func.count(QueryLog.id).label("total_queries"),
                func.coalesce(
                    func.sum(
                        case(
                            (QueryLog.created_at >= today_start, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("today_queries"),
                func.coalesce(func.avg(QueryLog.latency_ms), 0).label(
                    "avg_latency_ms"
                ),
            )
        ).first()

        # 3. token 用量 / 累计成本
        token_stats = session.exec(
            select(
                func.coalesce(func.sum(QueryLog.prompt_tokens), 0).label(
                    "prompt"
                ),
                func.coalesce(func.sum(QueryLog.completion_tokens), 0).label(
                    "completion"
                ),
                func.coalesce(func.sum(QueryLog.cost_cny), 0.0).label("cost"),
            )
        ).first()

        # 4. 反馈分布
        feedback_rows = session.exec(
            select(
                QueryLog.feedback,
                func.count(QueryLog.id).label("count"),
            )
            .group_by(QueryLog.feedback)
        ).all()
        feedback_dist: dict[int, int] = {1: 0, -1: 0, 0: 0}
        for row in feedback_rows:
            feedback_dist[int(row.feedback)] = int(row.count)

        # 5. 准确率（赞 / (赞 + 踩)）
        up = feedback_dist[1]
        down = feedback_dist[-1]
        accuracy = round(up / (up + down), 4) if (up + down) > 0 else None

        # 6. Top N 热门文档（按 match_count）
        top_docs = session.exec(
            select(
                RecipeStats.doc_id,
                RecipeStats.match_count,
                RecipeStats.view_count,
                Document.title,
            )
            .join(Document, RecipeStats.doc_id == Document.doc_id, isouter=True)
            .order_by(RecipeStats.match_count.desc())
            .limit(top_n)
        ).all()

    return {
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "documents": {
            "count": int(doc_stats.doc_count or 0),
            "chunk_count": int(doc_stats.chunk_count or 0),
            "total_chars": int(doc_stats.total_chars or 0),
        },
        "queries": {
            "total": int(query_stats.total_queries or 0),
            "today": int(query_stats.today_queries or 0),
            "avg_latency_ms": round(float(query_stats.avg_latency_ms or 0), 2),
        },
        "tokens": {
            "prompt_tokens": int(token_stats.prompt or 0),
            "completion_tokens": int(token_stats.completion or 0),
            "total_tokens": int(
                (token_stats.prompt or 0) + (token_stats.completion or 0)
            ),
            "total_cost_cny": round(float(token_stats.cost or 0.0), 6),
        },
        "feedback": {
            "up": feedback_dist[1],
            "down": feedback_dist[-1],
            "none": feedback_dist[0],
            "accuracy": accuracy,
        },
        "top_documents": [
            {
                "doc_id": row.doc_id,
                "title": row.title or "(已删除)",
                "match_count": int(row.match_count or 0),
                "view_count": int(row.view_count or 0),
            }
            for row in top_docs
        ],
    }
