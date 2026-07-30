"""V3-Task10: 认证流程升级测试（multiuser 模式）。"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# require_role 中间件测试
# ---------------------------------------------------------------------------
def test_require_role_disabled_multiuser(client):
    """未启用 multiuser 时 require_role 放行（向后兼容）。"""
    # client fixture 默认 KB_MULTIUSER=false，访问 /auth/me 不应 403
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200


def test_multi_login_disabled_returns_400(client):
    """未启用 multiuser 时 multi-login 返回 400。"""
    resp = client.post("/api/auth/multi-login", json={
        "username": "admin",
        "password": "pass",
    })
    assert resp.status_code == 400
    assert "多用户模式未启用" in resp.json()["detail"]


def test_register_disabled_returns_400(client):
    """未启用 multiuser 时 register 返回 400。"""
    resp = client.post("/api/auth/register", json={
        "invite_code": "ABC",
        "username": "newuser",
        "password": "password123",
    })
    assert resp.status_code == 400


def test_invite_endpoint_requires_auth(monkeypatch):
    """invite 端点在 multiuser 模式下需要登录。"""
    from fastapi.testclient import TestClient

    from hermes_kb.app import create_app
    from hermes_kb.config import get_settings, reset_settings

    reset_settings()
    import os
    monkeypatch.setenv("KB_MULTIUSER", "true")
    monkeypatch.setenv("KB_AUTH_ENABLED", "true")
    monkeypatch.setenv("KB_AUTH_PASSWORD", "secret")
    monkeypatch.setenv("KB_JWT_SECRET", "test-secret-key-for-multiuser")

    app = create_app()
    with TestClient(app) as c:
        # 未登录调用 invite → 401
        resp = c.post("/api/auth/invite", json={"role": "member"})
        assert resp.status_code == 401

    reset_settings()


# ---------------------------------------------------------------------------
# multiuser 模式完整流程测试
# ---------------------------------------------------------------------------
@pytest.fixture
def multiuser_client(tmp_db, monkeypatch):
    """启用 multiuser + auth 的 TestClient。

    预置 owner 账户（admin/secret），返回 (client, owner_token)。
    """
    from fastapi.testclient import TestClient

    from hermes_kb.app import create_app
    from hermes_kb.config import reset_settings

    reset_settings()
    monkeypatch.setenv("KB_MULTIUSER", "true")
    monkeypatch.setenv("KB_AUTH_ENABLED", "true")
    monkeypatch.setenv("KB_AUTH_PASSWORD", "secret")
    monkeypatch.setenv("KB_USERNAME", "admin")
    monkeypatch.setenv("KB_JWT_SECRET", "test-secret-key-for-multiuser")

    app = create_app()
    with TestClient(app) as c:
        c.post("/api/age-gate/confirm", json={"confirmed": True})
        # 首次 multi-login 触发 owner 初始化
        resp = c.post("/api/auth/multi-login", json={
            "username": "admin",
            "password": "secret",
        })
        assert resp.status_code == 200
        token = resp.json()["token"]
        yield c, token

    reset_settings()


def test_multi_login_owner_init(multiuser_client):
    """首次 multi-login 自动初始化 owner 账户。"""
    client, token = multiuser_client
    assert token  # 非空 token

    # /auth/me 应返回 owner 角色
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert body["role"] == "owner"
    assert body["multiuser"] is True


def test_multi_login_wrong_password(multiuser_client):
    """错误密码登录失败。"""
    client, _ = multiuser_client
    resp = client.post("/api/auth/multi-login", json={
        "username": "admin",
        "password": "wrong",
    })
    assert resp.status_code == 401


def test_multi_login_unknown_user(multiuser_client):
    """不存在的用户登录失败。"""
    client, _ = multiuser_client
    resp = client.post("/api/auth/multi-login", json={
        "username": "nobody",
        "password": "pass",
    })
    assert resp.status_code == 401


def test_owner_generate_invite(multiuser_client):
    """owner 生成邀请码。"""
    client, token = multiuser_client
    resp = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "code" in body
    assert body["role"] == "member"
    assert body["created_by"] == "admin"


def test_owner_generate_invite_owner_rejected(multiuser_client):
    """owner 不允许邀请 owner 角色。"""
    client, token = multiuser_client
    resp = client.post(
        "/api/auth/invite",
        json={"role": "owner"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_member_cannot_invite(multiuser_client):
    """member 角色不能生成邀请码。"""
    client, owner_token = multiuser_client

    # owner 生成邀请码
    invite_resp = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    code = invite_resp.json()["code"]

    # member 注册
    reg_resp = client.post("/api/auth/register", json={
        "invite_code": code,
        "username": "member1",
        "password": "memberpass",
    })
    assert reg_resp.status_code == 200
    member_token = reg_resp.json()["token"]

    # member 尝试生成邀请码 → 403
    resp = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert resp.status_code == 403


def test_register_with_invite_code(multiuser_client):
    """邀请码注册新用户完整流程。"""
    client, owner_token = multiuser_client

    # 生成邀请码
    invite_resp = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    code = invite_resp.json()["code"]

    # 注册
    reg_resp = client.post("/api/auth/register", json={
        "invite_code": code,
        "username": "newuser",
        "password": "newpass123",
    })
    assert reg_resp.status_code == 200
    body = reg_resp.json()
    assert body["username"] == "newuser"
    assert body["role"] == "member"
    assert body["token"]

    # 新用户可登录
    login_resp = client.post("/api/auth/multi-login", json={
        "username": "newuser",
        "password": "newpass123",
    })
    assert login_resp.status_code == 200


def test_register_reused_invite_rejected(multiuser_client):
    """已使用的邀请码不能再次注册。"""
    client, owner_token = multiuser_client

    invite_resp = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    code = invite_resp.json()["code"]

    # 第一次注册成功
    client.post("/api/auth/register", json={
        "invite_code": code,
        "username": "user1",
        "password": "pass123456",
    })

    # 第二次注册失败
    resp = client.post("/api/auth/register", json={
        "invite_code": code,
        "username": "user2",
        "password": "pass123456",
    })
    assert resp.status_code == 400
    assert "已被使用" in resp.json()["detail"]


def test_register_duplicate_username(multiuser_client):
    """注册已存在的用户名失败。"""
    client, owner_token = multiuser_client

    # 生成两个邀请码
    c1 = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["code"]
    c2 = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["code"]

    # 第一次注册成功
    client.post("/api/auth/register", json={
        "invite_code": c1,
        "username": "sameuser",
        "password": "pass123456",
    })

    # 第二次同名注册失败（但第二个邀请码已被消费）
    resp = client.post("/api/auth/register", json={
        "invite_code": c2,
        "username": "sameuser",
        "password": "pass123456",
    })
    assert resp.status_code == 400
    assert "已存在" in resp.json()["detail"]


def test_register_short_password_rejected(multiuser_client):
    """密码长度 <6 被拒绝（Pydantic 校验）。"""
    client, owner_token = multiuser_client

    invite_resp = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    code = invite_resp.json()["code"]

    resp = client.post("/api/auth/register", json={
        "invite_code": code,
        "username": "user1",
        "password": "12345",  # 5 字符
    })
    assert resp.status_code == 422  # Pydantic 校验失败


def test_owner_list_users(multiuser_client):
    """owner 查看用户列表。"""
    client, owner_token = multiuser_client

    # 生成邀请码并注册一个 member
    code = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["code"]
    client.post("/api/auth/register", json={
        "invite_code": code,
        "username": "member1",
        "password": "pass123456",
    })

    # owner 查看用户列表
    resp = client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    users = resp.json()["items"]
    usernames = [u["username"] for u in users]
    assert "admin" in usernames
    assert "member1" in usernames


def test_member_cannot_list_users(multiuser_client):
    """member 不能查看用户列表。"""
    client, owner_token = multiuser_client

    code = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["code"]
    reg = client.post("/api/auth/register", json={
        "invite_code": code,
        "username": "member1",
        "password": "pass123456",
    })
    member_token = reg.json()["token"]

    resp = client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert resp.status_code == 403


def test_owner_list_invites(multiuser_client):
    """owner 查看邀请码列表。"""
    client, owner_token = multiuser_client

    client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    resp = client.get(
        "/api/auth/invites",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    invites = resp.json()["items"]
    assert len(invites) >= 1


def test_owner_update_user_role(multiuser_client):
    """owner 修改用户角色。"""
    client, owner_token = multiuser_client

    # 注册一个 member
    code = client.post(
        "/api/auth/invite",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["code"]
    client.post("/api/auth/register", json={
        "invite_code": code,
        "username": "member1",
        "password": "pass123456",
    })

    # 提升为 owner
    resp = client.post(
        "/api/auth/users/member1/role",
        json={"role": "owner"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "owner"


def test_owner_update_role_not_found(multiuser_client):
    """修改不存在用户返回 404。"""
    client, owner_token = multiuser_client

    resp = client.post(
        "/api/auth/users/nobody/role",
        json={"role": "owner"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 404


def test_owner_update_role_invalid(multiuser_client):
    """非法角色返回 400。"""
    client, owner_token = multiuser_client

    resp = client.post(
        "/api/auth/users/admin/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 400


def test_me_returns_role_in_multiuser(multiuser_client):
    """/auth/me 在 multiuser 模式返回 role 字段。"""
    client, token = multiuser_client

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["multiuser"] is True
    assert body["role"] == "owner"


def test_viewer_cannot_access_owner_endpoints(multiuser_client):
    """viewer 角色被 owner 端点拒绝。"""
    client, owner_token = multiuser_client

    # 注册一个 viewer
    code = client.post(
        "/api/auth/invite",
        json={"role": "viewer"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["code"]
    reg = client.post("/api/auth/register", json={
        "invite_code": code,
        "username": "viewer1",
        "password": "pass123456",
    })
    viewer_token = reg.json()["token"]
    assert reg.json()["role"] == "viewer"

    # viewer 不能访问 owner 端点
    resp = client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


def test_invite_with_ttl(multiuser_client):
    """带有效期的邀请码。"""
    client, owner_token = multiuser_client

    resp = client.post(
        "/api/auth/invite",
        json={"role": "member", "ttl_hours": 24},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["expires_at"] is not None
