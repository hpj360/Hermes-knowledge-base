"""V3-Task9/10：用户服务（密码哈希 + CRUD + 角色权限）。

设计要点：
- **密码哈希**：使用标准库 ``hashlib.pbkdf2_hmac('sha256', ...)`` + 随机 salt + 高迭代次数，
  避免引入 bcrypt/argon2 外部依赖（Windows 兼容性问题）。
- **存储格式**：``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``，与 Django 兼容格式。
- **角色层级**：owner > member > viewer，``require_role`` 用层级比较而非硬编码列表。
- **首次初始化**：启用 multiuser 时若 users 表为空，将旧 ``KB_AUTH_PASSWORD`` 迁移为
  owner 账户（username=KB_USERNAME），实现单用户→多用户平滑过渡。
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import USER_ROLES, InviteCode, User, _now_utc

# ---------------------------------------------------------------------------
# 密码哈希（pbkdf2_hmac sha256，标准库实现）
# ---------------------------------------------------------------------------
_PBKDF2_ITERATIONS = 200_000  # 2026 年安全基线（OWASP 推荐 ≥600k for PBKDF2-SHA256，
#                              # 但考虑 SQLite 单机 + 测试耗时，取 200k 平衡安全与性能）
_SALT_BYTES = 16
_HASH_BYTES = 32


def hash_password(password: str) -> str:
    """生成密码哈希串。

    格式：``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``
    """
    if not password:
        raise ValueError("密码不能为空")
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS, dklen=_HASH_BYTES
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验密码是否匹配哈希串。

    使用 ``hmac.compare_digest`` 防止时序攻击。
    """
    if not password or not stored:
        return False
    try:
        algo, iter_str, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iter_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected)
    )
    return hmac.compare_digest(derived, expected)


# ---------------------------------------------------------------------------
# 角色权限
# ---------------------------------------------------------------------------
_ROLE_LEVEL = {"viewer": 1, "member": 2, "owner": 3}


def role_level(role: str) -> int:
    """返回角色层级数字（越大权限越高）。未知角色返回 0。"""
    return _ROLE_LEVEL.get(role, 0)


def is_role_at_least(user_role: str, required: str) -> bool:
    """判断用户角色是否达到要求层级（含）。"""
    return role_level(user_role) >= role_level(required)


def validate_role(role: str) -> str:
    """校验角色合法性，返回归一化后的角色名。"""
    if role not in USER_ROLES:
        raise ValueError(f"非法角色: {role}，允许: {USER_ROLES}")
    return role


# ---------------------------------------------------------------------------
# 用户 CRUD
# ---------------------------------------------------------------------------
def create_user(
    username: str,
    password: str,
    role: str = "member",
    invited_by: str = "",
) -> dict[str, Any]:
    """创建用户。

    Args:
        username: 用户名（唯一）
        password: 明文密码（内部哈希存储）
        role: owner/member/viewer
        invited_by: 邀请人用户名（owner 自注册为空）

    Returns:
        {id, username, role, invited_by, created_at}

    Raises:
        ValueError: 用户名已存在 / 角色非法 / 密码为空
    """
    validate_role(role)
    username = username.strip()
    if not username:
        raise ValueError("用户名不能为空")
    if len(username) > 64:
        raise ValueError("用户名长度不能超过 64 字符")

    with get_session() as session:
        # 唯一性检查
        existing = session.exec(
            select(User).where(User.username == username)
        ).first()
        if existing:
            raise ValueError(f"用户名已存在: {username}")

        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            invited_by=invited_by,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "invited_by": user.invited_by,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }


def authenticate(username: str, password: str) -> User | None:
    """用户名+密码校验，成功返回 User 实例，失败返回 None。

    - 用户不存在 / 密码错误 / 账户禁用均返回 None（不暴露具体原因防枚举）
    """
    username = username.strip()
    if not username or not password:
        return None
    with get_session() as session:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


def get_user_by_name(username: str) -> User | None:
    """按用户名查询用户。"""
    with get_session() as session:
        return session.exec(
            select(User).where(User.username == username)
        ).first()


def list_users(active_only: bool = False) -> list[dict[str, Any]]:
    """列出全部用户（脱敏，不含 password_hash）。"""
    with get_session() as session:
        stmt = select(User)
        if active_only:
            stmt = stmt.where(User.is_active == True)  # noqa: E712
        users = session.exec(stmt).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "invited_by": u.invited_by,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]


def update_user_role(username: str, new_role: str) -> bool:
    """修改用户角色（仅 owner 可调用，调用方负责权限校验）。

    Returns:
        True 表示修改成功，False 表示用户不存在。
    """
    validate_role(new_role)
    with get_session() as session:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if not user:
            return False
        user.role = new_role
        user.updated_at = _now_utc()
        session.add(user)
        session.commit()
        return True


def deactivate_user(username: str) -> bool:
    """软禁用用户（is_active=False，保留数据）。"""
    with get_session() as session:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if not user:
            return False
        user.is_active = False
        user.updated_at = _now_utc()
        session.add(user)
        session.commit()
        return True


# ---------------------------------------------------------------------------
# 首次初始化（单用户 → 多用户迁移）
# ---------------------------------------------------------------------------
def ensure_owner_initialized(
    default_username: str,
    default_password: str,
) -> dict[str, Any] | None:
    """启用 multiuser 时首次初始化 owner 账户。

    - 若 users 表已有 owner 角色用户，跳过（已初始化）
    - 若 users 表为空，用 KB_USERNAME + KB_AUTH_PASSWORD 创建首个 owner
    - 若 users 表非空但无 owner，不自动创建（需手动介入）

    Returns:
        新建 owner 用户信息，或 None（已初始化/无法初始化）
    """
    with get_session() as session:
        # 检查是否已有 owner
        existing_owner = session.exec(
            select(User).where(User.role == "owner")
        ).first()
        if existing_owner:
            return None

        # 检查表是否为空
        any_user = session.exec(select(User)).first()
        if any_user:
            return None  # 非空但无 owner，需手动介入

        # 表为空，创建首个 owner
        if not default_username or not default_password:
            return None
        owner = User(
            username=default_username.strip(),
            password_hash=hash_password(default_password),
            role="owner",
            invited_by="",
        )
        session.add(owner)
        session.commit()
        session.refresh(owner)
        return {
            "id": owner.id,
            "username": owner.username,
            "role": owner.role,
            "created_at": owner.created_at.isoformat() if owner.created_at else None,
        }


# ---------------------------------------------------------------------------
# 邀请码（Task 10 使用，此处提供服务层基础）
# ---------------------------------------------------------------------------
def generate_invite_code(
    created_by: str,
    role: str = "member",
    ttl_hours: int | None = None,
) -> dict[str, Any]:
    """生成邀请码（仅 owner 可调用，调用方负责权限校验）。

    Args:
        created_by: 生成者用户名（owner）
        role: 被邀请者角色（member/viewer，不允许 owner）
        ttl_hours: 有效期（小时），None 表示永久

    Returns:
        {code, role, created_by, expires_at}
    """
    if role == "owner":
        raise ValueError("不允许邀请 owner 角色")
    validate_role(role)

    code = secrets.token_urlsafe(16)
    expires_at: datetime | None = None
    if ttl_hours is not None and ttl_hours > 0:
        expires_at = _now_utc() + timedelta(hours=ttl_hours)

    with get_session() as session:
        invite = InviteCode(
            code=code,
            role=role,
            created_by=created_by,
            expires_at=expires_at,
        )
        session.add(invite)
        session.commit()
        session.refresh(invite)
        return {
            "code": invite.code,
            "role": invite.role,
            "created_by": invite.created_by,
            "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
        }


def consume_invite_code(
    code: str,
    used_by: str,
) -> dict[str, Any]:
    """消费邀请码（注册时调用）。

    Returns:
        {code, role, created_by} 用于注册新用户

    Raises:
        LookupError: 邀请码不存在/已使用/已过期
    """
    with get_session() as session:
        invite = session.exec(
            select(InviteCode).where(InviteCode.code == code)
        ).first()
        if not invite:
            raise LookupError("邀请码不存在")
        if invite.used_by:
            raise LookupError("邀请码已被使用")
        if invite.expires_at and invite.expires_at < _now_utc():
            raise LookupError("邀请码已过期")

        invite.used_by = used_by
        invite.used_at = _now_utc()
        session.add(invite)
        session.commit()
        return {
            "code": invite.code,
            "role": invite.role,
            "created_by": invite.created_by,
        }


def list_invite_codes(active_only: bool = False) -> list[dict[str, Any]]:
    """列出邀请码。active_only=True 时仅返回未使用且未过期的。"""
    with get_session() as session:
        stmt = select(InviteCode)
        invites = session.exec(stmt).all()
        now = _now_utc()
        result = []
        for inv in invites:
            is_used = inv.used_by is not None
            is_expired = inv.expires_at is not None and inv.expires_at < now
            if active_only and (is_used or is_expired):
                continue
            result.append({
                "code": inv.code,
                "role": inv.role,
                "created_by": inv.created_by,
                "used_by": inv.used_by,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "used_at": inv.used_at.isoformat() if inv.used_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            })
        return result
