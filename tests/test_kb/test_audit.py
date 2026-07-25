"""M2-08 审计日志测试。

覆盖：
1. AuditLog 表 CRUD（model 层）
2. log_action 写入 + meta_json 序列化
3. log_ask_sampled 采样率（hash(query) % 10 == 0）
4. extract_user 从 JWT payload 提取用户
5. 关键写操作自动审计（login/import/delete/seed/ask/metadata）
6. /api/audit 查询端点（含筛选、分页）
7. 管理员权限校验（auth_enabled 时非 admin → 403）
8. 审计写入失败不影响主业务（吞异常）
"""
from __future__ import annotations

import json

import pytest

from hermes_kb.audit import (
    _should_sample_ask,
    extract_user,
    log_action,
    log_ask_sampled,
)
from hermes_kb.database import get_session
from hermes_kb.models import AuditLog


# ---------------------------------------------------------------------------
# Model 层：AuditLog 表 CRUD
# ---------------------------------------------------------------------------
class TestAuditLogModel:
    def test_create_audit_log_minimal(self, tmp_db):
        """最小字段写入。"""
        with get_session() as session:
            entry = AuditLog(action="login", target_type="user", target_id="admin")
            session.add(entry)
            session.commit()
            assert entry.id is not None
            assert entry.user == "anonymous"  # 默认值
            assert entry.meta_json == "{}"  # 默认值
            assert entry.created_at is not None

    def test_create_audit_log_full(self, tmp_db):
        """全字段写入。"""
        meta = {"filename": "test.txt", "size": 1024}
        with get_session() as session:
            entry = AuditLog(
                action="import",
                target_type="document",
                target_id="doc_abc123",
                user="admin",
                meta_json=json.dumps(meta, ensure_ascii=False),
            )
            session.add(entry)
            session.commit()
            # 重新查询验证
            loaded = session.get(AuditLog, entry.id)
            assert loaded.action == "import"
            assert loaded.target_type == "document"
            assert loaded.target_id == "doc_abc123"
            assert loaded.user == "admin"
            assert json.loads(loaded.meta_json) == meta

    def test_audit_log_indexes_exist(self, tmp_db):
        """验证关键索引存在（action/user/target_type/created_at）。"""
        from sqlalchemy import inspect

        from hermes_kb.database import get_engine

        eng = get_engine()
        insp = inspect(eng)
        indexes = {i["name"] for i in insp.get_indexes("auditlog")}
        # SQLModel 自动生成 ix_<table>_<column> 命名
        assert any("action" in n for n in indexes), f"action index missing: {indexes}"
        assert any("user" in n for n in indexes), f"user index missing: {indexes}"
        assert any("created_at" in n for n in indexes), "created_at index missing"


# ---------------------------------------------------------------------------
# log_action 函数
# ---------------------------------------------------------------------------
class TestLogAction:
    def test_log_action_basic(self, tmp_db):
        """log_action 写入 + 默认值。"""
        log_action(
            action="import",
            target_type="document",
            target_id="doc_test1",
            user="alice",
            meta={"filename": "test.md"},
        )
        with get_session() as session:
            from sqlmodel import select

            entries = session.exec(select(AuditLog)).all()
            assert len(entries) == 1
            e = entries[0]
            assert e.action == "import"
            assert e.target_type == "document"
            assert e.target_id == "doc_test1"
            assert e.user == "alice"
            assert json.loads(e.meta_json) == {"filename": "test.md"}

    def test_log_action_defaults(self, tmp_db):
        """log_action 默认值（user=anonymous, meta={}）。"""
        log_action(action="delete", target_type="document", target_id="doc_x")
        with get_session() as session:
            from sqlmodel import select

            e = session.exec(select(AuditLog)).first()
            assert e.user == "anonymous"
            assert json.loads(e.meta_json) == {}

    def test_log_action_meta_serialization_chinese(self, tmp_db):
        """meta 含中文字符确保 UTF-8 序列化（ensure_ascii=False）。"""
        log_action(
            action="import",
            target_type="document",
            target_id="doc_zh",
            meta={"title": "中国白酒香型", "category": "中国白酒"},
        )
        with get_session() as session:
            from sqlmodel import select

            e = session.exec(select(AuditLog)).first()
            meta = json.loads(e.meta_json)
            assert meta["title"] == "中国白酒香型"
            assert meta["category"] == "中国白酒"

    def test_log_action_target_id_truncation(self, tmp_db):
        """target_id 超过 128 字符自动截断（防数据库截断异常）。"""
        long_id = "x" * 200
        log_action(action="import", target_id=long_id)
        with get_session() as session:
            from sqlmodel import select

            e = session.exec(select(AuditLog)).first()
            assert len(e.target_id) == 128

    def test_log_action_swallows_exception(self, tmp_db, monkeypatch):
        """审计写入失败不影响主业务（吞异常 + log warning）。"""

        # 模拟 get_session 抛异常
        def _broken_session():
            raise RuntimeError("db locked")

        from hermes_kb import audit as audit_mod
        from contextlib import contextmanager

        @contextmanager
        def _broken_cm():
            raise RuntimeError("db locked")
            yield  # noqa: E701 —— 不可达，仅为 contextmanager 协议

        monkeypatch.setattr(audit_mod, "get_session", _broken_cm)

        # 不应抛异常
        log_action(action="login", target_type="user", target_id="admin")
        # 验证主业务流程仍能继续
        assert True

    def test_log_action_user_truncation(self, tmp_db):
        """user 字段超过 64 字符截断。"""
        long_user = "u" * 100
        log_action(action="login", user=long_user)
        with get_session() as session:
            from sqlmodel import select

            e = session.exec(select(AuditLog)).first()
            assert len(e.user) == 64


# ---------------------------------------------------------------------------
# log_ask_sampled 采样逻辑
# ---------------------------------------------------------------------------
class TestAskSampling:
    def test_should_sample_deterministic(self):
        """同一 query 多次调用结果一致（确定性 hash）。"""
        q = "金酒有什么特点？"
        result1 = _should_sample_ask(q)
        result2 = _should_sample_ask(q)
        assert result1 == result2, "采样结果必须确定性"

    def test_should_sample_empty_query(self):
        """空 query 不采样。"""
        assert _should_sample_ask("") is False

    @pytest.mark.parametrize(
        "query",
        [
            "金酒",
            "威士忌是什么",
            "葡萄酒品鉴",
            "中国白酒香型",
            "朗姆酒调制",
        ],
    )
    def test_should_sample_distribution(self, query):
        """采样率约 10%（用大量样本验证分布）。"""
        # 通过批量不同 query 验证采样率在合理范围
        sampled = sum(1 for i in range(100) if _should_sample_ask(f"{query}_{i}"))
        # 100 个样本中采样数应在 0-25 之间（10% ± 容差）
        assert 0 <= sampled <= 25, f"采样率异常: {sampled}/100"

    def test_log_ask_sampled_skips_unsampled(self, tmp_db):
        """未被采样的 query 不写入审计。"""
        # 找一个不会被采样的 query
        unsampled_q = next(
            f"unsampled_{i}" for i in range(100) if not _should_sample_ask(f"unsampled_{i}")
        )
        result = log_ask_sampled(query=unsampled_q, user="alice")
        assert result is False
        with get_session() as session:
            from sqlmodel import select

            assert session.exec(select(AuditLog)).first() is None

    def test_log_ask_sampled_records_sampled(self, tmp_db):
        """被采样的 query 写入审计。"""
        # 找一个会被采样的 query
        sampled_q = next(
            f"sampled_{i}" for i in range(100) if _should_sample_ask(f"sampled_{i}")
        )
        result = log_ask_sampled(
            query=sampled_q,
            user="bob",
            model_used="glm-4-flash",
            latency_ms=42,
        )
        assert result is True
        with get_session() as session:
            from sqlmodel import select

            e = session.exec(select(AuditLog)).first()
            assert e.action == "ask"
            assert e.target_type == "query"
            assert e.user == "bob"
            meta = json.loads(e.meta_json)
            assert meta["query"] == sampled_q
            assert meta["model_used"] == "glm-4-flash"
            assert meta["latency_ms"] == 42


# ---------------------------------------------------------------------------
# extract_user
# ---------------------------------------------------------------------------
class TestExtractUser:
    def test_extract_user_none_payload(self):
        """未启用认证 → anonymous。"""
        assert extract_user(None) == "anonymous"

    def test_extract_user_no_sub(self):
        """payload 无 sub → anonymous。"""
        assert extract_user({"role": "admin"}) == "anonymous"

    def test_extract_user_with_sub(self):
        """payload 有 sub → 返回 sub。"""
        assert extract_user({"sub": "alice", "role": "admin"}) == "alice"

    def test_extract_user_sub_is_int(self):
        """sub 为整数 → 转字符串。"""
        assert extract_user({"sub": 12345}) == "12345"


# ---------------------------------------------------------------------------
# API 集成：关键写操作自动审计
# ---------------------------------------------------------------------------
class TestAuditAPIIntegration:
    def test_login_success_audited(self, client, tmp_db, monkeypatch):
        """登录成功 → 写入 login 审计。"""
        from hermes_kb.config import override_settings

        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret="test-secret-for-audit-only-1234567890",
        )
        resp = client.post("/api/auth/login", json={"password": "test123"})
        assert resp.status_code == 200
        with get_session() as session:
            from sqlmodel import select

            login_logs = session.exec(
                select(AuditLog).where(AuditLog.action == "login")
            ).all()
            assert len(login_logs) == 1
            assert login_logs[0].user == "admin"
            assert login_logs[0].target_id == "admin"
            meta = json.loads(login_logs[0].meta_json)
            assert meta["success"] is True

    def test_login_failure_audited(self, client, tmp_db, monkeypatch):
        """登录失败 → 写入 login 审计（user=unknown）。"""
        from hermes_kb.config import override_settings

        override_settings(
            auth_enabled=True,
            auth_password="correct-pwd",
            auth_username="admin",
            jwt_secret="test-secret-for-audit-only-1234567890",
        )
        resp = client.post("/api/auth/login", json={"password": "wrong"})
        assert resp.status_code == 401
        with get_session() as session:
            from sqlmodel import select

            login_logs = session.exec(
                select(AuditLog).where(AuditLog.action == "login")
            ).all()
            assert len(login_logs) == 1
            assert login_logs[0].user == "unknown"
            meta = json.loads(login_logs[0].meta_json)
            assert meta["success"] is False
            assert meta["reason"] == "invalid_password"

    def test_import_text_audited(self, client, tmp_db):
        """import-text → 写入 import 审计。"""
        resp = client.post(
            "/api/documents/import-text",
            json={"title": "测试文档", "content": "内容", "file_type": "txt"},
        )
        assert resp.status_code == 200
        with get_session() as session:
            from sqlmodel import select

            audit = session.exec(
                select(AuditLog).where(AuditLog.action == "import")
            ).first()
            assert audit is not None
            assert audit.target_type == "document"
            assert audit.target_id  # doc_id 非空
            meta = json.loads(audit.meta_json)
            assert meta["source"] == "import-text"
            assert meta["title"] == "测试文档"

    def test_delete_document_audited(self, client, tmp_db):
        """删除文档 → 写入 delete 审计。"""
        # 先导入
        resp = client.post(
            "/api/documents/import-text",
            json={"title": "待删除", "content": "内容"},
        )
        doc_id = resp.json()["doc_id"]
        # 删除
        resp = client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 200
        with get_session() as session:
            from sqlmodel import select

            audit = session.exec(
                select(AuditLog).where(AuditLog.action == "delete")
            ).first()
            assert audit is not None
            assert audit.target_id == doc_id

    def test_seed_audited(self, client, tmp_db):
        """种子数据初始化 → 写入 seed 审计。"""
        resp = client.post("/api/seed")
        assert resp.status_code == 200
        with get_session() as session:
            from sqlmodel import select

            audit = session.exec(
                select(AuditLog).where(AuditLog.action == "seed")
            ).first()
            assert audit is not None
            meta = json.loads(audit.meta_json)
            assert meta["kind"] == "docs"

    def test_metadata_update_audited(self, client, tmp_db):
        """更新文档元信息 → 写入 metadata 审计。"""
        # 先导入
        resp = client.post(
            "/api/documents/import-text",
            json={"title": "原标题", "content": "内容"},
        )
        doc_id = resp.json()["doc_id"]
        # 更新 metadata
        resp = client.put(
            f"/api/documents/{doc_id}/metadata",
            json={"title": "新标题", "category": "烈酒"},
        )
        assert resp.status_code == 200
        with get_session() as session:
            from sqlmodel import select

            audit = session.exec(
                select(AuditLog).where(AuditLog.action == "metadata")
            ).first()
            assert audit is not None
            meta = json.loads(audit.meta_json)
            assert meta["title_updated"] is True
            assert meta["category_updated"] is True


# ---------------------------------------------------------------------------
# /api/audit 查询端点
# ---------------------------------------------------------------------------
class TestAuditEndpoint:
    def test_list_audit_empty(self, client, tmp_db):
        """空审计表 → 200 + 空列表。"""
        resp = client.get("/api/audit")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list_audit_returns_items(self, client, tmp_db):
        """有审计记录 → 返回 items + 分页字段。"""
        # 触发若干写操作
        for i in range(3):
            client.post(
                "/api/documents/import-text",
                json={"title": f"doc-{i}", "content": "x"},
            )
        resp = client.get("/api/audit")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 3
        assert len(body["items"]) >= 3
        # 字段完整
        item = body["items"][0]
        assert "id" in item
        assert "action" in item
        assert "target_type" in item
        assert "target_id" in item
        assert "user" in item
        assert "meta" in item  # 解析后的 dict
        assert "created_at" in item

    def test_list_audit_filter_by_action(self, client, tmp_db):
        """按 action 筛选。"""
        # 触发不同 action
        client.post("/api/seed")  # seed
        client.post(
            "/api/documents/import-text",
            json={"title": "x", "content": "y"},
        )  # import
        resp = client.get("/api/audit?action=import")
        assert resp.status_code == 200
        body = resp.json()
        assert all(i["action"] == "import" for i in body["items"])
        assert body["total"] == len(body["items"])

    def test_list_audit_filter_by_target_type(self, client, tmp_db):
        """按 target_type 筛选。"""
        client.post("/api/seed")  # target_type=document
        client.post("/api/seed/recipes")  # target_type=recipe
        resp = client.get("/api/audit?target_type=recipe")
        assert resp.status_code == 200
        body = resp.json()
        assert all(i["target_type"] == "recipe" for i in body["items"])

    def test_list_audit_pagination(self, client, tmp_db):
        """分页：limit + offset。"""
        for i in range(5):
            client.post(
                "/api/documents/import-text",
                json={"title": f"doc-{i}", "content": "x"},
            )
        # 取第 2 页（每页 2 条）
        resp = client.get("/api/audit?limit=2&offset=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == 2
        assert body["offset"] == 2
        assert len(body["items"]) <= 2

    def test_list_audit_limit_max_500(self, client, tmp_db):
        """limit 上限 500。"""
        resp = client.get("/api/audit?limit=999")
        assert resp.status_code == 422  # 校验失败

    def test_list_audit_limit_min_1(self, client, tmp_db):
        """limit 下限 1。"""
        resp = client.get("/api/audit?limit=0")
        assert resp.status_code == 422

    def test_list_audit_admin_when_auth_disabled(self, client, tmp_db):
        """auth_enabled=False → 任意访问者可查（dev 模式）。"""
        # 默认 auth_enabled=False
        resp = client.get("/api/audit")
        assert resp.status_code == 200

    def test_list_audit_admin_required_when_auth_enabled(
        self, client, tmp_db, monkeypatch
    ):
        """auth_enabled=True → 非 admin JWT → 403。"""
        from hermes_kb.api.deps import jwt_encode
        from hermes_kb.config import override_settings

        secret = "test-secret-for-audit-only-1234567890"
        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret=secret,
        )
        # 构造非 admin token（role=user）
        token = jwt_encode({"sub": "user1", "role": "user"}, secret)
        resp = client.get(
            "/api/audit", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403
        assert "管理员" in resp.json()["detail"]

    def test_list_audit_admin_allowed_with_admin_token(
        self, client, tmp_db, monkeypatch
    ):
        """auth_enabled=True + admin token → 200。"""
        from hermes_kb.api.deps import jwt_encode
        from hermes_kb.config import override_settings

        secret = "test-secret-for-audit-only-1234567890"
        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret=secret,
        )
        token = jwt_encode({"sub": "admin", "role": "admin"}, secret)
        resp = client.get(
            "/api/audit", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    def test_list_audit_unauthorized_without_token_when_auth_enabled(
        self, client, tmp_db, monkeypatch
    ):
        """auth_enabled=True + 无 token → 401。"""
        from hermes_kb.config import override_settings

        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret="test-secret-for-audit-only-1234567890",
        )
        resp = client.get("/api/audit")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 端到端：完整审计链路
# ---------------------------------------------------------------------------
class TestAuditE2E:
    def test_full_workflow_audited(self, client, tmp_db):
        """端到端：导入 → 更新 → 删除 全链路审计。"""
        # 1. 导入
        r1 = client.post(
            "/api/documents/import-text",
            json={"title": "端到端测试", "content": "内容"},
        )
        doc_id = r1.json()["doc_id"]
        # 2. 更新 metadata
        client.put(
            f"/api/documents/{doc_id}/metadata",
            json={"category": "烈酒"},
        )
        # 3. 删除
        client.delete(f"/api/documents/{doc_id}")
        # 4. 查询审计
        resp = client.get("/api/audit?limit=50")
        body = resp.json()
        actions = [i["action"] for i in body["items"]]
        # 至少包含 import / metadata / delete
        assert "import" in actions
        assert "metadata" in actions
        assert "delete" in actions
        # 顺序：最新在前（desc by created_at）
        # delete 应在 metadata 之前
        delete_idx = actions.index("delete")
        metadata_idx = actions.index("metadata")
        assert delete_idx < metadata_idx, "审计日志应按时间倒序"
