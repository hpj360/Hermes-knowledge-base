"""M2-08：审计日志服务。

提供 ``log_action()`` 辅助函数，在关键写操作处调用以记录审计日志。

设计要点：
- **写失败不影响主业务**：所有写入异常被吞掉并 log warning，避免审计机制
  成为单点故障源
- **采样策略**：``ask`` 动作按 query 哈希采样 10%（确定性，测试可复现），
  避免随机数导致 flaky test；其余写操作 100% 记录
- **用户来源**：从 JWT payload.sub 获取，未启用认证时为 "anonymous"
- **不依赖 api 模块**：避免循环依赖，调用方自行解析 user 传入
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from hermes_kb.database import get_session
from hermes_kb.models import AuditLog

log = logging.getLogger("hermes_kb.audit")

# ask 动作采样率（10%），用 hash(query) % 10 == 0 实现，确定性可复现
_ASK_SAMPLE_RATE = 10


def _should_sample_ask(query: str) -> bool:
    """ask 动作采样：hash(query) % 10 == 0。

    用确定性 hash 而非 random.random()：
    1. 测试可复现（避免 flaky）
    2. 同一 query 多次问询只会采样一次（去重）
    """
    if not query:
        return False
    h = hashlib.md5(query.encode("utf-8")).hexdigest()
    # 取 hash 前 8 位（int 截断溢出无关紧要，只需稳定 mod）
    return int(h[:8], 16) % _ASK_SAMPLE_RATE == 0


def log_action(
    action: str,
    target_type: str = "",
    target_id: str = "",
    user: str = "anonymous",
    meta: dict[str, Any] | None = None,
) -> None:
    """记录审计日志（同步写入，吞异常）。

    Args:
        action: 动作类型（login/import/delete/seed/ask/metadata/...）
        target_type: 目标对象类型（document/user/recipe/query）
        target_id: 目标对象 ID（doc_id / user_id / log_id）
        user: 操作者（从 JWT payload.sub 获取）
        meta: 任意元信息（文件名、查询内容、模型名等）

    Note:
        任何异常均被吞掉（仅 log warning），保证不影响主业务。
    """
    try:
        with get_session() as session:
            entry = AuditLog(
                action=action,
                target_type=target_type,
                target_id=str(target_id)[:128] if target_id else "",
                user=user[:64] if user else "anonymous",
                meta_json=json.dumps(meta or {}, ensure_ascii=False),
            )
            session.add(entry)
            session.commit()
    except Exception as exc:  # noqa: BLE001 —— 审计失败不能影响主业务
        log.warning("audit log write failed (action=%s): %s", action, exc)


def log_ask_sampled(
    query: str,
    user: str = "anonymous",
    *,
    model_used: str = "",
    latency_ms: int = 0,
    log_id: int | None = None,
) -> bool:
    """ask 动作采样记录（10%）。

    Returns:
        True 表示本次记录被采样写入；False 表示被采样过滤掉。

    Note:
        采样使用 hash(query) % 10 == 0，同一 query 多次问询只采样一次。
    """
    if not _should_sample_ask(query):
        return False
    log_action(
        action="ask",
        target_type="query",
        target_id=str(log_id) if log_id else "",
        user=user,
        meta={
            "query": query[:200],
            "model_used": model_used,
            "latency_ms": latency_ms,
        },
    )
    return True


def extract_user(payload: dict[str, Any] | None) -> str:
    """从 JWT payload 提取用户名。

    Args:
        payload: require_auth 返回的 JWT payload；None 表示未启用认证。

    Returns:
        用户名（payload.sub），未启用认证时为 "anonymous"。
    """
    if not payload:
        return "anonymous"
    sub = payload.get("sub")
    return str(sub) if sub else "anonymous"
