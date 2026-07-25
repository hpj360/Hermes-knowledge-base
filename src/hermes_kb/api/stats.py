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

    隐私：query 字段截断到 50 字符，避免泄露用户问答原文 PII
    （此端点用于 token 用量分析，不需要完整 query 内容）。
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
                    # 截断 query 防泄露 PII（仅用于 token 分析，不需要全文）
                    "query": (log.query or "")[:50],
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
        # 1. 文档 / 分片 / 字符数（独立表，单独查询）
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

        # 2-4. 合并 QueryLog 的 3 次扫描为 1 次：
        # 问答统计 + token 用量 + 反馈分布（按 feedback 分组无法与聚合合并，
        # 但问答统计 + token 用量可在单次扫描完成，反馈分布单独一次）
        query_token_stats = session.exec(
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
                # token 用量（同一次扫描聚合）
                func.coalesce(func.sum(QueryLog.prompt_tokens), 0).label(
                    "prompt"
                ),
                func.coalesce(func.sum(QueryLog.completion_tokens), 0).label(
                    "completion"
                ),
                func.coalesce(func.sum(QueryLog.cost_cny), 0.0).label("cost"),
                # 反馈分布（用条件聚合避免 GROUP BY，仍能在单次扫描完成）
                func.coalesce(
                    func.sum(
                        case(
                            (QueryLog.feedback == 1, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("up_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (QueryLog.feedback == -1, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("down_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (QueryLog.feedback == 0, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("none_count"),
            )
        ).first()

        # 5. Top N 热门文档（按 match_count）
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

    # 准确率（赞 / (赞 + 踩)）
    up = int(query_token_stats.up_count or 0)
    down = int(query_token_stats.down_count or 0)
    accuracy = round(up / (up + down), 4) if (up + down) > 0 else None

    return {
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "documents": {
            "count": int(doc_stats.doc_count or 0),
            "chunk_count": int(doc_stats.chunk_count or 0),
            "total_chars": int(doc_stats.total_chars or 0),
        },
        "queries": {
            "total": int(query_token_stats.total_queries or 0),
            "today": int(query_token_stats.today_queries or 0),
            "avg_latency_ms": round(float(query_token_stats.avg_latency_ms or 0), 2),
        },
        "tokens": {
            "prompt_tokens": int(query_token_stats.prompt or 0),
            "completion_tokens": int(query_token_stats.completion or 0),
            "total_tokens": int(
                (query_token_stats.prompt or 0)
                + (query_token_stats.completion or 0)
            ),
            "total_cost_cny": round(float(query_token_stats.cost or 0.0), 6),
        },
        "feedback": {
            "up": up,
            "down": down,
            "none": int(query_token_stats.none_count or 0),
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
