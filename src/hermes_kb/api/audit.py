"""M2-08：审计日志查询端点（仅管理员可查）。"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select

from hermes_kb.api.deps import require_auth
from hermes_kb.config import get_settings
from hermes_kb.database import get_session
from hermes_kb.models import AuditLog

router = APIRouter(prefix="/api", tags=["audit"])


async def require_admin(payload: dict[str, Any] | None = Depends(require_auth)) -> str:
    """仅管理员可查询审计日志。

    - 未启用认证时放行（dev 模式），返回 "anonymous"
    - 启用认证时校验 role==admin，否则 403
    """
    settings = get_settings()
    if not settings.auth_enabled:
        return "anonymous"
    if not payload:
        # require_auth 已抛 401，理论不会到这里
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
        )
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可查询审计日志",
        )
    return str(payload.get("sub") or "anonymous")


@router.get("/audit", dependencies=[Depends(require_admin)])
async def list_audit(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, description="按动作筛选"),
    target_type: str | None = Query(default=None, description="按目标类型筛选"),
    user: str | None = Query(default=None, description="按操作者筛选"),
) -> dict[str, Any]:
    """查询审计日志（仅管理员）。

    支持筛选 + 分页：
    - action: login/import/delete/seed/ask/...
    - target_type: document/user/recipe/query
    - user: 操作者（payload.sub）
    """
    with get_session() as session:
        stmt = select(AuditLog)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if target_type:
            stmt = stmt.where(AuditLog.target_type == target_type)
        if user:
            stmt = stmt.where(AuditLog.user == user)
        # 总数（不应用 offset/limit）
        total = len(session.exec(stmt).all())
        # 分页
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        items = session.exec(stmt).all()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "id": item.id,
                    "action": item.action,
                    "target_type": item.target_type,
                    "target_id": item.target_id,
                    "user": item.user,
                    "meta": json.loads(item.meta_json or "{}"),
                    "created_at": item.created_at.isoformat()
                    if item.created_at
                    else None,
                }
                for item in items
            ],
        }
