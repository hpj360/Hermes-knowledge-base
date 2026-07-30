# -*- coding: utf-8 -*-
"""V5：结构化反馈测试——comment + tag + 汇总端点。

覆盖：
- POST /api/feedback/{log_id} 提交带 comment 的反馈
- POST /api/feedback/{log_id} 提交带 tag 的反馈
- POST /api/feedback/{log_id} 提交空 comment（仅评分）
- GET /api/feedback/list 返回带评论的反馈
- GET /api/feedback/list?tag=... 标签筛选
- GET /api/feedback/list 分页
- 单用户模式下 /feedback/list 放行（向后兼容）
- multiuser 模式下 member 角色访问 /feedback/list 返回 403
"""
from __future__ import annotations

import pytest


def _create_query_log(client, query: str = "测试问题") -> int:
    """通过 /api/ask 创建一条 QueryLog，返回 log_id。"""
    client.post("/api/seed")
    resp = client.post("/api/ask", json={"query": query})
    assert resp.status_code == 200
    # /api/history 倒序，最新在最前
    hist = client.get("/api/history").json()
    assert hist["items"], "ask 后应有历史记录"
    return hist["items"][0]["id"]


# ---------------------------------------------------------------------------
# POST /api/feedback/{log_id} 结构化反馈
# ---------------------------------------------------------------------------

def test_feedback_with_comment(client):
    """提交带 comment 的反馈：comment 应被持久化。"""
    log_id = _create_query_log(client, "金酒的核心风味是什么？")
    resp = client.post(
        f"/api/feedback/{log_id}",
        json={"feedback": -1, "comment": "答案把伏特加和金酒搞混了"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["feedback"] == -1
    assert body["status"] == "ok"

    # 验证持久化
    from hermes_kb.database import get_session
    from hermes_kb.models import QueryLog

    with get_session() as session:
        log = session.get(QueryLog, log_id)
        assert log.feedback == -1
        assert log.feedback_comment == "答案把伏特加和金酒搞混了"


def test_feedback_with_tag(client):
    """提交带 tag 的反馈：tag 应被持久化。"""
    log_id = _create_query_log(client, "波本威士忌是什么？")
    resp = client.post(
        f"/api/feedback/{log_id}",
        json={"feedback": -1, "tag": "inaccurate"},
    )
    assert resp.status_code == 200

    from hermes_kb.database import get_session
    from hermes_kb.models import QueryLog

    with get_session() as session:
        log = session.get(QueryLog, log_id)
        assert log.feedback == -1
        assert log.feedback_tag == "inaccurate"


def test_feedback_with_comment_and_tag(client):
    """同时提交 comment + tag。"""
    log_id = _create_query_log(client, "如何调制马天尼？")
    resp = client.post(
        f"/api/feedback/{log_id}",
        json={
            "feedback": -1,
            "comment": "引用的配方比例不对",
            "tag": "wrong_citation",
        },
    )
    assert resp.status_code == 200

    from hermes_kb.database import get_session
    from hermes_kb.models import QueryLog

    with get_session() as session:
        log = session.get(QueryLog, log_id)
        assert log.feedback == -1
        assert log.feedback_comment == "引用的配方比例不对"
        assert log.feedback_tag == "wrong_citation"


def test_feedback_without_comment(client):
    """仅评分（不传 comment/tag）：保持原空值，向后兼容。"""
    log_id = _create_query_log(client, "朗姆酒种类")
    resp = client.post(f"/api/feedback/{log_id}", json={"feedback": 1})
    assert resp.status_code == 200

    from hermes_kb.database import get_session
    from hermes_kb.models import QueryLog

    with get_session() as session:
        log = session.get(QueryLog, log_id)
        assert log.feedback == 1
        # comment/tag 应保持默认空串
        assert log.feedback_comment == ""
        assert log.feedback_tag == ""


def test_feedback_comment_max_length_enforced(client):
    """comment 字段受 Pydantic max_length=500 限制。

    - 恰好 500 字：被接受
    - 超过 500 字：返回 422（Pydantic 在端点入口校验）
    """
    log_id = _create_query_log(client, "威士忌产区")

    # 500 字恰好被接受
    resp_500 = client.post(
        f"/api/feedback/{log_id}",
        json={"feedback": -1, "comment": "x" * 500},
    )
    assert resp_500.status_code == 200

    # 501 字被 Pydantic 拒绝（422）
    resp_501 = client.post(
        f"/api/feedback/{log_id}",
        json={"feedback": -1, "comment": "x" * 501},
    )
    assert resp_501.status_code == 422


def test_feedback_up_with_comment(client):
    """👍 评分也可附带评论（用于好评）。"""
    log_id = _create_query_log(client, "白兰地历史")
    resp = client.post(
        f"/api/feedback/{log_id}",
        json={"feedback": 1, "comment": "讲解很清晰，引用准确"},
    )
    assert resp.status_code == 200

    from hermes_kb.database import get_session
    from hermes_kb.models import QueryLog

    with get_session() as session:
        log = session.get(QueryLog, log_id)
        assert log.feedback == 1
        assert log.feedback_comment == "讲解很清晰，引用准确"


# ---------------------------------------------------------------------------
# GET /api/feedback/list 汇总端点
# ---------------------------------------------------------------------------

def test_feedback_list_returns_only_commented(client):
    """仅返回 feedback_comment 非空的记录。"""
    # 第一条：带评论
    log1 = _create_query_log(client, "金酒是什么")
    client.post(
        f"/api/feedback/{log1}",
        json={"feedback": -1, "comment": "答非所问", "tag": "inaccurate"},
    )
    # 第二条：仅评分，无评论
    log2 = _create_query_log(client, "威士忌是什么")
    client.post(f"/api/feedback/{log2}", json={"feedback": 1})

    resp = client.get("/api/feedback/list")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["log_id"] == log1
    assert body["items"][0]["comment"] == "答非所问"
    assert body["items"][0]["tag"] == "inaccurate"
    assert body["items"][0]["feedback"] == -1


def test_feedback_list_tag_filter(client):
    """按 tag 筛选反馈列表。"""
    # 三条反馈：不同 tag
    log1 = _create_query_log(client, "问题 A")
    client.post(
        f"/api/feedback/{log1}",
        json={"feedback": -1, "comment": "答案不准", "tag": "inaccurate"},
    )
    log2 = _create_query_log(client, "问题 B")
    client.post(
        f"/api/feedback/{log2}",
        json={"feedback": -1, "comment": "找不到文档", "tag": "not_found"},
    )
    log3 = _create_query_log(client, "问题 C")
    client.post(
        f"/api/feedback/{log3}",
        json={"feedback": -1, "comment": "引用错误", "tag": "wrong_citation"},
    )

    # 筛选 inaccurate
    resp = client.get("/api/feedback/list", params={"tag": "inaccurate"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["log_id"] == log1
    assert body["items"][0]["tag"] == "inaccurate"

    # 筛选 not_found
    resp = client.get("/api/feedback/list", params={"tag": "not_found"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["log_id"] == log2


def test_feedback_list_pagination(client):
    """分页：limit + offset。"""
    # 创建 3 条带评论的反馈
    for i in range(3):
        log_id = _create_query_log(client, f"问题 {i}")
        client.post(
            f"/api/feedback/{log_id}",
            json={"feedback": -1, "comment": f"评论 {i}", "tag": "other"},
        )

    # limit=2 应返回 2 条，total=3
    resp = client.get("/api/feedback/list", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 0

    # offset=2 应返回剩余 1 条
    resp = client.get("/api/feedback/list", params={"limit": 2, "offset": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 1


def test_feedback_list_query_truncated(client):
    """query 字段超过 100 字时被截断。"""
    long_query = "请详细解释" + "酒" * 200 + "的工艺"
    log_id = _create_query_log(client, long_query)
    client.post(
        f"/api/feedback/{log_id}",
        json={"feedback": -1, "comment": "回答过长没切中要点", "tag": "inaccurate"},
    )

    resp = client.get("/api/feedback/list")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    query_text = body["items"][0]["query"]
    # 截断后应为 100 字 + "…" = 101 字符
    assert len(query_text) == 101
    assert query_text.endswith("…")


def test_feedback_list_empty(client):
    """无评论反馈时返回空列表。"""
    resp = client.get("/api/feedback/list")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_feedback_list_single_user_mode_allowed(client):
    """单用户模式（默认）下 /feedback/list 放行，不要求角色。

    client fixture 默认 KB_MULTIUSER=false，require_role 直接放行。
    """
    log_id = _create_query_log(client, "单用户模式测试")
    client.post(
        f"/api/feedback/{log_id}",
        json={"feedback": -1, "comment": "测试", "tag": "other"},
    )
    resp = client.get("/api/feedback/list")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ---------------------------------------------------------------------------
# multiuser 模式权限测试
# ---------------------------------------------------------------------------

@pytest.fixture
def multiuser_client(tmp_db, monkeypatch):
    """启用 multiuser + auth 的 TestClient，预置 owner 与 member 账户。"""
    from fastapi.testclient import TestClient

    from hermes_kb.app import create_app
    from hermes_kb.config import reset_settings

    reset_settings()
    monkeypatch.setenv("KB_MULTIUSER", "true")
    monkeypatch.setenv("KB_AUTH_ENABLED", "true")
    monkeypatch.setenv("KB_AUTH_PASSWORD", "secret")
    monkeypatch.setenv("KB_USERNAME", "admin")
    monkeypatch.setenv("KB_JWT_SECRET", "test-secret-key-for-feedback")

    app = create_app()
    with TestClient(app) as c:
        c.post("/api/age-gate/confirm", json={"confirmed": True})
        # owner 初始化
        resp = c.post("/api/auth/multi-login", json={"username": "admin", "password": "secret"})
        assert resp.status_code == 200
        owner_token = resp.json()["token"]

        # owner 生成邀请码 + 注册 member
        invite = c.post(
            "/api/auth/invite",
            json={"role": "member"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert invite.status_code == 200
        code = invite.json()["code"]
        reg = c.post("/api/auth/register", json={
            "invite_code": code,
            "username": "member1",
            "password": "memberpass",
        })
        assert reg.status_code == 200
        member_token = reg.json()["token"]
        yield c, owner_token, member_token

    reset_settings()


def test_feedback_list_member_forbidden(multiuser_client):
    """multiuser 模式下 member 角色访问 /feedback/list 返回 403。"""
    client, _owner_token, member_token = multiuser_client
    resp = client.get(
        "/api/feedback/list",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert resp.status_code == 403


def test_feedback_list_owner_allowed(multiuser_client):
    """multiuser 模式下 owner 角色可访问 /feedback/list。"""
    client, owner_token, _member_token = multiuser_client
    resp = client.get(
        "/api/feedback/list",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body


def test_feedback_list_unauthenticated_401(multiuser_client):
    """multiuser 模式下未认证访问 /feedback/list 返回 401。"""
    client, _owner, _member = multiuser_client
    resp = client.get("/api/feedback/list")
    assert resp.status_code == 401
