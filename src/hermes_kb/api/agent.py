"""鸡尾酒智能体端点：/agent/ask（SSE 流式）+ /agent/ask/sync（同步）。

- ``POST /api/agent/ask``      SSE 流式：逐事件输出 tool_call / token / done
- ``POST /api/agent/ask/sync`` 同步 JSON：一次返回完整结果（供测试与简单客户端）

两者均需认证 + 年龄门。年龄门未通过时由 ``CocktailAgent`` 内部强制拒绝
（未验证且非无酒精请求 → rejected 响应，不调用任何配方工具）。
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hermes_kb.api.deps import get_agent, require_age_gate, require_auth
from hermes_kb.database import get_session
from hermes_kb.models import QueryLog
from hermes_kb.token_cost import calculate_cost

log = logging.getLogger("hermes_kb.agent_api")

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentAskReq(BaseModel):
    query: str = Field(..., max_length=2000)
    # 会话上下文：多轮对话历史（role: user/assistant）
    history: list[dict[str, str]] = Field(default_factory=list)


def _validate(req: AgentAskReq) -> str:
    """校验请求，返回规范化 query；非法时抛 400。"""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    if len(req.history) > 50:
        raise HTTPException(status_code=400, detail="history 过长（最多 50 条）")
    return req.query.strip()


class _AgentLogView:
    """将 AgentResult.to_dict() 映射为日志字段访问接口（避免依赖 AgentResult 实例）。"""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def model_used(self) -> str:
        return str(self._data.get("model_used", "mock"))

    @property
    def prompt_tokens(self) -> int:
        return int(self._data.get("prompt_tokens", 0) or 0)

    @property
    def completion_tokens(self) -> int:
        return int(self._data.get("completion_tokens", 0) or 0)

    @property
    def answer(self) -> str:
        return str(self._data.get("answer", ""))

    @property
    def citations(self) -> list[dict[str, Any]]:
        return self._data.get("citations", [])


def _agent_result_from_event(evt: dict[str, Any]) -> Any:
    """从 SSE done 事件提取 AgentResult 字段映射对象。"""
    return _AgentLogView(evt)


def _log_agent_query(query: str, result: Any, started: float) -> None:
    """写入问答日志，使 agent 的 token 用量计入现有 token_cost 统计。

    字段与 RAGEngine._log_query 对齐（model_used / tokens / cost_cny），
    便于统一在 token 统计面板中汇总。历史记录中展示 answer 与 citations。
    """
    cost = calculate_cost(
        result.model_used,
        result.prompt_tokens,
        result.completion_tokens,
    )
    entry = QueryLog(
        query=query,
        answer=result.answer,
        citations=json.dumps(result.citations, ensure_ascii=False),
        model_used=result.model_used,
        latency_ms=int((time.perf_counter() - started) * 1000),
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_cny=cost,
    )
    try:
        with get_session() as session:
            session.add(entry)
            session.commit()
    except Exception as exc:  # noqa: BLE001 — 审计写入失败不阻塞响应
        log.warning("agent query log failed: %s", exc)


@router.post(
    "/ask",
    dependencies=[Depends(require_auth), Depends(require_age_gate)],
)
async def agent_ask(
    req: AgentAskReq,
    agent: Any = Depends(get_agent),
) -> StreamingResponse:
    """SSE 流式智能体问答。

    事件格式（每行 ``data: <json>``）：
    - ``{"type": "tool_call", "name", "arguments", "result", "call_id"}`` 工具调用
    - ``{"type": "token", "content": "..."}``                            回答片段
    - ``{"type": "done", ...AgentResult}``                                结束（含引用/轮次）
    - ``{"type": "error", "message": "..."}``                             错误
    """
    q = _validate(req)
    started = time.perf_counter()

    async def gen():
        try:
            events = agent.ask_events(q, history=req.history)
            for evt in events:
                if evt.get("type") == "done":
                    _log_agent_query(q, _agent_result_from_event(evt), started)
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001 — SSE 流内异常转 error 事件
            log.warning("agent/ask stream failed: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/ask/sync",
    dependencies=[Depends(require_auth), Depends(require_age_gate)],
)
async def agent_ask_sync(
    req: AgentAskReq,
    agent: Any = Depends(get_agent),
) -> dict[str, Any]:
    """同步智能体问答：一次返回完整 AgentResult JSON。"""
    q = _validate(req)
    started = time.perf_counter()
    try:
        result = agent.ask(q, history=req.history)
    except Exception as exc:  # 异常转错误响应
        log.warning("agent/ask/sync failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"智能体执行失败: {exc}") from exc
    _log_agent_query(q, result, started)
    return result.to_dict()
