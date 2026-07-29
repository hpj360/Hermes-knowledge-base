"""V3-Task9: 用户数据模型与服务测试。"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError


# ---------------------------------------------------------------------------
# 模型层测试
# ---------------------------------------------------------------------------
def test_user_model_unique_username(tmp_db):
    """username 唯一约束：同名用户第二次插入抛 IntegrityError。"""
    from hermes_kb.database import get_session
    from hermes_kb.models import User

    with get_session() as session:
        u1 = User(username="alice", password_hash="hash1", role="owner")
        session.add(u1)
        session.commit()

        u2 = User(username="alice", password_hash="hash2", role="member")
        session.add(u2)
        with pytest.raises(IntegrityError):
            session.commit()


def test_invite_code_model_unique_code(tmp_db):
    """邀请码 code 唯一约束。"""
    from hermes_kb.database import get_session
    from hermes_kb.models import InviteCode

    with get_session() as session:
        i1 = InviteCode(code="ABC123", role="member", created_by="alice")
        session.add(i1)
        session.commit()

        i2 = InviteCode(code="ABC123", role="viewer", created_by="alice")
        session.add(i2)
        with pytest.raises(IntegrityError):
            session.commit()


def test_user_role_constants():
    """USER_ROLES 常量包含三种角色。"""
    from hermes_kb.models import USER_ROLES

    assert "owner" in USER_ROLES
    assert "member" in USER_ROLES
    assert "viewer" in USER_ROLES
    assert len(USER_ROLES) == 3


# ---------------------------------------------------------------------------
# 密码哈希测试
# ---------------------------------------------------------------------------
def test_hash_password_format():
    """哈希串格式：pbkdf2_sha256$<iter>$<salt_hex>$<hash_hex>。"""
    from hermes_kb.users import hash_password

    h = hash_password("mypassword")
    parts = h.split("$")
    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert parts[1].isdigit()
    assert int(parts[1]) >= 100_000  # 迭代次数安全基线


def test_hash_password_unique_salt():
    """同一密码两次哈希结果不同（随机 salt）。"""
    from hermes_kb.users import hash_password

    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2


def test_hash_password_empty_rejected():
    """空密码应抛 ValueError。"""
    from hermes_kb.users import hash_password

    with pytest.raises(ValueError, match="不能为空"):
        hash_password("")


def test_verify_password_correct():
    """正确密码校验通过。"""
    from hermes_kb.users import hash_password, verify_password

    h = hash_password("secret123")
    assert verify_password("secret123", h) is True


def test_verify_password_wrong():
    """错误密码校验失败。"""
    from hermes_kb.users import hash_password, verify_password

    h = hash_password("secret123")
    assert verify_password("wrong", h) is False


def test_verify_password_empty():
    """空密码/空哈希返回 False。"""
    from hermes_kb.users import verify_password

    assert verify_password("", "pbkdf2_sha256$100000$abc$def") is False
    assert verify_password("abc", "") is False


def test_verify_password_malformed():
    """格式错误的哈希串返回 False（不抛异常）。"""
    from hermes_kb.users import verify_password

    assert verify_password("abc", "malformed") is False
    assert verify_password("abc", "wrong_algo$100$abc$def") is False
    assert verify_password("abc", "pbkdf2_sha256$notint$abc$def") is False


# ---------------------------------------------------------------------------
# 角色权限测试
# ---------------------------------------------------------------------------
def test_role_level_hierarchy():
    """角色层级：owner > member > viewer。"""
    from hermes_kb.users import role_level

    assert role_level("owner") > role_level("member")
    assert role_level("member") > role_level("viewer")
    assert role_level("unknown") == 0


def test_is_role_at_least():
    """角色层级判断。"""
    from hermes_kb.users import is_role_at_least

    assert is_role_at_least("owner", "member") is True
    assert is_role_at_least("owner", "owner") is True
    assert is_role_at_least("viewer", "owner") is False
    assert is_role_at_least("member", "viewer") is True


def test_validate_role_valid():
    """合法角色通过校验。"""
    from hermes_kb.users import validate_role

    assert validate_role("owner") == "owner"
    assert validate_role("member") == "member"
    assert validate_role("viewer") == "viewer"


def test_validate_role_invalid():
    """非法角色抛 ValueError。"""
    from hermes_kb.users import validate_role

    with pytest.raises(ValueError, match="非法角色"):
        validate_role("admin")  # 旧角色名应被拒绝


# ---------------------------------------------------------------------------
# 用户 CRUD 测试
# ---------------------------------------------------------------------------
def test_create_user_success(tmp_db):
    """创建用户成功。"""
    from hermes_kb.users import create_user, get_user_by_name

    result = create_user("alice", "pass123", role="owner")
    assert result["username"] == "alice"
    assert result["role"] == "owner"
    assert result["id"] is not None

    # 数据库中应有该用户，且 password_hash 已哈希
    user = get_user_by_name("alice")
    assert user is not None
    assert user.password_hash.startswith("pbkdf2_sha256$")
    assert user.password_hash != "pass123"  # 明文未存储


def test_create_user_duplicate(tmp_db):
    """重复用户名抛 ValueError。"""
    from hermes_kb.users import create_user

    create_user("alice", "pass1")
    with pytest.raises(ValueError, match="已存在"):
        create_user("alice", "pass2")


def test_create_user_empty_username(tmp_db):
    """空用户名抛 ValueError。"""
    from hermes_kb.users import create_user

    with pytest.raises(ValueError, match="不能为空"):
        create_user("  ", "pass")


def test_create_user_invalid_role(tmp_db):
    """非法角色抛 ValueError。"""
    from hermes_kb.users import create_user

    with pytest.raises(ValueError, match="非法角色"):
        create_user("alice", "pass", role="admin")


def test_authenticate_success(tmp_db):
    """正确用户名+密码认证成功。"""
    from hermes_kb.users import authenticate, create_user

    create_user("alice", "secret", role="member")
    user = authenticate("alice", "secret")
    assert user is not None
    assert user.username == "alice"
    assert user.role == "member"


def test_authenticate_wrong_password(tmp_db):
    """错误密码返回 None。"""
    from hermes_kb.users import authenticate, create_user

    create_user("alice", "secret")
    assert authenticate("alice", "wrong") is None


def test_authenticate_unknown_user(tmp_db):
    """不存在的用户返回 None。"""
    from hermes_kb.users import authenticate

    assert authenticate("nobody", "pass") is None


def test_authenticate_inactive_user(tmp_db):
    """被禁用的用户拒绝登录。"""
    from hermes_kb.users import authenticate, create_user, deactivate_user

    create_user("alice", "pass")
    assert deactivate_user("alice") is True
    assert authenticate("alice", "pass") is None


def test_list_users(tmp_db):
    """列出用户（不含 password_hash）。"""
    from hermes_kb.users import create_user, list_users

    create_user("alice", "pass", role="owner")
    create_user("bob", "pass", role="member")
    create_user("carol", "pass", role="viewer")

    users = list_users()
    assert len(users) == 3
    names = [u["username"] for u in users]
    assert set(names) == {"alice", "bob", "carol"}
    # 不含敏感字段
    assert all("password_hash" not in u for u in users)


def test_list_users_active_only(tmp_db):
    """active_only=True 仅返回活跃用户。"""
    from hermes_kb.users import create_user, deactivate_user, list_users

    create_user("alice", "pass")
    create_user("bob", "pass")
    deactivate_user("bob")

    active = list_users(active_only=True)
    assert len(active) == 1
    assert active[0]["username"] == "alice"


def test_update_user_role(tmp_db):
    """修改用户角色。"""
    from hermes_kb.users import create_user, get_user_by_name, update_user_role

    create_user("alice", "pass", role="member")
    assert update_user_role("alice", "owner") is True
    user = get_user_by_name("alice")
    assert user.role == "owner"


def test_update_user_role_not_found(tmp_db):
    """修改不存在用户返回 False。"""
    from hermes_kb.users import update_user_role

    assert update_user_role("nobody", "owner") is False


def test_deactivate_user(tmp_db):
    """软禁用用户。"""
    from hermes_kb.users import create_user, deactivate_user, get_user_by_name

    create_user("alice", "pass")
    assert deactivate_user("alice") is True
    user = get_user_by_name("alice")
    assert user.is_active is False


def test_deactivate_user_not_found(tmp_db):
    """禁用不存在用户返回 False。"""
    from hermes_kb.users import deactivate_user

    assert deactivate_user("nobody") is False


# ---------------------------------------------------------------------------
# 首次初始化测试
# ---------------------------------------------------------------------------
def test_ensure_owner_initialized_empty_table(tmp_db):
    """空 users 表时创建首个 owner。"""
    from hermes_kb.users import ensure_owner_initialized, get_user_by_name

    result = ensure_owner_initialized("admin", "admin_pass")
    assert result is not None
    assert result["username"] == "admin"
    assert result["role"] == "owner"

    user = get_user_by_name("admin")
    assert user is not None
    assert user.role == "owner"


def test_ensure_owner_initialized_already_has_owner(tmp_db):
    """已有 owner 时跳过初始化。"""
    from hermes_kb.users import create_user, ensure_owner_initialized

    create_user("existing_owner", "pass", role="owner")
    result = ensure_owner_initialized("admin", "admin_pass")
    assert result is None  # 跳过


def test_ensure_owner_initialized_non_empty_no_owner(tmp_db):
    """非空但无 owner 时不自动创建（需手动介入）。"""
    from hermes_kb.users import create_user, ensure_owner_initialized

    create_user("member1", "pass", role="member")
    result = ensure_owner_initialized("admin", "admin_pass")
    assert result is None  # 不自动创建


def test_ensure_owner_initialized_no_credentials(tmp_db):
    """空用户名/密码时不初始化。"""
    from hermes_kb.users import ensure_owner_initialized

    assert ensure_owner_initialized("", "pass") is None
    assert ensure_owner_initialized("admin", "") is None


# ---------------------------------------------------------------------------
# 邀请码测试
# ---------------------------------------------------------------------------
def test_generate_invite_code(tmp_db):
    """生成邀请码。"""
    from hermes_kb.users import create_user, generate_invite_code, list_invite_codes

    create_user("owner1", "pass", role="owner")
    result = generate_invite_code("owner1", role="member")
    assert "code" in result
    assert len(result["code"]) > 10
    assert result["role"] == "member"
    assert result["created_by"] == "owner1"

    # 数据库中应有该邀请码
    codes = list_invite_codes()
    assert len(codes) == 1
    assert codes[0]["code"] == result["code"]


def test_generate_invite_code_with_ttl(tmp_db):
    """带有效期的邀请码。"""
    from hermes_kb.users import create_user, generate_invite_code

    create_user("owner1", "pass", role="owner")
    result = generate_invite_code("owner1", role="member", ttl_hours=24)
    assert result["expires_at"] is not None


def test_generate_invite_code_owner_rejected(tmp_db):
    """不允许邀请 owner 角色。"""
    from hermes_kb.users import create_user, generate_invite_code

    create_user("owner1", "pass", role="owner")
    with pytest.raises(ValueError, match="不允许邀请 owner"):
        generate_invite_code("owner1", role="owner")


def test_consume_invite_code_success(tmp_db):
    """消费邀请码成功。"""
    from hermes_kb.users import (
        consume_invite_code,
        create_user,
        generate_invite_code,
    )

    create_user("owner1", "pass", role="owner")
    invite = generate_invite_code("owner1", role="member")
    result = consume_invite_code(invite["code"], "newuser1")
    assert result["role"] == "member"
    assert result["created_by"] == "owner1"


def test_consume_invite_code_already_used(tmp_db):
    """已使用的邀请码抛 LookupError。"""
    from hermes_kb.users import (
        consume_invite_code,
        create_user,
        generate_invite_code,
    )

    create_user("owner1", "pass", role="owner")
    invite = generate_invite_code("owner1", role="member")
    consume_invite_code(invite["code"], "user1")
    with pytest.raises(LookupError, match="已被使用"):
        consume_invite_code(invite["code"], "user2")


def test_consume_invite_code_not_found(tmp_db):
    """不存在的邀请码抛 LookupError。"""
    from hermes_kb.users import consume_invite_code

    with pytest.raises(LookupError, match="不存在"):
        consume_invite_code("nonexistent", "user1")


def test_consume_invite_code_expired(tmp_db):
    """过期邀请码抛 LookupError。"""
    from datetime import timedelta

    from hermes_kb.database import get_session
    from hermes_kb.models import InviteCode, _now_utc
    from hermes_kb.users import consume_invite_code

    # 直接构造一个已过期的邀请码
    with get_session() as session:
        invite = InviteCode(
            code="EXPIRED1",
            role="member",
            created_by="owner1",
            expires_at=_now_utc() - timedelta(hours=1),
        )
        session.add(invite)
        session.commit()

    with pytest.raises(LookupError, match="已过期"):
        consume_invite_code("EXPIRED1", "user1")


def test_list_invite_codes_active_only(tmp_db):
    """active_only 过滤已使用/过期邀请码。"""
    from datetime import timedelta

    from hermes_kb.database import get_session
    from hermes_kb.models import InviteCode, _now_utc
    from hermes_kb.users import (
        consume_invite_code,
        create_user,
        generate_invite_code,
        list_invite_codes,
    )

    create_user("owner1", "pass", role="owner")
    # 未使用未过期
    c1 = generate_invite_code("owner1", role="member")
    # 已使用
    c2 = generate_invite_code("owner1", role="member")
    consume_invite_code(c2["code"], "user1")
    # 已过期
    with get_session() as session:
        session.add(InviteCode(
            code="EXPIRED2",
            role="member",
            created_by="owner1",
            expires_at=_now_utc() - timedelta(hours=1),
        ))
        session.commit()

    all_codes = list_invite_codes()
    assert len(all_codes) == 3

    active = list_invite_codes(active_only=True)
    assert len(active) == 1
    assert active[0]["code"] == c1["code"]
