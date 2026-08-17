"""共享依赖：JWT 工具、认证、年龄门、RAG/Import 服务获取。

- ``jwt_encode`` / ``jwt_decode``：HS256 JWT（无外部依赖）。
- ``require_auth``：校验 Bearer JWT（未启用认证时放行）。
- ``require_role``：V3-Task10 角色权限中间件（multiuser 模式下校验角色层级）。
- ``require_age_gate``：从 :mod:`hermes_kb.age_gate` 重导出，便于路由统一从
  ``hermes_kb.api.deps`` 导入认证类依赖。
- ``get_rag`` / ``get_importer``：从 ``app.state`` 取应用级服务实例（实例在
  ``create_app()`` 中创建，保证每个 app 拥有独立实例，避免跨测试 settings 污染）。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from hermes_kb.age_gate import require_age_gate  # noqa: F401  re-export
from hermes_kb.config import get_settings
from hermes_kb.rag import ImportService, RAGEngine
from hermes_kb.users import is_role_at_least, validate_role


# ---------------------------------------------------------------------------
# JWT 工具（HS256，无外部依赖）
# ---------------------------------------------------------------------------
def _b64e(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return urlsafe_b64decode(s + pad)


def jwt_encode(payload: dict[str, Any], secret: str, ttl_hours: int = 24) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    body = {**payload, "iat": now, "exp": now + ttl_hours * 3600}
    h = _b64e(json.dumps(header, separators=(",", ":")).encode())
    p = _b64e(json.dumps(body, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64e(sig)}"


def jwt_decode(token: str, secret: str) -> dict[str, Any] | None:
    """解码并校验 JWT。失败返回 None。"""
    try:
        h, p, s = token.split(".")
    except ValueError:
        return None
    signing_input = f"{h}.{p}".encode()
    expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    try:
        actual = _b64d(s)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(expected, actual):
        return None
    try:
        body = json.loads(_b64d(p).decode())
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if body.get("exp", 0) < int(time.time()):
        return None
    return body


# ---------------------------------------------------------------------------
# 认证依赖
# ---------------------------------------------------------------------------
async def require_auth(request: Request) -> dict[str, Any] | None:
    """若启用认证，校验 JWT；未启用时直接放行。"""
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
        )
    token = auth[7:].strip()
    payload = jwt_decode(token, settings.jwt_secret)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌无效或已过期",
        )
    return payload


def require_role(min_role: str):
    """V3-Task10：角色权限中间件工厂。

    用法：``Depends(require_role("owner"))``

    - 未启用 multiuser 时放行（保持单用户模式向后兼容）
    - 启用 multiuser 但未认证 → 401
    - 认证但角色层级不足 → 403
    - 认证且角色层级达标 → 返回 payload

    Args:
        min_role: 要求的最低角色（owner/member/viewer）
    """
    validate_role(min_role)

    async def _checker(payload: dict[str, Any] | None = Depends(require_auth)) -> dict[str, Any]:
        settings = get_settings()
        if not settings.multiuser:
            return payload or {}
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="多用户模式需登录后访问",
            )
        user_role = str(payload.get("role", "viewer"))
        if not is_role_at_least(user_role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：需要 {min_role} 及以上角色，当前 {user_role}",
            )
        return payload

    return _checker


def get_current_user(payload: dict[str, Any] | None) -> str:
    """从 JWT payload 提取当前用户名（multiuser 模式下有效）。

    未启用认证/未登录时返回 "anonymous"。
    """
    if not payload:
        return "anonymous"
    sub = payload.get("sub")
    return str(sub) if sub else "anonymous"


# ---------------------------------------------------------------------------
# 应用级服务依赖（实例在 create_app() 中创建并挂到 app.state）
# ---------------------------------------------------------------------------
def get_rag(request: Request) -> RAGEngine:
    return request.app.state.rag


def get_importer(request: Request) -> ImportService:
    return request.app.state.importer


def get_agent(request: Request):
    """获取应用级鸡尾酒智能体实例（create_app() 中挂到 app.state）。"""
    return request.app.state.agent
