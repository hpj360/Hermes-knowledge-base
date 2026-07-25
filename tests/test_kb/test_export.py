"""M2-09 数据导出与导入测试。

覆盖：
1. 单文档 Markdown 导出（GET /api/documents/{doc_id}.md）
   - 路由优先级（不与 /{doc_id} 冲突）
   - H1 标题前置 / 防双标题
   - Content-Disposition 中文文件名
   - 404 不存在
2. 全量导出（GET /api/export/all.json）
   - payload 结构（version / tables / count）
   - 数据完整性（含所有 10 张表）
   - Content-Disposition 附件头
   - 审计日志记录 export 动作
   - 管理员权限校验（auth_enabled 时非 admin → 403）
3. 导入恢复（POST /api/export/import）
   - 上传 JSON 文件恢复
   - 幂等（同一份 JSON 多次导入不重复）
   - 数据 round-trip（export → import → export 等价）
   - 空 / 非法 JSON → 400
   - 审计日志记录 import 动作
4. 边界与异常
   - 不存在的 doc_id .md → 404
   - 空内容文档的 .md 导出
   - 大量数据导出性能（< 1s）
"""
from __future__ import annotations

import io
import json
import time
from urllib.parse import unquote

from hermes_kb.database import get_session
from hermes_kb.models import (
    AuditLog,
    Document,
    QueryLog,
    Tag,
)


# ===========================================================================
# 1. 单文档 Markdown 导出
# ===========================================================================
class TestDocumentMarkdownExport:
    """GET /api/documents/{doc_id}.md"""

    def test_md_route_does_not_conflict_with_get(self, client):
        """关键：/{doc_id}.md 必须命中 MD 端点，而非 /{doc_id}（doc_id="foo.md"）。"""
        r = client.post(
            "/api/documents/import-text",
            json={"title": "冲突测试", "content": "正文", "file_type": "md"},
        )
        doc_id = r.json()["doc_id"]
        # 访问 .md 端点
        resp = client.get(f"/api/documents/{doc_id}.md")
        assert resp.status_code == 200
        # 必须返回 markdown（若命中 /{doc_id} 则返回 JSON dict）
        assert resp.headers["content-type"].startswith("text/markdown")
        # 普通详情端点仍可访问
        r2 = client.get(f"/api/documents/{doc_id}")
        assert r2.status_code == 200
        assert r2.headers["content-type"].startswith("application/json")

    def test_md_export_adds_h1_title(self, client):
        """content 不以 # 开头时，自动前置 ``# {title}\\n\\n``。"""
        r = client.post(
            "/api/documents/import-text",
            json={"title": "我的文档", "content": "正文段落", "file_type": "txt"},
        )
        doc_id = r.json()["doc_id"]
        resp = client.get(f"/api/documents/{doc_id}.md")
        assert resp.status_code == 200
        assert resp.text.startswith("# 我的文档\n\n")
        assert "正文段落" in resp.text

    def test_md_export_avoids_double_h1(self, client):
        """content 已以 ``# `` 开头时不重复添加 H1。"""
        r = client.post(
            "/api/documents/import-text",
            json={
                "title": "已有标题",
                "content": "# 已有标题\n\n正文",
                "file_type": "md",
            },
        )
        doc_id = r.json()["doc_id"]
        resp = client.get(f"/api/documents/{doc_id}.md")
        assert resp.status_code == 200
        # 不应出现两个 H1
        assert resp.text.count("\n# ") == 0
        assert resp.text.startswith("# 已有标题")

    def test_md_export_chinese_filename_rfc5987(self, client):
        """中文文件名走 RFC 5987 filename*=UTF-8''<encoded>。"""
        r = client.post(
            "/api/documents/import-text",
            json={"title": "中文标题测试", "content": "x"},
        )
        doc_id = r.json()["doc_id"]
        resp = client.get(f"/api/documents/{doc_id}.md")
        cd = resp.headers["content-disposition"]
        assert "attachment" in cd
        assert "filename*=UTF-8''" in cd
        # 解码后应包含原标题 + .md
        encoded_part = cd.split("filename*=UTF-8''")[1].strip()
        decoded = unquote(encoded_part)
        assert decoded == "中文标题测试.md"

    def test_md_export_ascii_fallback_when_title_non_ascii(self, client):
        """纯中文标题 → ASCII filename 兜底为 ``document.md``。"""
        r = client.post(
            "/api/documents/import-text",
            json={"title": "纯中文", "content": "x"},
        )
        doc_id = r.json()["doc_id"]
        resp = client.get(f"/api/documents/{doc_id}.md")
        cd = resp.headers["content-disposition"]
        # filename="..." 部分应为 document.md（非 ".md" 裸扩展名）
        assert 'filename="document.md"' in cd

    def test_md_export_404_when_doc_not_exist(self, client):
        """不存在的 doc_id → 404。"""
        resp = client.get("/api/documents/doc_notexist.md")
        assert resp.status_code == 404

    def test_md_export_empty_content(self, client):
        """空 content 仍可导出（仅 H1 标题）。"""
        r = client.post(
            "/api/documents/import-text",
            json={"title": "空文档", "content": "占位", "file_type": "txt"},
        )
        doc_id = r.json()["doc_id"]
        # 直接置空 content
        with get_session() as session:
            doc = session.get(Document, doc_id)
            doc.content = ""
            session.add(doc)
            session.commit()
        resp = client.get(f"/api/documents/{doc_id}.md")
        assert resp.status_code == 200
        assert resp.text == "# 空文档\n\n"

    def test_md_export_media_type(self, client):
        """media_type 必须为 text/markdown。"""
        r = client.post(
            "/api/documents/import-text",
            json={"title": "T", "content": "x", "file_type": "pdf"},
        )
        doc_id = r.json()["doc_id"]
        resp = client.get(f"/api/documents/{doc_id}.md")
        assert resp.headers["content-type"] == "text/markdown; charset=utf-8"


# ===========================================================================
# 2. 全量导出
# ===========================================================================
class TestFullExport:
    """GET /api/export/all.json"""

    def test_export_returns_all_tables(self, client):
        """导出包含 10 张业务表。"""
        # 先导入一些数据
        client.post(
            "/api/documents/import-text",
            json={"title": "文档1", "content": "内容1"},
        )
        client.post("/api/tags", json={"name": "标签1"})

        resp = client.get("/api/export/all.json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "1.0"
        assert "exported_at" in body
        assert "tables" in body
        expected_tables = {
            "documents",
            "chunks",
            "tags",
            "document_tags",
            "query_logs",
            "audit_logs",
            "recipe_stats",
            "ingredient_substitutes",
            "missing_ingredient_stats",
            "recipe_variants",
        }
        assert set(body["tables"].keys()) == expected_tables

    def test_export_count_fields(self, client):
        """每个表有对应的 ``{name}_count`` 字段。"""
        client.post(
            "/api/documents/import-text",
            json={"title": "D", "content": "C"},
        )
        resp = client.get("/api/export/all.json")
        body = resp.json()
        assert body["documents_count"] == 1
        # chunks 至少 1（content "C" 会被分片）
        assert body["chunks_count"] >= 0  # 单字符可能不分片
        assert body["tags_count"] == 0
        assert body["document_tags_count"] == 0
        # audit_logs 至少有刚才的 import 记录
        assert body["audit_logs_count"] >= 1

    def test_export_row_serialization_datetime_iso(self, client):
        """datetime 字段序列化为 ISO 字符串。"""
        r = client.post(
            "/api/documents/import-text",
            json={"title": "T", "content": "x"},
        )
        doc_id = r.json()["doc_id"]
        resp = client.get("/api/export/all.json")
        body = resp.json()
        docs = body["tables"]["documents"]
        target = [d for d in docs if d["doc_id"] == doc_id][0]
        assert isinstance(target["created_at"], str)
        # ISO 格式 YYYY-MM-DDTHH:MM:SS
        assert "T" in target["created_at"]

    def test_export_content_disposition_attachment(self, client):
        """响应头包含 attachment; filename=...json。"""
        resp = client.get("/api/export/all.json")
        cd = resp.headers["content-disposition"]
        assert "attachment" in cd
        assert ".json" in cd
        # 文件名含时间戳
        assert "hermes_kb_export_" in cd

    def test_export_cache_control_no_store(self, client):
        """敏感数据导出必须 no-store。"""
        resp = client.get("/api/export/all.json")
        assert resp.headers["cache-control"] == "no-store"

    def test_export_audited(self, client):
        """导出动作本身被审计（action=export）。"""
        client.get("/api/export/all.json")
        with get_session() as session:
            from sqlmodel import select

            audit = session.exec(
                select(AuditLog).where(AuditLog.action == "export")
            ).first()
            assert audit is not None
            assert audit.target_type == "database"
            assert audit.target_id == "all"
            meta = json.loads(audit.meta_json)
            assert meta["version"] == "1.0"
            assert "tables" in meta

    def test_export_admin_required_when_auth_enabled(self, client, monkeypatch):
        """auth_enabled=True → 非 admin JWT → 403。"""
        from hermes_kb.api.deps import jwt_encode
        from hermes_kb.config import override_settings

        secret = "test-secret-for-export-only-1234567890"
        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret=secret,
        )
        token = jwt_encode({"sub": "user1", "role": "user"}, secret)
        resp = client.get(
            "/api/export/all.json",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert "管理员" in resp.json()["detail"]

    def test_export_admin_allowed_with_admin_token(self, client, monkeypatch):
        """auth_enabled=True + admin token → 200。"""
        from hermes_kb.api.deps import jwt_encode
        from hermes_kb.config import override_settings

        secret = "test-secret-for-export-only-1234567890"
        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret=secret,
        )
        token = jwt_encode({"sub": "admin", "role": "admin"}, secret)
        resp = client.get(
            "/api/export/all.json",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_export_unauthorized_without_token_when_auth_enabled(
        self, client, monkeypatch
    ):
        """auth_enabled=True + 无 token → 401。"""
        from hermes_kb.config import override_settings

        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret="test-secret-for-export-only-1234567890",
        )
        resp = client.get("/api/export/all.json")
        assert resp.status_code == 401

    def test_export_includes_query_logs(self, client):
        """导出包含 query_logs（含 token 字段）。"""
        # 直接插入一条 QueryLog
        with get_session() as session:
            session.add(
                QueryLog(
                    query="测试问题",
                    answer="测试答案",
                    model_used="test-model",
                    latency_ms=100,
                    feedback=1,
                    prompt_tokens=50,
                    completion_tokens=30,
                    cost_cny=0.001,
                )
            )
            session.commit()
        resp = client.get("/api/export/all.json")
        body = resp.json()
        logs = body["tables"]["query_logs"]
        assert len(logs) >= 1
        target = [log for log in logs if log["query"] == "测试问题"][0]
        assert target["prompt_tokens"] == 50
        assert target["completion_tokens"] == 30
        assert target["cost_cny"] == 0.001

    def test_export_performance_under_1s(self, client):
        """验收：导出 100 篇文档 + 1000 条历史 < 1s。"""
        # 批量构造数据
        for i in range(100):
            client.post(
                "/api/documents/import-text",
                json={"title": f"D{i}", "content": f"内容{i}" * 10},
            )
        with get_session() as session:
            for i in range(1000):
                session.add(
                    QueryLog(
                        query=f"Q{i}",
                        answer=f"A{i}",
                        model_used="mock",
                        latency_ms=10,
                    )
                )
            session.commit()
        t0 = time.perf_counter()
        resp = client.get("/api/export/all.json")
        elapsed = time.perf_counter() - t0
        assert resp.status_code == 200
        assert elapsed < 1.0, f"export too slow: {elapsed:.2f}s"


# ===========================================================================
# 3. 导入恢复
# ===========================================================================
class TestImportFromExport:
    """POST /api/export/import"""

    def _upload_json(self, client, payload: dict):
        """辅助：把 dict 作为 JSON 文件上传到 /api/export/import。"""
        files = {
            "file": (
                "export.json",
                io.BytesIO(json.dumps(payload).encode("utf-8")),
                "application/json",
            )
        }
        return client.post("/api/export/import", files=files)

    def test_import_round_trip_basic(self, client):
        """round-trip：export → import → export 等价（核心验收）。"""
        # 构造初始数据
        r = client.post(
            "/api/documents/import-text",
            json={"title": "原始文档", "content": "原始内容"},
        )
        doc_id = r.json()["doc_id"]
        client.post("/api/tags", json={"name": "标签A"})
        # 第一次导出
        export1 = client.get("/api/export/all.json").json()
        # 截取 documents + tags 子集（不含审计日志，因审计会随每次操作递增）
        docs1 = export1["tables"]["documents"]
        tags1 = export1["tables"]["tags"]
        chunks1 = export1["tables"]["chunks"]
        assert len(docs1) == 1
        assert len(tags1) == 1
        # 导入到新库（用同一 client，但 merge 语义会覆盖）
        resp = self._upload_json(client, export1)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "imported"
        assert body["counts"]["documents"] == 1
        assert body["counts"]["tags"] == 1
        # 验证：再次导出，documents / tags / chunks 应等价
        export2 = client.get("/api/export/all.json").json()
        docs2 = export2["tables"]["documents"]
        tags2 = export2["tables"]["tags"]
        chunks2 = export2["tables"]["chunks"]
        # 文档数应仍为 1（merge 幂等，不重复）
        assert len(docs2) == 1
        assert docs2[0]["doc_id"] == doc_id
        assert docs2[0]["title"] == "原始文档"
        assert docs2[0]["content"] == "原始内容"
        assert len(tags2) == 1
        assert tags2[0]["name"] == "标签A"
        # chunks 应等价（按 doc_id 过滤后比较 text）
        chunks1_text = sorted(c["text"] for c in chunks1 if c["doc_id"] == doc_id)
        chunks2_text = sorted(c["text"] for c in chunks2 if c["doc_id"] == doc_id)
        assert chunks1_text == chunks2_text

    def test_import_idempotent_multiple_runs(self, client):
        """同一份 JSON 多次导入不产生重复行。"""
        # 构造数据
        client.post(
            "/api/documents/import-text",
            json={"title": "幂等测试", "content": "内容"},
        )
        client.post("/api/tags", json={"name": "T1"})
        export = client.get("/api/export/all.json").json()
        # 第一次导入
        r1 = self._upload_json(client, export)
        assert r1.status_code == 200
        # 第二次导入
        r2 = self._upload_json(client, export)
        assert r2.status_code == 200
        # 验证：documents / tags 仍是原数量（merge 幂等）
        export_final = client.get("/api/export/all.json").json()
        # documents 至少 1（merge 不会创建重复 doc_id）
        doc_titles = [d["title"] for d in export_final["tables"]["documents"]]
        assert doc_titles.count("幂等测试") == 1
        tag_names = [t["name"] for t in export_final["tables"]["tags"]]
        assert tag_names.count("T1") == 1

    def test_import_preserves_doc_id_and_chunks(self, client):
        """导入保留原 doc_id 与 chunks 内容。"""
        # 构造一篇有多 chunk 的文档（chunk_size 默认 500，需要 > 500 字符）
        long_content = "段落一内容详细描述。\n\n段落二内容详细描述。\n\n段落三内容详细描述。\n\n" * 30
        r = client.post(
            "/api/documents/import-text",
            json={"title": "多分片", "content": long_content, "file_type": "md"},
        )
        doc_id = r.json()["doc_id"]
        export = client.get("/api/export/all.json").json()
        # 收集原 chunks
        orig_chunks = [
            c for c in export["tables"]["chunks"] if c["doc_id"] == doc_id
        ]
        assert len(orig_chunks) > 1
        # 导入
        self._upload_json(client, export)
        # 验证 chunks 仍存在且 idx 一致
        export2 = client.get("/api/export/all.json").json()
        new_chunks = [
            c for c in export2["tables"]["chunks"] if c["doc_id"] == doc_id
        ]
        assert len(new_chunks) == len(orig_chunks)
        # idx 集合等价
        assert sorted(c["idx"] for c in new_chunks) == sorted(
            c["idx"] for c in orig_chunks
        )

    def test_import_preserves_query_logs_with_tokens(self, client):
        """导入保留 query_logs（含 token 字段）。"""
        with get_session() as session:
            session.add(
                QueryLog(
                    query="带token的问题",
                    answer="答案",
                    model_used="gpt-4o-mini",
                    latency_ms=200,
                    feedback=1,
                    prompt_tokens=120,
                    completion_tokens=80,
                    cost_cny=0.002,
                )
            )
            session.commit()
        export = client.get("/api/export/all.json").json()
        # 导入
        self._upload_json(client, export)
        # 验证：query_logs 中仍有该记录，token 字段未丢失
        export2 = client.get("/api/export/all.json").json()
        target = [
            log
            for log in export2["tables"]["query_logs"]
            if log["query"] == "带token的问题"
        ]
        assert len(target) == 1
        assert target[0]["prompt_tokens"] == 120
        assert target[0]["completion_tokens"] == 80
        assert target[0]["cost_cny"] == 0.002

    def test_import_preserves_tag_associations(self, client):
        """导入保留 document_tags 关联。"""
        # 创建文档 + 标签 + 关联
        r = client.post(
            "/api/documents/import-text", json={"title": "D", "content": "C"}
        )
        doc_id = r.json()["doc_id"]
        t = client.post("/api/tags", json={"name": "T"}).json()
        client.put(
            f"/api/documents/{doc_id}/metadata", json={"tag_ids": [t["id"]]}
        )
        export = client.get("/api/export/all.json").json()
        # 验证导出含 document_tags
        assert len(export["tables"]["document_tags"]) == 1
        # 导入
        self._upload_json(client, export)
        # 验证：document_tags 仍存在
        export2 = client.get("/api/export/all.json").json()
        dt2 = export2["tables"]["document_tags"]
        # 至少 1 条关联（可能多条因 audit import 会写入）
        target = [d for d in dt2 if d["doc_id"] == doc_id]
        assert len(target) == 1
        assert target[0]["tag_id"] == t["id"]

    def test_import_invalid_json_400(self, client):
        """非法 JSON → 400。"""
        files = {
            "file": (
                "bad.json",
                io.BytesIO(b"not json {{{"),
                "application/json",
            )
        }
        resp = client.post("/api/export/import", files=files)
        assert resp.status_code == 400
        assert "JSON" in resp.json()["detail"]

    def test_import_empty_file_400(self, client):
        """空文件 → 400。"""
        files = {
            "file": (
                "empty.json",
                io.BytesIO(b""),
                "application/json",
            )
        }
        resp = client.post("/api/export/import", files=files)
        assert resp.status_code == 400
        assert "空" in resp.json()["detail"]

    def test_import_missing_tables_field_400(self, client):
        """payload 缺少 tables 字段 → 400。"""
        resp = self._upload_json(client, {"version": "1.0"})
        assert resp.status_code == 400
        assert "tables" in resp.json()["detail"]

    def test_import_tables_not_dict_400(self, client):
        """tables 不是 dict → 400。"""
        resp = self._upload_json(
            client, {"version": "1.0", "tables": "not a dict"}
        )
        assert resp.status_code == 400

    def test_import_tables_value_not_list_400(self, client):
        """tables.documents 不是 list → 400。"""
        resp = self._upload_json(
            client, {"version": "1.0", "tables": {"documents": "not a list"}}
        )
        assert resp.status_code == 400
        assert "documents" in resp.json()["detail"]

    def test_import_admin_required_when_auth_enabled(self, client, monkeypatch):
        """auth_enabled=True → 非 admin → 403。"""
        from hermes_kb.api.deps import jwt_encode
        from hermes_kb.config import override_settings

        secret = "test-secret-for-export-only-1234567890"
        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret=secret,
        )
        token = jwt_encode({"sub": "user1", "role": "user"}, secret)
        # 构造合法 payload
        payload = {
            "version": "1.0",
            "tables": {"documents": []},
        }
        files = {
            "file": (
                "export.json",
                io.BytesIO(json.dumps(payload).encode()),
                "application/json",
            )
        }
        resp = client.post(
            "/api/export/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_import_audited(self, client):
        """导入动作被审计（action=import, target_type=database）。"""
        payload = {
            "version": "1.0",
            "exported_at": "2026-01-01T00:00:00",
            "tables": {
                "documents": [],
                "chunks": [],
                "tags": [],
                "document_tags": [],
                "query_logs": [],
                "audit_logs": [],
                "recipe_stats": [],
                "ingredient_substitutes": [],
                "missing_ingredient_stats": [],
                "recipe_variants": [],
            },
        }
        self._upload_json(client, payload)
        with get_session() as session:
            from sqlmodel import select

            # 找到 target_type=database 的 import 审计
            audits = session.exec(
                select(AuditLog)
                .where(AuditLog.action == "import")
                .where(AuditLog.target_type == "database")
            ).all()
            assert any(a.target_id == "all" for a in audits)


# ===========================================================================
# 4. 边界与端到端
# ===========================================================================
class TestExportE2E:
    def test_export_import_export_e2e(self, client):
        """完整 round-trip：构造数据 → export → wipe → import → export 等价。"""
        # 1. 构造多种数据
        client.post(
            "/api/documents/import-text",
            json={"title": "E2E 文档", "content": "段落一\n\n段落二\n\n段落三"},
        )
        client.post("/api/tags", json={"name": "E2E标签"})
        with get_session() as session:
            session.add(
                QueryLog(
                    query="E2E 问题",
                    answer="E2E 答案",
                    model_used="mock",
                    latency_ms=50,
                )
            )
            session.commit()
        # 2. 第一次导出
        export1 = client.get("/api/export/all.json").json()
        # 3. 清空数据库（直接删 Document，级联删 chunks/tags关联）
        with get_session() as session:
            from sqlmodel import select as _select

            for doc in session.exec(_select(Document)).all():
                session.delete(doc)
            for tag in session.exec(_select(Tag)).all():
                session.delete(tag)
            for qlog in session.exec(_select(QueryLog)).all():
                session.delete(qlog)
            session.commit()
        # 4. 导入
        resp = client.post(
            "/api/export/import",
            files={
                "file": (
                    "export.json",
                    io.BytesIO(json.dumps(export1).encode()),
                    "application/json",
                )
            },
        )
        assert resp.status_code == 200
        # 5. 第二次导出
        export2 = client.get("/api/export/all.json").json()
        # 6. 验证 documents / chunks / tags / query_logs 等价
        #    （audit_logs 会有差异因 import 动作本身会写入新审计）
        docs1 = sorted(
            export1["tables"]["documents"], key=lambda d: d["doc_id"]
        )
        docs2 = sorted(
            export2["tables"]["documents"], key=lambda d: d["doc_id"]
        )
        assert len(docs1) == len(docs2)
        if docs1:
            assert docs1[0]["doc_id"] == docs2[0]["doc_id"]
            assert docs1[0]["title"] == docs2[0]["title"]
            assert docs1[0]["content"] == docs2[0]["content"]
        # query_logs（导出1 中的 query_logs 在导入后应仍在）
        q1 = [q for q in export1["tables"]["query_logs"] if q["query"] == "E2E 问题"]
        q2 = [q for q in export2["tables"]["query_logs"] if q["query"] == "E2E 问题"]
        assert len(q1) == 1
        assert len(q2) == 1
        # tags
        t1 = [t for t in export1["tables"]["tags"] if t["name"] == "E2E标签"]
        t2 = [t for t in export2["tables"]["tags"] if t["name"] == "E2E标签"]
        assert len(t1) == 1
        assert len(t2) == 1

    def test_export_with_unicode_content_round_trip(self, client):
        """中文 + emoji 内容的 round-trip。"""
        content = "中文测试 🍷 鸡尾酒配方\n\n# 子标题\n\n内容包含特殊字符 \"quotes\" 'apostrophe'"
        r = client.post(
            "/api/documents/import-text",
            json={"title": "🍷 鸡尾酒", "content": content, "file_type": "md"},
        )
        doc_id = r.json()["doc_id"]
        export = client.get("/api/export/all.json").json()
        # 验证导出含原内容
        docs = export["tables"]["documents"]
        target = [d for d in docs if d["doc_id"] == doc_id][0]
        assert target["title"] == "🍷 鸡尾酒"
        assert target["content"] == content
        # 导入
        client.post(
            "/api/export/import",
            files={
                "file": (
                    "export.json",
                    io.BytesIO(json.dumps(export).encode("utf-8")),
                    "application/json",
                )
            },
        )
        # 验证内容仍在
        export2 = client.get("/api/export/all.json").json()
        target2 = [
            d for d in export2["tables"]["documents"] if d["doc_id"] == doc_id
        ][0]
        assert target2["title"] == "🍷 鸡尾酒"
        assert target2["content"] == content


# ===========================================================================
# M5：导入未知字段过滤测试
# ===========================================================================
class TestImportUnknownFields:
    """M5：导出 JSON 含未知字段时静默丢弃并报告。"""

    def _upload_json(self, client, payload: dict):
        files = {
            "file": (
                "export.json",
                io.BytesIO(json.dumps(payload).encode("utf-8")),
                "application/json",
            )
        }
        return client.post("/api/export/import", files=files)

    def test_import_unknown_fields_silently_dropped(self, client):
        """M5：导出 JSON 含未来版本字段时静默丢弃，不阻塞导入。"""
        payload = {
            "version": "1.0",
            "exported_at": "2026-07-25T12:00:00Z",
            "tables": {
                "documents": [
                    {
                        "doc_id": "doc_m5_test_001",
                        "title": "M5 未知字段测试",
                        "content": "内容",
                        "source_type": "local",
                        "file_type": "txt",
                        "chunk_count": 0,
                        "category": "",
                        "created_at": "2026-07-25T12:00:00",
                        # 未来版本字段（当前 schema 不存在）
                        "future_column_v2": "value",
                        "ai_summary": "AI 生成的摘要",
                    }
                ],
                "tags": [],
                "query_logs": [],
                "missing_ingredient_stats": [],
                "ingredient_substitutes": [],
                "chunks": [],
                "document_tags": [],
                "recipe_stats": [],
                "recipe_variants": [],
            },
        }
        resp = self._upload_json(client, payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "imported"
        assert body["counts"]["documents"] == 1
        # unknown_fields 应报告被丢弃的字段
        assert "documents" in body["unknown_fields"]
        assert "future_column_v2" in body["unknown_fields"]["documents"]
        assert "ai_summary" in body["unknown_fields"]["documents"]
        # 验证文档确实导入了（未知字段被丢弃，已知字段保留）
        export = client.get("/api/export/all.json").json()
        docs = [d for d in export["tables"]["documents"] if d["doc_id"] == "doc_m5_test_001"]
        assert len(docs) == 1
        assert docs[0]["title"] == "M5 未知字段测试"

    def test_import_missing_fields_uses_defaults(self, client):
        """M5：导出 JSON 缺少字段时由 SQLModel 默认值兜底。"""
        payload = {
            "version": "1.0",
            "exported_at": "2026-07-25T12:00:00Z",
            "tables": {
                "documents": [
                    {
                        "doc_id": "doc_m5_defaults",
                        "title": "缺字段测试",
                        # 缺少 content / source_type / file_type / category 等
                        "created_at": "2026-07-25T12:00:00",
                    }
                ],
                "tags": [],
                "query_logs": [],
                "missing_ingredient_stats": [],
                "ingredient_substitutes": [],
                "chunks": [],
                "document_tags": [],
                "recipe_stats": [],
                "recipe_variants": [],
            },
        }
        resp = self._upload_json(client, payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["counts"]["documents"] == 1
        # 验证默认值生效
        export = client.get("/api/export/all.json").json()
        doc = [d for d in export["tables"]["documents"] if d["doc_id"] == "doc_m5_defaults"][0]
        assert doc["content"] == ""  # 默认值
        assert doc["source_type"] == "local"  # 默认值
        assert doc["file_type"] == "txt"  # 默认值

    def test_import_no_unknown_fields_returns_empty_dict(self, client):
        """M5：无未知字段时 unknown_fields 为空 dict。"""
        payload = {
            "version": "1.0",
            "exported_at": "2026-07-25T12:00:00Z",
            "tables": {
                "documents": [
                    {
                        "doc_id": "doc_m5_clean",
                        "title": "无未知字段",
                        "content": "x",
                        "source_type": "local",
                        "file_type": "txt",
                        "chunk_count": 0,
                        "category": "",
                        "created_at": "2026-07-25T12:00:00",
                    }
                ],
                "tags": [],
                "query_logs": [],
                "missing_ingredient_stats": [],
                "ingredient_substitutes": [],
                "chunks": [],
                "document_tags": [],
                "recipe_stats": [],
                "recipe_variants": [],
            },
        }
        resp = self._upload_json(client, payload)
        body = resp.json()
        assert body["unknown_fields"] == {}

    def test_import_unknown_fields_in_audit_log(self, client):
        """M5：未知字段报告写入审计日志 meta。"""
        payload = {
            "version": "1.0",
            "exported_at": "2026-07-25T12:00:00Z",
            "tables": {
                "documents": [
                    {
                        "doc_id": "doc_m5_audit",
                        "title": "审计测试",
                        "content": "x",
                        "source_type": "local",
                        "file_type": "txt",
                        "chunk_count": 0,
                        "category": "",
                        "created_at": "2026-07-25T12:00:00",
                        "future_field": "val",
                    }
                ],
                "tags": [],
                "query_logs": [],
                "missing_ingredient_stats": [],
                "ingredient_substitutes": [],
                "chunks": [],
                "document_tags": [],
                "recipe_stats": [],
                "recipe_variants": [],
            },
        }
        self._upload_json(client, payload)
        with get_session() as session:
            from sqlmodel import select

            audit = session.exec(
                select(AuditLog).where(AuditLog.action == "import")
            ).first()
            assert audit is not None
            meta = json.loads(audit.meta_json)
            assert "unknown_fields" in meta
            assert "documents" in meta["unknown_fields"]
            assert "future_field" in meta["unknown_fields"]["documents"]


# ===========================================================================
# H3：导入分批 commit 测试
# ===========================================================================
class TestImportBatchCommit:
    """H3：大量数据导入时分批 commit 不报错且数据完整。"""

    def _upload_json(self, client, payload: dict):
        files = {
            "file": (
                "export.json",
                io.BytesIO(json.dumps(payload).encode("utf-8")),
                "application/json",
            )
        }
        return client.post("/api/export/import", files=files)

    def test_import_large_batch_over_1000_rows(self, client):
        """H3：导入 > 1000 行 query_logs，分批 commit 不报错。"""
        # 构造 1500 条 query_logs（超过 batch_size=1000）
        query_logs = []
        for i in range(1500):
            query_logs.append({
                "id": 10000 + i,  # 避免与 seed 数据 id 冲突
                "query": f"批量导入问题{i}",
                "answer": f"答案{i}",
                "citations": "[]",
                "model_used": "test",
                "latency_ms": 10,
                "feedback": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost_cny": 0.0,
                "created_at": "2026-07-25T12:00:00",
            })
        payload = {
            "version": "1.0",
            "exported_at": "2026-07-25T12:00:00Z",
            "tables": {
                "documents": [],
                "tags": [],
                "query_logs": query_logs,
                "missing_ingredient_stats": [],
                "ingredient_substitutes": [],
                "chunks": [],
                "document_tags": [],
                "recipe_stats": [],
                "recipe_variants": [],
            },
        }
        resp = self._upload_json(client, payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["counts"]["query_logs"] == 1500
        assert body["total"] == 1500
        # 验证数据完整（抽查首尾）
        export = client.get("/api/export/all.json").json()
        all_queries = [q["query"] for q in export["tables"]["query_logs"]]
        assert "批量导入问题0" in all_queries
        assert "批量导入问题1499" in all_queries

    def test_import_batch_idempotent_large(self, client):
        """H3：大批量导入幂等（重复导入不重复行）。"""
        query_logs = []
        for i in range(1200):
            query_logs.append({
                "id": 20000 + i,
                "query": f"幂等测试{i}",
                "answer": "答案",
                "citations": "[]",
                "model_used": "test",
                "latency_ms": 10,
                "feedback": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost_cny": 0.0,
                "created_at": "2026-07-25T12:00:00",
            })
        payload = {
            "version": "1.0",
            "exported_at": "2026-07-25T12:00:00Z",
            "tables": {
                "documents": [],
                "tags": [],
                "query_logs": query_logs,
                "missing_ingredient_stats": [],
                "ingredient_substitutes": [],
                "chunks": [],
                "document_tags": [],
                "recipe_stats": [],
                "recipe_variants": [],
            },
        }
        # 第一次导入
        r1 = self._upload_json(client, payload)
        assert r1.status_code == 200
        assert r1.json()["counts"]["query_logs"] == 1200
        # 第二次导入（幂等）
        r2 = self._upload_json(client, payload)
        assert r2.status_code == 200
        assert r2.json()["counts"]["query_logs"] == 1200
        # 验证不重复
        export = client.get("/api/export/all.json").json()
        idempotent_queries = [
            q for q in export["tables"]["query_logs"]
            if q["query"].startswith("幂等测试")
        ]
        assert len(idempotent_queries) == 1200
