"""M2-10：token 用量统计端点。

提供：
- GET /api/stats/tokens：累计 token 数 + 成本 + 按模型分组统计
- GET /api/stats/tokens/recent：最近 N 条问答的 token 明细
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import select

from hermes_kb.api.audit import require_admin  # 复用管理员校验
from hermes_kb.database import get_session
from hermes_kb.models import QueryLog

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
