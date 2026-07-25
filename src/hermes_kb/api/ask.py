"""问答端点：ask/ask-stream/history/feedback/seed/seed-recipes。"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import select

from hermes_kb.api.deps import get_importer, get_rag, require_age_gate, require_auth
from hermes_kb.audit import extract_user, log_action, log_ask_sampled
from hermes_kb.database import get_session
from hermes_kb.models import Document, QueryLog
from hermes_kb.rag import ImportService, RAGEngine
from hermes_kb.seed import SEED_DOCS
from hermes_kb.seed_recipes import SEED_RECIPES

router = APIRouter(prefix="/api", tags=["ask"])


class AskReq(BaseModel):
    query: str = Field(..., max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class FeedbackReq(BaseModel):
    feedback: int = Field(..., ge=-1, le=1)  # 1=up / -1=down / 0=none


@router.post("/ask", dependencies=[Depends(require_auth), Depends(require_age_gate)])
async def ask(
    req: AskReq,
    rag: RAGEngine = Depends(get_rag),
    payload: dict[str, Any] | None = Depends(require_auth),
) -> dict[str, Any]:
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    # P2-6：将同步 RAG 调用卸载到线程池，避免阻塞事件循环
    result = await anyio.to_thread.run_sync(rag.answer, req.query, req.top_k)
    # M2-08：ask 采样 10% 审计（hash(query) % 10 == 0，确定性可复现）
    log_ask_sampled(
        query=req.query,
        user=extract_user(payload),
        model_used=result.model_used,
        latency_ms=result.latency_ms,
        log_id=None,  # answer_id 为 UUID，按业务标识记录
    )
    return result.to_dict()


@router.post("/ask/stream", dependencies=[Depends(require_auth), Depends(require_age_gate)])
async def ask_stream(
    req: AskReq,
    rag: RAGEngine = Depends(get_rag),
    payload: dict[str, Any] | None = Depends(require_auth),
) -> StreamingResponse:
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")

    # M2-08：流式问答采样审计（在请求开始时记录，避免流式完成后再写）
    log_ask_sampled(
        query=req.query,
        user=extract_user(payload),
        model_used="stream",
        latency_ms=0,
    )

    async def gen():
        async for chunk in rag.answer_stream(req.query, top_k=req.top_k):
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# 历史 + 反馈

# M2-07：历史搜索关键词净化——剥离 SQL/regex 元字符，避免 LIKE 注入与意外语义。
# 保留中文 / 字母 / 数字 / 空格。多空白折叠为单空格。
# 注：\w 在 re.UNICODE 下包含下划线，但下划线是 LIKE 通配符，需在净化后单独转义。
_SEARCH_SAFE_RE = re.compile(r'[^\w\u4e00-\u9fff\s]', re.UNICODE)
_WHITESPACE_RE = re.compile(r'\s+')
# 高亮 mark 标签（前端直接渲染，已转义查询词避免 XSS）
_HIGHLIGHT_PRE = '<mark>'
_HIGHLIGHT_POST = '</mark>'
# snippet 最大长度（前后截断）
_SNIPPET_MAX = 80
# history 关键词最大长度（防超长 LIKE 拖慢大表查询）
_Q_MAX_LENGTH = 200


def _sanitize_search_q(q: str) -> str:
    """净化搜索关键词：剥离特殊字符 + 折叠空白。

    返回空串表示无有效关键词（回退普通查询）。
    注：净化后仍可能含 `_`（LIKE 通配符），需在构造 LIKE pattern 时转义。
    """
    cleaned = _SEARCH_SAFE_RE.sub(' ', q)
    cleaned = _WHITESPACE_RE.sub(' ', cleaned).strip()
    # 长度截断，防超长输入拖慢 LIKE 全表扫描
    if len(cleaned) > _Q_MAX_LENGTH:
        cleaned = cleaned[:_Q_MAX_LENGTH]
    return cleaned


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符（% 和 _），避免用户输入意外匹配。

    配合 LIKE ... ESCAPE '\\' 使用。
    """
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _highlight(text: str, keyword: str) -> str | None:
    """在 text 中高亮 keyword（大小写不敏感，转义 regex 元字符）。

    返回带 <mark> 标签的文本。无命中返回 None。

    安全：先用 html.escape 转义 text 全文，避免 answer/query 中嵌入的
    HTML 标签被前端 v-html 渲染导致 XSS。
    """
    if not text or not keyword:
        return None
    # 先转义全文，防 XSS（answer 可能含 <script> 等用户输入）
    import html

    safe_text = html.escape(text)
    pattern = re.escape(keyword)
    highlighted = re.sub(
        pattern,
        lambda m: f"{_HIGHLIGHT_PRE}{m.group()}{_HIGHLIGHT_POST}",
        safe_text,
        flags=re.IGNORECASE,
    )
    if _HIGHLIGHT_PRE not in highlighted:
        return None
    return highlighted


def _make_snippet(text: str, keyword: str, max_len: int = _SNIPPET_MAX) -> str | None:
    """生成 keyword 周围的 snippet（前后截断 + 高亮）。

    无命中返回 None。

    安全：先转义全文再高亮，防 XSS。
    """
    if not text or not keyword:
        return None
    import html

    safe_text = html.escape(text)
    match = re.search(re.escape(keyword), safe_text, flags=re.IGNORECASE)
    if not match:
        return None
    start = max(0, match.start() - max_len // 2)
    end = min(len(safe_text), match.end() + max_len // 2)
    snippet = safe_text[start:end]
    if start > 0:
        snippet = '...' + snippet
    if end < len(safe_text):
        snippet = snippet + '...'
    # 高亮 snippet 中的 keyword
    return re.sub(
        re.escape(keyword),
        lambda m: f"{_HIGHLIGHT_PRE}{m.group()}{_HIGHLIGHT_POST}",
        snippet,
        flags=re.IGNORECASE,
    )


def _parse_date(date_str: str | None, *, end_of_day: bool = False) -> datetime | None:
    """解析 YYYY-MM-DD 日期字符串为 datetime。

    end_of_day=True 时返回当日 23:59:59，便于 `<=` 闭区间筛选。
    解析失败返回 None。
    """
    if not date_str or not date_str.strip():
        return None
    try:
        d = datetime.strptime(date_str.strip()[:10], '%Y-%m-%d')
    except ValueError:
        return None
    if end_of_day:
        d = d + timedelta(days=1) - timedelta(seconds=1)
    return d


def _format_history_item(
    log: QueryLog,
    *,
    query_highlight: str | None = None,
    answer_snippet: str | None = None,
) -> dict[str, Any]:
    """统一格式化历史条目。"""
    created_at = log.created_at
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    elif created_at is not None:
        created_at = str(created_at)
    return {
        "id": log.id,
        "query": log.query,
        "answer": log.answer,
        "citations": json.loads(log.citations or "[]"),
        "model_used": log.model_used,
        "latency_ms": log.latency_ms,
        "feedback": log.feedback,
        "created_at": created_at,
        # M2-07：高亮字段（仅搜索路径返回非 None）
        "query_highlight": query_highlight,
        "answer_snippet": answer_snippet,
    }


@router.get("/history", dependencies=[Depends(require_auth)])
async def history(
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=200, description="关键词搜索"),
    feedback: int | None = Query(default=None, ge=-1, le=1, description="反馈筛选：1=赞/-1=踩/0=无"),
    date_from: str | None = Query(default=None, description="起始日期 YYYY-MM-DD（含）"),
    date_to: str | None = Query(default=None, description="结束日期 YYYY-MM-DD（含）"),
) -> dict[str, Any]:
    """M2-07：历史搜索 + 筛选。

    - 无 q：按时间倒序普通查询，支持 feedback / date_from / date_to 筛选
    - 有 q：用 LIKE 子串匹配（覆盖所有中文场景），返回 query_highlight 与 answer_snippet
    - 验收：响应 < 200ms（LIKE 在 1w 条以内性能足够；超大规模可切 FTS5）

    注：history_fts 表已建（迁移 0004）并随 querylog 自动同步，
    当前 API 暂用 LIKE 保证中文子串召回（FTS5 unicode61 对连续中文
    整体作为单 token，前缀匹配无法命中中间子串）。后续大数据量可切 FTS5。

    性能/安全：
    - 计数下推到 SQL COUNT(*)，避免 len(.all()) 全量加载到内存
    - LIKE pattern 转义 % 和 _ 通配符，避免用户输入意外匹配
    """
    limit = max(1, min(limit, 500))
    dt_from = _parse_date(date_from, end_of_day=False)
    dt_to = _parse_date(date_to, end_of_day=True)
    search_q = _sanitize_search_q(q) if q else ''

    with get_session() as session:
        stmt = select(QueryLog)
        if feedback is not None:
            stmt = stmt.where(QueryLog.feedback == feedback)
        if dt_from is not None:
            stmt = stmt.where(QueryLog.created_at >= dt_from)
        if dt_to is not None:
            stmt = stmt.where(QueryLog.created_at <= dt_to)
        if search_q:
            # LIKE 子串匹配（query OR answer），覆盖中文所有位置
            # 转义 % 和 _ 通配符，避免用户输入的 _ 意外匹配任意单字符
            escaped_q = _escape_like(search_q)
            like_pattern = f"%{escaped_q}%"
            stmt = stmt.where(
                (QueryLog.query.like(like_pattern, escape='\\'))
                | (QueryLog.answer.like(like_pattern, escape='\\'))
            )
        # 总数下推到 SQL COUNT(*)，避免全量加载到内存（10w 行 OOM 风险）
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.exec(count_stmt).one()
        # 分页 + 倒序
        stmt = stmt.order_by(QueryLog.created_at.desc()).offset(offset).limit(limit)
        logs = session.exec(stmt).all()
        items: list[dict[str, Any]] = []
        for log in logs:
            if search_q:
                q_h = _highlight(log.query, search_q)
                a_s = _make_snippet(log.answer, search_q)
            else:
                q_h = None
                a_s = None
            items.append(
                _format_history_item(log, query_highlight=q_h, answer_snippet=a_s)
            )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "q": q or "",
        "items": items,
    }


@router.post("/feedback/{log_id}", dependencies=[Depends(require_auth)])
async def feedback(
    log_id: int,
    req: FeedbackReq,
    payload: dict[str, Any] | None = Depends(require_auth),
) -> dict[str, Any]:
    with get_session() as session:
        log = session.get(QueryLog, log_id)
        if not log:
            raise HTTPException(status_code=404, detail="问答记录不存在")
        log.feedback = req.feedback
        session.add(log)
        session.commit()
    # M2-08：审计 feedback 写操作（之前遗漏，导致反馈篡改无法追溯）
    log_action(
        action="feedback",
        target_type="query",
        target_id=str(log_id),
        user=extract_user(payload),
        meta={"feedback": req.feedback},
    )
    return {"id": log_id, "feedback": req.feedback, "status": "ok"}


# 种子数据
@router.post("/seed", dependencies=[Depends(require_auth)])
async def seed(
    importer: ImportService = Depends(get_importer),
    payload: dict[str, Any] | None = Depends(require_auth),
) -> dict[str, Any]:
    imported: list[dict[str, Any]] = []
    for doc in SEED_DOCS:
        try:
            result = importer.import_text(
                content=doc["content"],
                title=doc["title"],
                source_type="seed",
                file_type="md",
            )
            imported.append(result)
        except Exception as e:
            imported.append(
                {"title": doc["title"], "error": str(e), "status": "failed"}
            )
    seeded_count = len([x for x in imported if x.get("status") == "imported"])
    failed_count = len([x for x in imported if x.get("status") == "failed"])
    # M2-08：审计 seed
    log_action(
        action="seed",
        target_type="document",
        target_id="",
        user=extract_user(payload),
        meta={
            "kind": "docs",
            "total": len(SEED_DOCS),
            "seeded": seeded_count,
            "failed": failed_count,
        },
    )
    return {
        "seeded": seeded_count,
        "failed": failed_count,
        "items": imported,
    }


@router.post("/seed/recipes", dependencies=[Depends(require_auth)])
async def seed_recipes(
    importer: ImportService = Depends(get_importer),
    payload: dict[str, Any] | None = Depends(require_auth),
) -> dict[str, Any]:
    """M3：导入 IBA 配方种子数据（幂等）。"""
    seeded = 0
    failed = 0
    skipped = 0
    items: list[dict[str, Any]] = []
    for recipe in SEED_RECIPES:
        with get_session() as session:
            existing = session.exec(
                select(Document).where(Document.title == recipe["title"])
            ).first()
            if existing:
                items.append(
                    {
                        "title": recipe["title"],
                        "status": "skipped",
                        "doc_id": existing.doc_id,
                    }
                )
                skipped += 1
                continue
        try:
            # P2-3: category 随 doc 原子落库（消除两阶段非原子）
            result = importer.import_text(
                content=recipe["content"],
                title=recipe["title"],
                source_type="seed",
                file_type="md",
                category="recipe",
            )
            seeded += 1
            items.append({**result, "status": "imported"})
        except Exception as e:
            failed += 1
            items.append(
                {"title": recipe["title"], "error": str(e), "status": "failed"}
            )
    # M2-08：审计 seed recipes
    log_action(
        action="seed",
        target_type="recipe",
        target_id="",
        user=extract_user(payload),
        meta={
            "kind": "recipes",
            "total": len(SEED_RECIPES),
            "seeded": seeded,
            "skipped": skipped,
            "failed": failed,
        },
    )
    return {"seeded": seeded, "failed": failed, "items": items}
