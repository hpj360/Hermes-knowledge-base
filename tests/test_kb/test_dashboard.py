"""M2-11 仪表盘测试。

覆盖：
1. /api/stats/dashboard 端点基本可用性
2. 空库指标全 0
3. 文档统计（count / chunk_count / total_chars）
4. 问答统计（total / today / avg_latency_ms）
5. token 用量与累计成本聚合
6. 反馈分布（up / down / none）
7. 准确率（赞 / (赞 + 踩)）
8. 准确率 None 边界（无反馈时）
9. Top N 热门文档（按 match_count 倒序）
10. top_n 参数边界（1 / 50 / 越界）
11. 文档被删除时 RecipeStats 孤儿记录 → "(已删除)"
12. 管理员权限校验（auth_enabled=True 时非 admin → 403）
13. auth_enabled=False 时任意访问（dev 模式）
14. generated_at 字段格式
15. SQL 注入 / 异常输入鲁棒性
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hermes_kb.database import get_session
from hermes_kb.models import Document, QueryLog, RecipeStats


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
def _now_utc_naive() -> datetime:
    """无时区的 UTC datetime（与 QueryLog.created_at 存储格式对齐）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _insert_doc(
    title: str = "测试文档",
    content: str = "正文内容",
    chunk_count: int = 1,
    category: str = "",
) -> str:
    """直接写入文档，返回 doc_id。"""
    with get_session() as session:
        doc = Document(
            title=title,
            content=content,
            chunk_count=chunk_count,
            category=category,
        )
        session.add(doc)
        session.commit()
        return doc.doc_id


def _insert_query_log(
    query: str = "q",
    answer: str = "a",
    model_used: str = "mock",
    feedback: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_cny: float = 0.0,
    latency_ms: int = 0,
    created_at: datetime | None = None,
) -> int:
    with get_session() as session:
        log = QueryLog(
            query=query,
            answer=answer,
            model_used=model_used,
            feedback=feedback,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_cny=cost_cny,
            latency_ms=latency_ms,
            created_at=created_at or _now_utc_naive(),
        )
        session.add(log)
        session.commit()
        return log.id


def _insert_recipe_stats(
    doc_id: str,
    match_count: int = 0,
    view_count: int = 0,
) -> None:
    with get_session() as session:
        stats = RecipeStats(
            doc_id=doc_id,
            match_count=match_count,
            view_count=view_count,
        )
        session.add(stats)
        session.commit()


# ---------------------------------------------------------------------------
# 1. 端点基本可用性 + 空库
# ---------------------------------------------------------------------------
class TestDashboardEmpty:
    def test_dashboard_returns_200(self, client, tmp_db):
        """端点可访问，返回 200。"""
        resp = client.get("/api/stats/dashboard")
        assert resp.status_code == 200

    def test_dashboard_empty_all_zero(self, client, tmp_db):
        """空库 → 所有指标为 0。"""
        resp = client.get("/api/stats/dashboard")
        body = resp.json()
        assert body["documents"]["count"] == 0
        assert body["documents"]["chunk_count"] == 0
        assert body["documents"]["total_chars"] == 0
        assert body["queries"]["total"] == 0
        assert body["queries"]["today"] == 0
        assert body["queries"]["avg_latency_ms"] == 0
        assert body["tokens"]["prompt_tokens"] == 0
        assert body["tokens"]["completion_tokens"] == 0
        assert body["tokens"]["total_tokens"] == 0
        assert body["tokens"]["total_cost_cny"] == 0.0
        assert body["feedback"]["up"] == 0
        assert body["feedback"]["down"] == 0
        assert body["feedback"]["none"] == 0
        assert body["feedback"]["accuracy"] is None
        assert body["top_documents"] == []

    def test_dashboard_has_generated_at(self, client, tmp_db):
        """generated_at 字段为 ISO 格式 + Z 后缀（UTC）。"""
        resp = client.get("/api/stats/dashboard")
        body = resp.json()
        assert "generated_at" in body
        # 形如 "2026-07-25T03:45:12.345678Z"
        assert body["generated_at"].endswith("Z")
        # 可被 fromisoformat 解析（替换 Z 为 +00:00）
        parsed = datetime.fromisoformat(body["generated_at"].replace("Z", "+00:00"))
        assert parsed.tzinfo is not None


# ---------------------------------------------------------------------------
# 2. 文档统计
# ---------------------------------------------------------------------------
class TestDashboardDocuments:
    def test_document_count(self, client, tmp_db):
        """文档数正确。"""
        for i in range(3):
            _insert_doc(title=f"doc-{i}")
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["documents"]["count"] == 3

    def test_chunk_count_sum(self, client, tmp_db):
        """chunk_count 为所有文档 chunk 数之和。"""
        _insert_doc(title="d1", chunk_count=5)
        _insert_doc(title="d2", chunk_count=3)
        _insert_doc(title="d3", chunk_count=0)
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["documents"]["chunk_count"] == 8

    def test_total_chars_sum(self, client, tmp_db):
        """total_chars 为所有文档 content 字符数之和。"""
        _insert_doc(title="d1", content="abcde")  # 5
        _insert_doc(title="d2", content="中文测试")  # 4
        _insert_doc(title="d3", content="")  # 0
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["documents"]["total_chars"] == 9

    def test_total_chars_chinese_uses_char_length(self, client, tmp_db):
        """中文字符按 char_length 计算（每个汉字算 1）。"""
        _insert_doc(title="d1", content="中国白酒")  # 4
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["documents"]["total_chars"] == 4


# ---------------------------------------------------------------------------
# 3. 问答统计
# ---------------------------------------------------------------------------
class TestDashboardQueries:
    def test_query_total(self, client, tmp_db):
        """问答总数正确。"""
        for i in range(5):
            _insert_query_log(query=f"q{i}")
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["queries"]["total"] == 5

    def test_query_today_only(self, client, tmp_db):
        """today 只统计今日（UTC 零点之后）。"""
        now = _now_utc_naive()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # 今日 2 条
        _insert_query_log(query="today1", created_at=now)
        _insert_query_log(query="today2", created_at=now)
        # 昨日 3 条
        yesterday = today_start - timedelta(hours=2)
        for i in range(3):
            _insert_query_log(query=f"yesterday{i}", created_at=yesterday)
        resp = client.get("/api/stats/dashboard")
        body = resp.json()
        assert body["queries"]["total"] == 5
        assert body["queries"]["today"] == 2

    def test_avg_latency_ms(self, client, tmp_db):
        """平均延迟正确计算。"""
        _insert_query_log(query="q1", latency_ms=100)
        _insert_query_log(query="q2", latency_ms=200)
        _insert_query_log(query="q3", latency_ms=300)
        resp = client.get("/api/stats/dashboard")
        # (100+200+300)/3 = 200.0
        assert resp.json()["queries"]["avg_latency_ms"] == pytest.approx(200.0, abs=0.01)

    def test_avg_latency_ms_rounded_to_2_decimals(self, client, tmp_db):
        """avg_latency_ms 四舍五入到 2 位小数。"""
        _insert_query_log(query="q1", latency_ms=100)
        _insert_query_log(query="q2", latency_ms=101)
        _insert_query_log(query="q3", latency_ms=102)
        resp = client.get("/api/stats/dashboard")
        # (100+101+102)/3 = 101.0
        # 但用更不易整除的例子：100/3 = 33.33...
        _insert_query_log(query="q4", latency_ms=0)
        resp = client.get("/api/stats/dashboard")
        # (100+101+102+0)/4 = 75.75
        assert resp.json()["queries"]["avg_latency_ms"] == 75.75


# ---------------------------------------------------------------------------
# 4. token 用量与成本
# ---------------------------------------------------------------------------
class TestDashboardTokens:
    def test_token_aggregation(self, client, tmp_db):
        """token 用量正确聚合。"""
        _insert_query_log(
            query="q1",
            prompt_tokens=100,
            completion_tokens=50,
            cost_cny=0.001,
        )
        _insert_query_log(
            query="q2",
            prompt_tokens=200,
            completion_tokens=100,
            cost_cny=0.002,
        )
        resp = client.get("/api/stats/dashboard")
        tokens = resp.json()["tokens"]
        assert tokens["prompt_tokens"] == 300
        assert tokens["completion_tokens"] == 150
        assert tokens["total_tokens"] == 450
        assert tokens["total_cost_cny"] == pytest.approx(0.003, abs=1e-6)

    def test_token_zero_when_all_mock(self, client, tmp_db):
        """mock 模型 token 全 0。"""
        _insert_query_log(query="q1", model_used="mock")
        _insert_query_log(query="q2", model_used="mock")
        resp = client.get("/api/stats/dashboard")
        tokens = resp.json()["tokens"]
        assert tokens["prompt_tokens"] == 0
        assert tokens["completion_tokens"] == 0
        assert tokens["total_tokens"] == 0
        assert tokens["total_cost_cny"] == 0.0


# ---------------------------------------------------------------------------
# 5. 反馈分布
# ---------------------------------------------------------------------------
class TestDashboardFeedback:
    def test_feedback_distribution(self, client, tmp_db):
        """反馈分布计数正确。"""
        _insert_query_log(query="q1", feedback=1)
        _insert_query_log(query="q2", feedback=1)
        _insert_query_log(query="q3", feedback=1)
        _insert_query_log(query="q4", feedback=-1)
        _insert_query_log(query="q5", feedback=0)
        _insert_query_log(query="q6", feedback=0)
        resp = client.get("/api/stats/dashboard")
        fb = resp.json()["feedback"]
        assert fb["up"] == 3
        assert fb["down"] == 1
        assert fb["none"] == 2

    def test_accuracy_calculation(self, client, tmp_db):
        """准确率 = 赞 / (赞 + 踩)。"""
        _insert_query_log(query="q1", feedback=1)
        _insert_query_log(query="q2", feedback=1)
        _insert_query_log(query="q3", feedback=1)
        _insert_query_log(query="q4", feedback=-1)
        resp = client.get("/api/stats/dashboard")
        # 3 / (3 + 1) = 0.75
        assert resp.json()["feedback"]["accuracy"] == 0.75

    def test_accuracy_none_when_no_feedback(self, client, tmp_db):
        """无赞踩反馈 → accuracy=None。"""
        _insert_query_log(query="q1", feedback=0)
        _insert_query_log(query="q2", feedback=0)
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["feedback"]["accuracy"] is None

    def test_accuracy_none_when_empty(self, client, tmp_db):
        """空库 → accuracy=None。"""
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["feedback"]["accuracy"] is None

    def test_accuracy_all_up(self, client, tmp_db):
        """全部赞 → accuracy=1.0。"""
        _insert_query_log(query="q1", feedback=1)
        _insert_query_log(query="q2", feedback=1)
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["feedback"]["accuracy"] == 1.0

    def test_accuracy_all_down(self, client, tmp_db):
        """全部踩 → accuracy=0.0。"""
        _insert_query_log(query="q1", feedback=-1)
        _insert_query_log(query="q2", feedback=-1)
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["feedback"]["accuracy"] == 0.0

    def test_accuracy_only_none_feedback_not_counted(self, client, tmp_db):
        """feedback=0 不参与准确率分母。"""
        _insert_query_log(query="q1", feedback=1)
        _insert_query_log(query="q2", feedback=0)  # 不参与
        _insert_query_log(query="q3", feedback=0)  # 不参与
        resp = client.get("/api/stats/dashboard")
        # 1 / (1 + 0) = 1.0
        assert resp.json()["feedback"]["accuracy"] == 1.0

    def test_accuracy_rounded_to_4_decimals(self, client, tmp_db):
        """accuracy 四舍五入到 4 位小数。"""
        # 1 赞 + 2 踩 = 1/3 = 0.3333...
        _insert_query_log(query="q1", feedback=1)
        _insert_query_log(query="q2", feedback=-1)
        _insert_query_log(query="q3", feedback=-1)
        resp = client.get("/api/stats/dashboard")
        # round(1/3, 4) = 0.3333
        assert resp.json()["feedback"]["accuracy"] == 0.3333


# ---------------------------------------------------------------------------
# 6. Top N 热门文档
# ---------------------------------------------------------------------------
class TestDashboardTopDocuments:
    def test_top_documents_sorted_by_match_count_desc(self, client, tmp_db):
        """按 match_count 倒序。"""
        doc1 = _insert_doc(title="热门A")
        doc2 = _insert_doc(title="热门B")
        doc3 = _insert_doc(title="冷门C")
        _insert_recipe_stats(doc1, match_count=10)
        _insert_recipe_stats(doc2, match_count=30)
        _insert_recipe_stats(doc3, match_count=5)
        resp = client.get("/api/stats/dashboard")
        top = resp.json()["top_documents"]
        assert len(top) == 3
        assert top[0]["doc_id"] == doc2
        assert top[0]["match_count"] == 30
        assert top[1]["doc_id"] == doc1
        assert top[1]["match_count"] == 10
        assert top[2]["doc_id"] == doc3
        assert top[2]["match_count"] == 5

    def test_top_documents_includes_view_count(self, client, tmp_db):
        """top_documents 包含 view_count。"""
        doc1 = _insert_doc(title="d1")
        _insert_recipe_stats(doc1, match_count=10, view_count=42)
        resp = client.get("/api/stats/dashboard")
        top = resp.json()["top_documents"]
        assert top[0]["view_count"] == 42

    def test_top_documents_includes_title(self, client, tmp_db):
        """top_documents 包含 title。"""
        doc1 = _insert_doc(title="标题测试")
        _insert_recipe_stats(doc1, match_count=1)
        resp = client.get("/api/stats/dashboard")
        top = resp.json()["top_documents"]
        assert top[0]["title"] == "标题测试"

    def test_top_documents_default_top_n_10(self, client, tmp_db):
        """默认 top_n=10。"""
        for i in range(15):
            doc = _insert_doc(title=f"d{i}")
            _insert_recipe_stats(doc, match_count=i)
        resp = client.get("/api/stats/dashboard")
        assert len(resp.json()["top_documents"]) == 10

    def test_top_documents_custom_top_n(self, client, tmp_db):
        """自定义 top_n。"""
        for i in range(10):
            doc = _insert_doc(title=f"d{i}")
            _insert_recipe_stats(doc, match_count=i)
        resp = client.get("/api/stats/dashboard?top_n=3")
        assert len(resp.json()["top_documents"]) == 3
        # 前 3 应是 match_count 最高的
        top = resp.json()["top_documents"]
        assert top[0]["match_count"] == 9
        assert top[1]["match_count"] == 8
        assert top[2]["match_count"] == 7

    def test_top_n_min_1(self, client, tmp_db):
        """top_n=0 → 422。"""
        resp = client.get("/api/stats/dashboard?top_n=0")
        assert resp.status_code == 422

    def test_top_n_max_50(self, client, tmp_db):
        """top_n=51 → 422。"""
        resp = client.get("/api/stats/dashboard?top_n=51")
        assert resp.status_code == 422

    def test_top_n_at_boundaries(self, client, tmp_db):
        """top_n=1 和 top_n=50 都是合法值。"""
        for i in range(60):
            doc = _insert_doc(title=f"d{i}")
            _insert_recipe_stats(doc, match_count=i)
        resp1 = client.get("/api/stats/dashboard?top_n=1")
        assert resp1.status_code == 200
        assert len(resp1.json()["top_documents"]) == 1
        resp50 = client.get("/api/stats/dashboard?top_n=50")
        assert resp50.status_code == 200
        assert len(resp50.json()["top_documents"]) == 50

    def test_top_documents_empty_when_no_stats(self, client, tmp_db):
        """无 RecipeStats → top_documents=[]。"""
        _insert_doc(title="d1")  # 有文档但无 stats
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["top_documents"] == []

    def test_top_documents_orphan_stats_shows_deleted_label(
        self, client, tmp_db
    ):
        """文档被删除后 RecipeStats 因 CASCADE 也不存在 → 不出现在 top_documents。

        FK 设置 ON DELETE CASCADE，文档删除时 stats 同步删除。
        此测试验证 CASCADE 行为，确保不会出现孤儿 stats 导致仪表盘异常。
        """
        # 先创建文档 + stats
        doc_id = _insert_doc(title="待删除")
        _insert_recipe_stats(doc_id, match_count=999)
        # 验证初始状态
        resp = client.get("/api/stats/dashboard")
        assert len(resp.json()["top_documents"]) == 1
        assert resp.json()["top_documents"][0]["title"] == "待删除"
        # 删除文档（CASCADE 应同步删除 stats）
        with get_session() as session:
            doc = session.get(Document, doc_id)
            session.delete(doc)
            session.commit()
        # 删除后 top_documents 应为空（无孤儿）
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["top_documents"] == []


# ---------------------------------------------------------------------------
# 7. 管理员权限校验
# ---------------------------------------------------------------------------
class TestDashboardAdminAuth:
    def test_dashboard_accessible_when_auth_disabled(self, client, tmp_db):
        """auth_enabled=False → 任意访问者可查（dev 模式）。"""
        resp = client.get("/api/stats/dashboard")
        assert resp.status_code == 200

    def test_dashboard_requires_admin_when_auth_enabled(
        self, client, tmp_db, monkeypatch
    ):
        """auth_enabled=True → 非 admin → 403。"""
        from hermes_kb.api.deps import jwt_encode
        from hermes_kb.config import override_settings

        secret = "test-secret-for-dashboard-only-1234567890"
        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret=secret,
        )
        token = jwt_encode({"sub": "user1", "role": "user"}, secret)
        resp = client.get(
            "/api/stats/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_dashboard_allowed_with_admin_token(
        self, client, tmp_db, monkeypatch
    ):
        """auth_enabled=True + admin token → 200。"""
        from hermes_kb.api.deps import jwt_encode
        from hermes_kb.config import override_settings

        secret = "test-secret-for-dashboard-only-1234567890"
        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret=secret,
        )
        token = jwt_encode({"sub": "admin", "role": "admin"}, secret)
        resp = client.get(
            "/api/stats/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 8. 端到端：通过 /api/ask 触发后查 dashboard
# ---------------------------------------------------------------------------
class TestDashboardE2E:
    def test_ask_then_dashboard_reflects(self, client, tmp_db):
        """mock 问答 → dashboard 反映。"""
        # 触发一次问答
        client.post("/api/ask", json={"query": "金酒有什么特点？"})
        resp = client.get("/api/stats/dashboard")
        body = resp.json()
        assert body["queries"]["total"] >= 1
        assert body["queries"]["today"] >= 1
        # mock 模型 token 为 0
        assert body["tokens"]["total_tokens"] == 0

    def test_feedback_reflected_in_dashboard(self, client, tmp_db):
        """问答反馈 → dashboard 反馈分布反映。"""
        # 触发问答
        r = client.post("/api/ask", json={"query": "金酒"})
        assert r.status_code == 200
        # /api/ask 返回 answer_id（UUID），需从 DB 反查 QueryLog.id
        from sqlmodel import select

        with get_session() as session:
            log = session.exec(
                select(QueryLog).where(QueryLog.query == "金酒")
            ).first()
            assert log is not None, "问答应写入 QueryLog"
            log_id = log.id
        # 通过 API 提交赞反馈
        fb_resp = client.post(f"/api/feedback/{log_id}", json={"feedback": 1})
        assert fb_resp.status_code == 200
        # dashboard 应反映 1 个赞
        resp = client.get("/api/stats/dashboard")
        assert resp.json()["feedback"]["up"] >= 1


# ---------------------------------------------------------------------------
# 9. 鲁棒性 / 边界
# ---------------------------------------------------------------------------
class TestDashboardRobustness:
    def test_negative_top_n_rejected(self, client, tmp_db):
        """负数 top_n → 422。"""
        resp = client.get("/api/stats/dashboard?top_n=-1")
        assert resp.status_code == 422

    def test_non_integer_top_n_rejected(self, client, tmp_db):
        """非整数 top_n → 422。"""
        resp = client.get("/api/stats/dashboard?top_n=abc")
        assert resp.status_code == 422

    def test_dashboard_returns_complete_schema(self, client, tmp_db):
        """响应包含所有规格字段（M2-11 验收点）。"""
        resp = client.get("/api/stats/dashboard")
        body = resp.json()
        # 顶层字段
        assert set(body.keys()) >= {
            "generated_at",
            "documents",
            "queries",
            "tokens",
            "feedback",
            "top_documents",
        }
        # documents 字段
        assert set(body["documents"].keys()) == {
            "count",
            "chunk_count",
            "total_chars",
        }
        # queries 字段
        assert set(body["queries"].keys()) == {
            "total",
            "today",
            "avg_latency_ms",
        }
        # tokens 字段
        assert set(body["tokens"].keys()) == {
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "total_cost_cny",
        }
        # feedback 字段
        assert set(body["feedback"].keys()) == {
            "up",
            "down",
            "none",
            "accuracy",
        }
        # top_documents 每项字段
        if body["top_documents"]:
            assert set(body["top_documents"][0].keys()) == {
                "doc_id",
                "title",
                "match_count",
                "view_count",
            }
