"""B6+: IMA「酒博士」外部参考联检测试。

覆盖：
- S 级高价值关键词识别（_is_high_value_query）
- ExternalRef 构造（去重 / 截断 / 上限）
- RAG answer 低置信度触发联检
- RAG answer 高价值 query 触发联检
- IMA 未配置 / API 失败时降级不阻塞主流程
- 流式 meta 含 external_refs
- API 端点 /api/ask 响应含 external_refs 字段

UTF-8 编码（Windows 兼容）。
"""
from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from hermes_kb.llm import LLMClient
from hermes_kb.rag import (
    ExternalRef,
    RAGEngine,
    _build_external_refs,
    _is_high_value_query,
)
from hermes_kb.retrieval import HybridRetriever, RetrievalHit


# ---------------------------------------------------------------------------
# _is_high_value_query
# ---------------------------------------------------------------------------
def test_is_high_value_query_gb_standard():
    """GB/T 国标号触发。"""
    assert _is_high_value_query("GB/T 10781 浓香型白酒") is True
    assert _is_high_value_query("GB 2757 蒸馏酒卫生标准") is True
    assert _is_high_value_query("GBT10781") is True


def test_is_high_value_query_aroma_type():
    """十二大香型触发。"""
    assert _is_high_value_query("酱香型白酒的特点") is True
    assert _is_high_value_query("清香和浓香的区别") is True
    assert _is_high_value_query("兼型白酒工艺") is True


def test_is_high_value_query_region():
    """地理标志产区触发。"""
    assert _is_high_value_query("茅台镇产区范围") is True
    assert _is_high_value_query("泸州老窖工艺") is True
    assert _is_high_value_query("汾阳市杏花村") is True


def test_is_high_value_query_topic():
    """高价值主题词触发。"""
    assert _is_high_value_query("白酒酿造工艺") is True
    assert _is_high_value_query("评酒感官术语") is True
    assert _is_high_value_query("年份酒判定方法") is True


def test_is_high_value_query_negative():
    """普通 query 不触发。"""
    assert _is_high_value_query("金酒的核心风味") is False
    assert _is_high_value_query("威士忌怎么喝") is False
    assert _is_high_value_query("") is False
    assert _is_high_value_query(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _build_external_refs
# ---------------------------------------------------------------------------
def test_build_external_refs_dedup():
    """相同标题去重。"""
    items = [
        {"title": "GB/T 10781", "content": "浓香型白酒", "url": "u1"},
        {"title": "GB/T 10781", "content": "重复", "url": "u2"},
        {"title": "GB/T 26760", "content": "酱香型", "url": "u3"},
    ]
    refs = _build_external_refs(items)
    assert len(refs) == 2
    assert refs[0].title == "GB/T 10781"
    assert refs[1].title == "GB/T 26760"


def test_build_external_refs_skips_empty_title():
    """空标题条目被跳过。"""
    items = [
        {"title": "", "content": "x"},
        {"title": "   ", "content": "y"},
        {"title": "有效标题", "content": "z"},
    ]
    refs = _build_external_refs(items)
    assert len(refs) == 1
    assert refs[0].title == "有效标题"


def test_build_external_refs_limit():
    """超过 5 条时截断为 5 条。"""
    items = [{"title": f"标题{i}", "content": "c", "url": ""} for i in range(10)]
    refs = _build_external_refs(items)
    assert len(refs) == 5
    assert refs[0].title == "标题0"
    assert refs[-1].title == "标题4"


def test_build_external_refs_snippet_truncated():
    """snippet 截断到 200 字符。"""
    long_content = "x" * 500
    items = [{"title": "t", "content": long_content, "url": "u"}]
    refs = _build_external_refs(items)
    assert len(refs[0].snippet) == 200


def test_build_external_refs_source_label():
    """source 固定为 '酒博士'。"""
    items = [{"title": "t", "content": "c", "url": "u"}]
    refs = _build_external_refs(items)
    assert refs[0].source == "酒博士"


# ---------------------------------------------------------------------------
# RAGEngine 集成（mock IMA search_knowledge）
# ---------------------------------------------------------------------------
class _StubRetriever:
    """可控检索器：返回预设 hits，便于触发低置信度/正常分支。"""

    def __init__(self, hits: list[RetrievalHit]) -> None:
        self._hits = hits

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievalHit]:
        return list(self._hits)


def _make_hit(score: float = 0.05, title: str = "种子文档") -> RetrievalHit:
    """构造一条 RetrievalHit，score 默认高于阈值 0.015。"""
    return RetrievalHit(
        chunk_rowid=1,
        doc_id="doc_test",
        title=title,
        text="测试内容",
        score=score,
        source="bm25",
    )


def _mock_ima_response(items: list[dict[str, Any]]) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        content=json.dumps(
            {"code": 0, "data": {"info_list": items, "cursor": "", "has_more": False}}
        ).encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("POST", "https://ima.qq.com/test"),
    )


def test_rag_no_ima_no_external_refs(seeded_importer, monkeypatch):
    """IMA 未配置 + 高价值 query → external_refs=[]（不触发）。"""
    monkeypatch.delenv("KB_IMA_CLIENT_ID", raising=False)
    monkeypatch.delenv("KB_IMA_API_KEY", raising=False)
    from hermes_kb.config import reset_settings
    reset_settings()

    rag = RAGEngine(retriever=_StubRetriever([_make_hit()]), llm_client=LLMClient())
    result = rag.answer("GB/T 10781 浓香型白酒国家标准")
    assert result.external_refs == []
    assert result.answer  # 主流程正常返回


def test_rag_low_confidence_triggers_ima(seeded_importer, monkeypatch):
    """低置信度 + IMA 启用 → external_refs 非空。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    # 空检索 → 低置信度
    rag = RAGEngine(
        retriever=_StubRetriever([]), llm_client=LLMClient()
    )

    def fake_post(url, json, headers, timeout):
        return _mock_ima_response([
            {"title": "GB/T 10781 浓香型白酒", "content": "国家标准全文", "url": "https://example.com/gb10781"},
            {"title": "浓香型白酒技术规范", "content": "技术要求", "url": ""},
        ])

    monkeypatch.setattr(httpx, "post", fake_post)
    result = rag.answer("随便一个本地没有的问题")
    assert result.low_confidence is True
    assert len(result.external_refs) == 2
    assert result.external_refs[0].title == "GB/T 10781 浓香型白酒"
    assert result.external_refs[0].url == "https://example.com/gb10781"
    assert result.external_refs[0].source == "酒博士"


def test_rag_high_value_query_triggers_ima(seeded_importer, monkeypatch):
    """高价值 query + IMA 启用 + 本地命中 → external_refs 非空。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    # 高分 hit → 非低置信度
    rag = RAGEngine(
        retriever=_StubRetriever([_make_hit(score=0.05)]), llm_client=LLMClient()
    )

    def fake_post(url, json, headers, timeout):
        return _mock_ima_response([
            {"title": "酱香型白酒工艺", "content": "12987 工艺", "url": "https://example.com/jiangxiang"},
        ])

    monkeypatch.setattr(httpx, "post", fake_post)
    result = rag.answer("酱香型白酒酿造工艺")
    assert result.low_confidence is False
    assert len(result.external_refs) == 1
    assert result.external_refs[0].title == "酱香型白酒工艺"


def test_rag_normal_query_no_trigger(seeded_importer, monkeypatch):
    """普通 query + IMA 启用 + 本地命中 → 不触发 IMA。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    rag = RAGEngine(
        retriever=_StubRetriever([_make_hit(score=0.05)]), llm_client=LLMClient()
    )

    called = {"n": 0}

    def fake_post(url, json, headers, timeout):
        called["n"] += 1
        return _mock_ima_response([])

    monkeypatch.setattr(httpx, "post", fake_post)
    result = rag.answer("金酒的核心风味")  # 普通查询
    assert result.external_refs == []
    assert called["n"] == 0  # IMA 未被调用


def test_rag_ima_api_failure_graceful(seeded_importer, monkeypatch):
    """IMA API 抛错 → external_refs=[]，主流程不阻塞。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    rag = RAGEngine(
        retriever=_StubRetriever([]), llm_client=LLMClient()
    )  # 空检索 → 低置信度 → 触发 IMA

    def fake_post(url, json, headers, timeout):
        return httpx.Response(
            status_code=200,
            content=json.dumps(
                {"code": 220021, "msg": "资料获取次数已达上限"}
            ).encode(),
            headers={"content-type": "application/json"},
            request=httpx.Request("POST", "https://ima.qq.com/test"),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    result = rag.answer("GB/T 10781")
    # 失败降级为空，主流程仍正常返回低置信度提示
    assert result.external_refs == []
    assert result.low_confidence is True
    assert result.answer  # 仍有低置信度提示文本


def test_rag_ima_network_error_graceful(seeded_importer, monkeypatch):
    """IMA 网络异常 → external_refs=[]，主流程不阻塞。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    rag = RAGEngine(
        retriever=_StubRetriever([]), llm_client=LLMClient()
    )

    def fake_post(url, json, headers, timeout):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)
    result = rag.answer("茅台镇地理标志")
    assert result.external_refs == []
    assert result.low_confidence is True


def test_rag_to_dict_includes_external_refs(seeded_importer, monkeypatch):
    """to_dict 输出含 external_refs 字段（前端契约）。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    rag = RAGEngine(retriever=_StubRetriever([]), llm_client=LLMClient())

    def fake_post(url, json, headers, timeout):
        return _mock_ima_response([
            {"title": "国标全文", "content": "c", "url": "u"},
        ])

    monkeypatch.setattr(httpx, "post", fake_post)
    result = rag.answer("GB 2757 蒸馏酒卫生标准")
    d = result.to_dict()
    assert "external_refs" in d
    assert isinstance(d["external_refs"], list)
    assert d["external_refs"][0]["title"] == "国标全文"
    assert d["external_refs"][0]["source"] == "酒博士"


# ---------------------------------------------------------------------------
# 流式 answer_stream meta 含 external_refs
# ---------------------------------------------------------------------------
def test_rag_stream_meta_includes_external_refs(seeded_importer, monkeypatch):
    """流式 meta 事件应包含 external_refs 字段。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    import anyio

    rag = RAGEngine(retriever=_StubRetriever([]), llm_client=LLMClient())

    def fake_post(url, json, headers, timeout):
        return _mock_ima_response([
            {"title": "陈酿判定", "content": "y", "url": "https://e.com/y"},
        ])

    monkeypatch.setattr(httpx, "post", fake_post)

    async def collect() -> list[dict[str, Any]]:
        metas: list[dict[str, Any]] = []
        async for chunk in rag.answer_stream("年份酒陈酿判定方法"):
            assert chunk.startswith("data: ")
            payload = json.loads(chunk[6:])
            if payload.get("type") == "meta":
                metas.append(payload)
        return metas

    metas = anyio.run(collect)
    assert len(metas) == 1
    meta = metas[0]
    assert meta["low_confidence"] is True
    assert "external_refs" in meta
    assert len(meta["external_refs"]) == 1
    assert meta["external_refs"][0]["title"] == "陈酿判定"


# ---------------------------------------------------------------------------
# API 端点 /api/ask 响应含 external_refs
# ---------------------------------------------------------------------------
def test_api_ask_returns_external_refs(client, monkeypatch):
    """/api/ask 响应体含 external_refs 字段（默认空列表）。"""
    monkeypatch.delenv("KB_IMA_CLIENT_ID", raising=False)
    monkeypatch.delenv("KB_IMA_API_KEY", raising=False)
    from hermes_kb.config import reset_settings
    reset_settings()

    client.post("/api/seed")
    r = client.post("/api/ask", json={"query": "金酒的核心风味"})
    assert r.status_code == 200
    body = r.json()
    assert "external_refs" in body
    assert isinstance(body["external_refs"], list)
    assert body["external_refs"] == []  # IMA 未配置


def test_api_ask_with_ima_external_refs(client, monkeypatch):
    """IMA 启用 + 高价值 query → /api/ask 返回 external_refs。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    client.post("/api/seed")

    def fake_post(url, json, headers, timeout):
        return _mock_ima_response([
            {"title": "GB/T 10781 浓香型白酒", "content": "国标", "url": "https://e.com/gb"},
        ])

    monkeypatch.setattr(httpx, "post", fake_post)
    r = client.post("/api/ask", json={"query": "GB/T 10781 浓香型白酒国家标准"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["external_refs"]) == 1
    assert body["external_refs"][0]["title"] == "GB/T 10781 浓香型白酒"
    assert body["external_refs"][0]["source"] == "酒博士"
