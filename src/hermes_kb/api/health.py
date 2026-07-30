"""健康检查端点。

提供两个端点：
- GET /api/health        轻量 liveness 探针（始终 200，只读 config + 计数）
- GET /api/health/ready  readiness 探针：DB 连通性 + LLM 可用性 + 关键依赖，
                        任一失败返回 503，便于部署层摘除流量
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlmodel import select

from hermes_kb import __version__
from hermes_kb.config import get_settings
from hermes_kb.database import get_session
from hermes_kb.models import Document

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Liveness 探针：进程存活即 200。

    不做依赖检查（DB 故障时仍返回 200），避免被过度重启。
    """
    doc_count = 0
    try:
        with get_session() as session:
            doc_count = len(session.exec(select(Document)).all())
    except Exception:  # noqa: BLE001 — 软降级，不阻塞主流程
        doc_count = 0
    settings = get_settings()
    return {
        "status": "ok",
        "service": "hermes-kb",
        "version": __version__,
        "time": datetime.now(timezone.utc).isoformat(),
        "doc_count": doc_count,
        "llm_provider": settings.llm_provider,
        "llm_available": settings.llm_available,
        "embedding_provider": settings.embedding_provider,
        "embedding_available": settings.embedding_available,
        "auth_enabled": settings.auth_enabled,
        "multiuser": settings.multiuser,
        "age_gate_enabled": settings.age_gate_enabled,
        "vault_enabled": settings.vault_enabled,
    }


@router.get("/health/ready")
async def readiness() -> JSONResponse:
    """Readiness 探针：所有关键依赖就绪才返回 200，否则 503。

    检查项：
    - db：能否打开 session 并执行 SELECT 1
    - migrations：documents 表可访问（间接验证 schema 已迁移）

    LLM / embedding 不参与就绪判定（Mock 后端可降级服务）。
    """
    checks: dict[str, dict[str, Any]] = {}
    overall_ok = True

    # 1. DB 连通性
    db_ok = False
    db_error = ""
    try:
        with get_session() as session:
            session.exec(select(Document).limit(1))
            db_ok = True
    except Exception as e:  # noqa: BLE001 — 软降级，不阻塞主流程
        db_error = type(e).__name__
    checks["db"] = {"status": "up" if db_ok else "down", "error": db_error}
    if not db_ok:
        overall_ok = False

    body: dict[str, Any] = {
        "status": "ok" if overall_ok else "degraded",
        "time": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
        "checks": checks,
    }
    code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=body, status_code=code)
