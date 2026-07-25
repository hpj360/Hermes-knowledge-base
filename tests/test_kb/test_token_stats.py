"""M2-10 token 用量统计测试。

覆盖：
1. LLMResponse 含 token 字段
2. OpenAICompatBackend 解析 usage（mock httpx）
3. token_cost.calculate_cost 按模型定价计算
4. token_cost.estimate_tokens 启发式估算
5. QueryLog 模型含 token 字段（默认 0）
6. RAGEngine.answer 写入 token + cost
7. /api/stats/tokens 累计统计端点
8. /api/stats/tokens/recent 最近明细端点
9. 管理员权限校验
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hermes_kb.database import get_session
from hermes_kb.llm import LLMResponse, MockLLMBackend, OpenAICompatBackend
from hermes_kb.models import QueryLog
from hermes_kb.token_cost import (
    calculate_cost,
    estimate_tokens,
    get_model_price,
    register_model_price,
)


# ---------------------------------------------------------------------------
# LLMResponse 含 token 字段
# ---------------------------------------------------------------------------
class TestLLMResponse:
    def test_llm_response_default_tokens_zero(self):
        """LLMResponse 默认 token 数为 0。"""
        resp = LLMResponse(content="hello", model="gpt-4o-mini")
        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0

    def test_llm_response_with_tokens(self):
        """LLMResponse 可携带 token 数。"""
        resp = LLMResponse(
            content="hello",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert resp.prompt_tokens == 100
        assert resp.completion_tokens == 50

    def test_mock_backend_returns_zero_tokens(self):
        """Mock 后端返回 token 数为 0（无真实调用）。"""
        backend = MockLLMBackend()
        resp = backend.chat([{"role": "user", "content": "test"}])
        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0


# ---------------------------------------------------------------------------
# OpenAICompatBackend 解析 usage
# ---------------------------------------------------------------------------
class TestOpenAIBackendUsage:
    def test_chat_parses_usage_from_response(self, tmp_db, monkeypatch):
        """OpenAICompatBackend.chat() 解析 usage 字段。"""
        from hermes_kb.config import override_settings

        override_settings(
            llm_provider="openai",
            llm_api_key="sk-test",
            llm_model="gpt-4o-mini",
            llm_base_url="https://api.openai.com/v1",
        )
        backend = OpenAICompatBackend()

        # Mock httpx.Client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "答案"}}],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 80,
                "total_tokens": 230,
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            resp = backend.chat([{"role": "user", "content": "测试"}])

        assert resp.content == "答案"
        assert resp.model == "gpt-4o-mini"
        assert resp.prompt_tokens == 150
        assert resp.completion_tokens == 80

    def test_chat_handles_missing_usage(self, tmp_db, monkeypatch):
        """响应无 usage 字段时 token 数为 0（不抛异常）。"""
        from hermes_kb.config import override_settings

        override_settings(
            llm_provider="openai",
            llm_api_key="sk-test",
            llm_model="gpt-4o-mini",
            llm_base_url="https://api.openai.com/v1",
        )
        backend = OpenAICompatBackend()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "答案"}}],
            # 无 usage 字段
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            resp = backend.chat([{"role": "user", "content": "测试"}])

        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0

    def test_chat_handles_null_usage_values(self, tmp_db, monkeypatch):
        """usage 字段值为 null 时 token 数为 0。"""
        from hermes_kb.config import override_settings

        override_settings(
            llm_provider="openai",
            llm_api_key="sk-test",
            llm_model="gpt-4o-mini",
            llm_base_url="https://api.openai.com/v1",
        )
        backend = OpenAICompatBackend()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "答案"}}],
            "usage": {
                "prompt_tokens": None,
                "completion_tokens": None,
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            resp = backend.chat([{"role": "user", "content": "测试"}])

        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0


# ---------------------------------------------------------------------------
# token_cost 模块
# ---------------------------------------------------------------------------
class TestTokenCost:
    def test_get_model_price_known(self):
        """已知模型返回定价。"""
        price = get_model_price("gpt-4o-mini")
        assert price is not None
        assert price.input > 0
        assert price.output > 0

    def test_get_model_price_case_insensitive(self):
        """模型名大小写不敏感。"""
        assert get_model_price("GPT-4o-mini") is not None
        assert get_model_price("GLM-4-Flash") is not None

    def test_get_model_price_unknown(self):
        """未知模型返回 None。"""
        assert get_model_price("nonexistent-model-xyz") is None

    def test_get_model_price_empty(self):
        """空字符串返回 None。"""
        assert get_model_price("") is None
        assert get_model_price(None) is None  # type: ignore[arg-type]

    def test_calculate_cost_glm_4_flash(self):
        """glm-4-flash 成本计算（极便宜）。"""
        # 0.0001 元 / 1K tokens
        # 1000 prompt + 500 completion = 0.0001 + 0.00005 = 0.00015
        cost = calculate_cost("glm-4-flash", 1000, 500)
        assert cost == pytest.approx(0.00015, abs=1e-6)

    def test_calculate_cost_gpt_4o_mini(self):
        """gpt-4o-mini 成本计算。"""
        # input 0.00105 / 1K, output 0.0042 / 1K
        # 1000 + 500 = 0.00105 + 0.0021 = 0.00315
        cost = calculate_cost("gpt-4o-mini", 1000, 500)
        assert cost == pytest.approx(0.00315, abs=1e-6)

    def test_calculate_cost_mock_returns_zero(self):
        """mock 模型返回 0 成本。"""
        assert calculate_cost("mock-llm", 1000, 500) == 0.0
        assert calculate_cost("mock", 1000, 500) == 0.0

    def test_calculate_cost_unknown_model_returns_zero(self):
        """未知模型返回 0（不抛异常）。"""
        assert calculate_cost("unknown-model-xyz", 1000, 500) == 0.0

    def test_calculate_cost_zero_tokens(self):
        """0 token 返回 0 成本。"""
        assert calculate_cost("gpt-4o-mini", 0, 0) == 0.0

    def test_calculate_cost_rounded_to_6_decimals(self):
        """成本四舍五入到 6 位小数。"""
        # 0.0001 * 0.001 = 0.0000001 → round 到 0.0
        cost = calculate_cost("glm-4-flash", 1, 0)
        assert cost == 0.0  # 1 token * 0.0001/1000 = 0.0000001 → round(0.0000001, 6) = 0.0

    def test_register_model_price_runtime(self):
        """运行时注册新模型定价。"""
        register_model_price("custom-model", 0.005, 0.015)
        cost = calculate_cost("custom-model", 1000, 1000)
        # 0.005 + 0.015 = 0.02
        assert cost == pytest.approx(0.02, abs=1e-6)

    def test_estimate_tokens_empty(self):
        """空文本返回 0。"""
        assert estimate_tokens("") == 0

    def test_estimate_tokens_non_empty(self):
        """非空文本返回正整数（约 len/2.5）。"""
        # 100 字符 → 约 40 token
        text = "x" * 100
        result = estimate_tokens(text)
        assert result > 0
        assert 30 <= result <= 50  # 容差范围

    def test_estimate_tokens_short_text(self):
        """短文本至少返回 1 token。"""
        assert estimate_tokens("a") == 1
        assert estimate_tokens("ab") == 1


# ---------------------------------------------------------------------------
# QueryLog 模型新字段
# ---------------------------------------------------------------------------
class TestQueryLogTokenFields:
    def test_querylog_default_token_zero(self, tmp_db):
        """QueryLog 默认 token 字段为 0。"""
        with get_session() as session:
            log = QueryLog(query="测试", answer="答案", model_used="mock")
            session.add(log)
            session.commit()
            assert log.id is not None
            assert log.prompt_tokens == 0
            assert log.completion_tokens == 0
            assert log.cost_cny == 0.0

    def test_querylog_with_token_usage(self, tmp_db):
        """QueryLog 可写入 token 用量 + 成本。"""
        with get_session() as session:
            log = QueryLog(
                query="测试",
                answer="答案",
                model_used="gpt-4o-mini",
                prompt_tokens=150,
                completion_tokens=80,
                cost_cny=0.00315,
            )
            session.add(log)
            session.commit()
            loaded = session.get(QueryLog, log.id)
            assert loaded.prompt_tokens == 150
            assert loaded.completion_tokens == 80
            assert loaded.cost_cny == 0.00315


# ---------------------------------------------------------------------------
# RAGEngine 写入 token + cost
# ---------------------------------------------------------------------------
class TestRAGEngineTokenLogging:
    def test_answer_records_zero_tokens_for_mock(self, tmp_db, client):
        """mock 模型问答 → token 数为 0 + 成本为 0。"""
        # 默认 mock provider
        resp = client.post("/api/ask", json={"query": "金酒是什么？"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["prompt_tokens"] == 0
        assert body["completion_tokens"] == 0
        # 验证 QueryLog 也写入
        with get_session() as session:
            from sqlmodel import select

            log = session.exec(
                select(QueryLog).where(QueryLog.query == "金酒是什么？")
            ).first()
            assert log is not None
            assert log.prompt_tokens == 0
            assert log.completion_tokens == 0
            assert log.cost_cny == 0.0


# ---------------------------------------------------------------------------
# /api/stats/tokens 端点
# ---------------------------------------------------------------------------
class TestTokenStatsEndpoint:
    def test_token_stats_empty(self, client, tmp_db):
        """空库 → 全 0 统计。"""
        resp = client.get("/api/stats/tokens")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_prompt_tokens"] == 0
        assert body["total_completion_tokens"] == 0
        assert body["total_tokens"] == 0
        assert body["total_cost_cny"] == 0.0
        assert body["total_queries"] == 0
        assert body["by_model"] == []

    def test_token_stats_with_records(self, client, tmp_db):
        """有记录 → 聚合统计。"""
        # 手动写入若干带 token 的 QueryLog
        with get_session() as session:
            session.add(
                QueryLog(
                    query="q1",
                    answer="a1",
                    model_used="gpt-4o-mini",
                    prompt_tokens=100,
                    completion_tokens=50,
                    cost_cny=0.001,
                )
            )
            session.add(
                QueryLog(
                    query="q2",
                    answer="a2",
                    model_used="gpt-4o-mini",
                    prompt_tokens=200,
                    completion_tokens=100,
                    cost_cny=0.003,
                )
            )
            session.add(
                QueryLog(
                    query="q3",
                    answer="a3",
                    model_used="glm-4-flash",
                    prompt_tokens=500,
                    completion_tokens=200,
                    cost_cny=0.0001,
                )
            )
            session.commit()
        resp = client.get("/api/stats/tokens")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_prompt_tokens"] == 800  # 100+200+500
        assert body["total_completion_tokens"] == 350  # 50+100+200
        assert body["total_tokens"] == 1150
        assert body["total_cost_cny"] == pytest.approx(0.0041, abs=1e-6)
        assert body["total_queries"] == 3
        # by_model 按 cost 降序（gpt-4o-mini 总成本更高）
        assert body["by_model"][0]["model"] == "gpt-4o-mini"
        assert body["by_model"][0]["count"] == 2
        assert body["by_model"][0]["prompt_tokens"] == 300
        assert body["by_model"][1]["model"] == "glm-4-flash"

    def test_token_stats_recent(self, client, tmp_db):
        """最近明细端点。"""
        with get_session() as session:
            for i in range(5):
                session.add(
                    QueryLog(
                        query=f"q{i}",
                        answer=f"a{i}",
                        model_used="gpt-4o-mini",
                        prompt_tokens=i * 10,
                        completion_tokens=i * 5,
                        cost_cny=i * 0.001,
                    )
                )
            session.commit()
        resp = client.get("/api/stats/tokens/recent?limit=3")
        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == 3
        assert body["total"] == 3
        assert len(body["items"]) == 3
        # 倒序：最新在前
        item = body["items"][0]
        assert "id" in item
        assert "query" in item
        assert "model_used" in item
        assert "prompt_tokens" in item
        assert "completion_tokens" in item
        assert "total_tokens" in item
        assert "cost_cny" in item
        assert "latency_ms" in item
        assert "created_at" in item

    def test_token_stats_recent_default_limit(self, client, tmp_db):
        """默认 limit=20。"""
        resp = client.get("/api/stats/tokens/recent")
        assert resp.status_code == 200
        assert resp.json()["limit"] == 20

    def test_token_stats_recent_limit_max(self, client, tmp_db):
        """limit 上限 200。"""
        resp = client.get("/api/stats/tokens/recent?limit=999")
        assert resp.status_code == 422

    def test_token_stats_recent_limit_min(self, client, tmp_db):
        """limit 下限 1。"""
        resp = client.get("/api/stats/tokens/recent?limit=0")
        assert resp.status_code == 422

    def test_token_stats_admin_when_auth_disabled(self, client, tmp_db):
        """auth_enabled=False → 任意访问者可查（dev 模式）。"""
        resp = client.get("/api/stats/tokens")
        assert resp.status_code == 200

    def test_token_stats_admin_required_when_auth_enabled(
        self, client, tmp_db, monkeypatch
    ):
        """auth_enabled=True → 非 admin → 403。"""
        from hermes_kb.api.deps import jwt_encode
        from hermes_kb.config import override_settings

        secret = "test-secret-for-stats-only-1234567890"
        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret=secret,
        )
        token = jwt_encode({"sub": "user1", "role": "user"}, secret)
        resp = client.get(
            "/api/stats/tokens", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_token_stats_admin_allowed_with_admin_token(
        self, client, tmp_db, monkeypatch
    ):
        """auth_enabled=True + admin token → 200。"""
        from hermes_kb.api.deps import jwt_encode
        from hermes_kb.config import override_settings

        secret = "test-secret-for-stats-only-1234567890"
        override_settings(
            auth_enabled=True,
            auth_password="test123",
            auth_username="admin",
            jwt_secret=secret,
        )
        token = jwt_encode({"sub": "admin", "role": "admin"}, secret)
        resp = client.get(
            "/api/stats/tokens", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 端到端：mock 问答 → 统计
# ---------------------------------------------------------------------------
class TestTokenE2E:
    def test_ask_then_stats(self, client, tmp_db):
        """问答 → 统计端点反映。"""
        # 触发一次 mock 问答
        client.post("/api/ask", json={"query": "金酒有什么特点？"})
        # 查询统计
        resp = client.get("/api/stats/tokens")
        body = resp.json()
        assert body["total_queries"] >= 1
        # mock 模型 token 数为 0
        mock_model_stat = next(
            (m for m in body["by_model"] if "mock" in m["model"]), None
        )
        assert mock_model_stat is not None
        assert mock_model_stat["count"] >= 1
