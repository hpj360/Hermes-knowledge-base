"""认证与年龄门端点（M1-07 / M1-08 / V3-Task10）。"""
from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from hermes_kb.age_gate import (
    COOKIE_NAME,
    COOKIE_TTL_DAYS,
    make_age_cookie_value,
    verify_age_cookie,
)
from hermes_kb.api.deps import (
    get_current_user,
    jwt_encode,
    require_auth,
    require_role,
)
from hermes_kb.audit import log_action
from hermes_kb.config import get_settings

router = APIRouter(prefix="/api", tags=["auth"])


class LoginReq(BaseModel):
    password: str = Field(..., max_length=200)


class AgeGateReq(BaseModel):
    confirmed: bool


# V3-Task10：多用户模式请求体
class MultiLoginReq(BaseModel):
    """多用户模式登录：用户名 + 密码。"""
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=200)


class RegisterReq(BaseModel):
    """邀请码注册：邀请码 + 用户名 + 密码。"""
    invite_code: str = Field(..., min_length=1, max_length=64)
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6, max_length=200)


class InviteReq(BaseModel):
    """生成邀请码请求。"""
    role: str = Field(default="member", description="member/viewer，不允许 owner")
    ttl_hours: int | None = Field(default=None, ge=1, le=720, description="有效期小时，None=永久")


class UpdateRoleReq(BaseModel):
    """修改用户角色请求。"""
    role: str = Field(..., description="owner/member/viewer")


@router.post("/auth/login")
async def login(req: LoginReq) -> dict[str, Any]:
    """单用户模式登录（旧接口，向后兼容）。"""
    settings = get_settings()
    if not settings.auth_enabled:
        return {
            "token": "",
            "auth_enabled": False,
            "message": "认证未启用",
        }
    # 单用户密码校验
    if not settings.auth_password:
        raise HTTPException(
            status_code=500,
            detail="服务端未配置认证密码（KB_AUTH_PASSWORD）",
        )
    if not hmac.compare_digest(req.password, settings.auth_password):
        # M2-08：审计登录失败（不暴露用户名是否存在）
        log_action(
            action="login",
            target_type="user",
            target_id="",
            user="unknown",
            meta={"success": False, "reason": "invalid_password"},
        )
        raise HTTPException(status_code=401, detail="密码错误")
    token = jwt_encode(
        {"sub": settings.auth_username, "role": "owner"},
        settings.jwt_secret,
        ttl_hours=settings.jwt_ttl_hours,
    )
    # M2-08：审计登录成功
    log_action(
        action="login",
        target_type="user",
        target_id=settings.auth_username,
        user=settings.auth_username,
        meta={"success": True, "ttl_hours": settings.jwt_ttl_hours},
    )
    return {
        "token": token,
        "auth_enabled": True,
        "username": settings.auth_username,
        "expires_in": settings.jwt_ttl_hours * 3600,
    }


@router.post("/auth/multi-login")
async def multi_login(req: MultiLoginReq) -> dict[str, Any]:
    """V3-Task10：多用户模式登录（用户名 + 密码）。

    - 仅在 KB_MULTIUSER=true 时可用，否则返回 400
    - 首次登录时触发 owner 初始化（用 KB_USERNAME + KB_AUTH_PASSWORD 创建首个 owner）
    - 认证成功返回 JWT（sub=username, role=用户角色）
    """
    settings = get_settings()
    if not settings.multiuser:
        raise HTTPException(
            status_code=400,
            detail="多用户模式未启用（KB_MULTIUSER=false）",
        )

    # 首次初始化 owner（幂等：已有 owner 时跳过）
    from hermes_kb.users import authenticate, ensure_owner_initialized

    ensure_owner_initialized(settings.auth_username, settings.auth_password)

    user = authenticate(req.username, req.password)
    if not user:
        log_action(
            action="login",
            target_type="user",
            target_id=req.username,
            user=req.username,
            meta={"success": False, "reason": "invalid_credentials", "mode": "multiuser"},
        )
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = jwt_encode(
        {"sub": user.username, "role": user.role},
        settings.jwt_secret,
        ttl_hours=settings.jwt_ttl_hours,
    )
    log_action(
        action="login",
        target_type="user",
        target_id=user.username,
        user=user.username,
        meta={"success": True, "role": user.role, "mode": "multiuser"},
    )
    return {
        "token": token,
        "auth_enabled": True,
        "multiuser": True,
        "username": user.username,
        "role": user.role,
        "expires_in": settings.jwt_ttl_hours * 3600,
    }


@router.post("/auth/register")
async def register(req: RegisterReq) -> dict[str, Any]:
    """V3-Task10：邀请码注册新用户。

    - 仅在 KB_MULTIUSER=true 时可用
    - 邀请码一次性使用，注册后标记 used_by
    - 注册成功后可直接登录（返回 JWT）
    """
    settings = get_settings()
    if not settings.multiuser:
        raise HTTPException(
            status_code=400,
            detail="多用户模式未启用（KB_MULTIUSER=false）",
        )

    from hermes_kb.users import consume_invite_code, create_user

    try:
        invite_info = consume_invite_code(req.invite_code, req.username)
    except LookupError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        user_info = create_user(
            username=req.username,
            password=req.password,
            role=invite_info["role"],
            invited_by=invite_info["created_by"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # 自动签发 JWT（注册即登录）
    token = jwt_encode(
        {"sub": user_info["username"], "role": user_info["role"]},
        settings.jwt_secret,
        ttl_hours=settings.jwt_ttl_hours,
    )
    log_action(
        action="register",
        target_type="user",
        target_id=user_info["username"],
        user=user_info["username"],
        meta={"role": user_info["role"], "invited_by": invite_info["created_by"]},
    )
    return {
        "token": token,
        "auth_enabled": True,
        "multiuser": True,
        "username": user_info["username"],
        "role": user_info["role"],
        "expires_in": settings.jwt_ttl_hours * 3600,
    }


@router.post("/auth/invite")
async def create_invite(
    req: InviteReq,
    payload: dict[str, Any] = Depends(require_role("owner")),  # noqa: B008  # require_role 为 FastAPI 依赖，需在默认参数中调用
) -> dict[str, Any]:
    """V3-Task10：owner 生成邀请码。

    - 仅 owner 角色可调用
    - 邀请角色仅限 member/viewer
    """
    from hermes_kb.users import generate_invite_code

    current_user = get_current_user(payload)
    try:
        result = generate_invite_code(
            created_by=current_user,
            role=req.role,
            ttl_hours=req.ttl_hours,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    log_action(
        action="invite",
        target_type="invite_code",
        target_id=result["code"],
        user=current_user,
        meta={"role": req.role, "ttl_hours": req.ttl_hours},
    )
    return result


@router.get("/auth/users")
async def list_users_endpoint(
    payload: dict[str, Any] = Depends(require_role("owner")),  # noqa: B008  # require_role 为 FastAPI 依赖，需在默认参数中调用
) -> dict[str, Any]:
    """V3-Task10：owner 查看用户列表。"""
    from hermes_kb.users import list_users

    return {"items": list_users(active_only=False)}


@router.get("/auth/invites")
async def list_invites_endpoint(
    payload: dict[str, Any] = Depends(require_role("owner")),  # noqa: B008  # require_role 为 FastAPI 依赖，需在默认参数中调用
) -> dict[str, Any]:
    """V3-Task10：owner 查看邀请码列表。"""
    from hermes_kb.users import list_invite_codes

    return {"items": list_invite_codes(active_only=False)}


@router.post("/auth/users/{username}/role")
async def update_user_role_endpoint(
    username: str,
    req: UpdateRoleReq,
    payload: dict[str, Any] = Depends(require_role("owner")),  # noqa: B008  # require_role 为 FastAPI 依赖，需在默认参数中调用
) -> dict[str, Any]:
    """V3-Task10：owner 修改用户角色。"""
    from hermes_kb.users import update_user_role

    current_user = get_current_user(payload)
    try:
        ok = update_user_role(username, req.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not ok:
        raise HTTPException(status_code=404, detail=f"用户不存在: {username}")

    log_action(
        action="update_role",
        target_type="user",
        target_id=username,
        user=current_user,
        meta={"new_role": req.role},
    )
    return {"username": username, "role": req.role, "status": "ok"}


@router.get("/auth/me")
async def me(payload: dict[str, Any] | None = Depends(require_auth)) -> dict[str, Any]:
    settings = get_settings()
    return {
        "auth_enabled": settings.auth_enabled,
        "multiuser": settings.multiuser,
        "username": (payload or {}).get("sub") if payload else None,
        "role": (payload or {}).get("role") if payload else None,
        "exp": (payload or {}).get("exp") if payload else None,
    }


@router.post("/age-gate/confirm")
async def age_gate_confirm(req: AgeGateReq, response: Response) -> dict[str, Any]:
    settings = get_settings()
    if req.confirmed:
        response.set_cookie(
            key=COOKIE_NAME,
            value=make_age_cookie_value(),
            max_age=COOKIE_TTL_DAYS * 86400,
            httponly=True,
            samesite="strict",
            secure=settings.cookie_secure,  # P2-5: 生产 HTTPS 通过 KB_COOKIE_SECURE=true 启用
        )
    return {
        "confirmed": bool(req.confirmed),
        "age_gate_enabled": settings.age_gate_enabled,
        "message": "已确认成年" if req.confirmed else "未确认",
    }


@router.get("/age-gate/status")
async def age_gate_status(request: Request) -> dict[str, Any]:
    settings = get_settings()
    confirmed = verify_age_cookie(request.cookies.get(COOKIE_NAME))
    return {
        "age_gate_enabled": settings.age_gate_enabled,
        "confirmed": confirmed,
        "message": "本站内容含酒类知识，未满 18 岁请勿访问"
        if settings.age_gate_enabled
        else "年龄门未启用",
    }
