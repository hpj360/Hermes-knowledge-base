"""B6: IMA 知识库同步测试（mock HTTP，无真实网络调用）。"""
from __future__ import annotations

import json
from typing import Any

import httpx
import pytest


# ---------------------------------------------------------------------------
# _headers / 凭证配置
# ---------------------------------------------------------------------------
def test_headers_raises_when_not_configured(monkeypatch):
    """未配置凭证 → IMAConfigError。"""
    monkeypatch.delenv("KB_IMA_CLIENT_ID", raising=False)
    monkeypatch.delenv("KB_IMA_API_KEY", raising=False)
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import IMAConfigError, _headers

    reset_settings()
    with pytest.raises(IMAConfigError):
        _headers()


def test_headers_includes_custom_auth(monkeypatch):
    """配置凭证 → 头含 ima-openapi-clientid / ima-openapi-apikey / Content-Type。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "test-cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "test-key")
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import _headers

    reset_settings()
    h = _headers()
    assert h["ima-openapi-clientid"] == "test-cid"
    assert h["ima-openapi-apikey"] == "test-key"
    assert "application/json" in h["Content-Type"]


def test_ima_enabled_flag(monkeypatch):
    """ima_enabled 反映凭证是否齐全。"""
    monkeypatch.delenv("KB_IMA_CLIENT_ID", raising=False)
    monkeypatch.delenv("KB_IMA_API_KEY", raising=False)
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    assert Settings().ima_enabled is False

    monkeypatch.setenv("KB_IMA_CLIENT_ID", "x")
    monkeypatch.setenv("KB_IMA_API_KEY", "y")
    reset_settings()
    assert Settings().ima_enabled is True


# ---------------------------------------------------------------------------
# _post 错误处理（mock httpx.post）
# ---------------------------------------------------------------------------
def _mock_response(status_code: int = 200, payload: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(payload or {}).encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("POST", "https://ima.qq.com/test"),
    )


def test_post_raises_on_nonzero_code(monkeypatch):
    """IMA 返回 code != 0 → IMAAPIError 含 msg。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import IMAAPIError, _post

    reset_settings()

    def fake_post(url, json, headers, timeout):
        return _mock_response(200, {"code": 401, "msg": "invalid apikey"})

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(IMAAPIError, match="invalid apikey"):
        _post("/some/path", {"q": "x"})


def test_post_raises_on_http_error(monkeypatch):
    """HTTP 5xx → IMAAPIError。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import IMAAPIError, _post

    reset_settings()

    def fake_post(url, json, headers, timeout):
        return _mock_response(503, {"code": 0, "data": {}})

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(IMAAPIError):
        _post("/some/path", {"q": "x"})


def test_post_returns_data_on_success(monkeypatch):
    """code=0 → 返回 data 字段（脱壳）。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import _post

    reset_settings()

    def fake_post(url, json, headers, timeout):
        return _mock_response(200, {"code": 0, "msg": "ok", "data": {"foo": "bar"}})

    monkeypatch.setattr(httpx, "post", fake_post)
    data = _post("/x", {})
    assert data == {"foo": "bar"}


# ---------------------------------------------------------------------------
# list_knowledge_bases / resolve_kb_id / search_knowledge
# ---------------------------------------------------------------------------
def test_list_knowledge_bases(monkeypatch):
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import list_knowledge_bases

    reset_settings()

    captured: dict[str, Any] = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["body"] = json
        return _mock_response(200, {
            "code": 0,
            "data": {"info_list": [
                {"kb_id": "kb1", "kb_name": "鸡尾酒知识库", "content_count": 100},
                {"kb_id": "kb2", "kb_name": "葡萄酒笔记", "content_count": 50},
            ]},
        })

    monkeypatch.setattr(httpx, "post", fake_post)
    kbs = list_knowledge_bases(query="鸡尾酒", limit=2)
    assert len(kbs) == 2
    assert kbs[0]["kb_id"] == "kb1"
    assert "/openapi/wiki/v1/search_knowledge_base" in captured["url"]
    assert captured["body"]["query"] == "鸡尾酒"


def test_resolve_kb_id_explicit_wins(monkeypatch):
    """显式传入 > 配置 > 自动检测。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "from-config")
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import resolve_kb_id

    reset_settings()
    assert resolve_kb_id("explicit") == "explicit"
    assert resolve_kb_id(None) == "from-config"
    assert resolve_kb_id("") == "from-config"


def test_resolve_kb_id_falls_back_to_first(monkeypatch):
    """无显式 + 无配置 → list_knowledge_bases 第一个。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.delenv("KB_IMA_KB_ID", raising=False)
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import resolve_kb_id

    reset_settings()

    def fake_post(url, json, headers, timeout):
        return _mock_response(200, {
            "code": 0, "data": {"info_list": [{"kb_id": "auto-kb"}]},
        })

    monkeypatch.setattr(httpx, "post", fake_post)
    assert resolve_kb_id(None) == "auto-kb"


def test_search_knowledge_passes_kb_id(monkeypatch):
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import search_knowledge

    reset_settings()
    captured: dict[str, Any] = {}

    def fake_post(url, json, headers, timeout):
        captured["body"] = json
        return _mock_response(200, {
            "code": 0,
            "data": {
                "info_list": [{"title": "莫吉托", "content": "薄荷叶+朗姆"}],
                "cursor": "next-page",
                "has_more": True,
            },
        })

    monkeypatch.setattr(httpx, "post", fake_post)
    result = search_knowledge(query="莫吉托", kb_id="kb-1", limit=5)
    assert result["info_list"][0]["title"] == "莫吉托"
    assert result["cursor"] == "next-page"
    assert result["has_more"] is True
    assert captured["body"]["knowledge_base_id"] == "kb-1"
    assert captured["body"]["query"] == "莫吉托"


# ---------------------------------------------------------------------------
# sync_knowledge_base 端到端（mock 检索 + 真 ImportService）
# ---------------------------------------------------------------------------
def test_sync_knowledge_base_imports(monkeypatch, tmp_db):
    """成功导入 → imported=1, items 含 doc_id。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import sync_knowledge_base

    reset_settings()

    def fake_post(url, json, headers, timeout):
        return _mock_response(200, {
            "code": 0,
            "data": {
                "info_list": [{
                    "item_id": "i1",
                    "title": "经典莫吉托",
                    "content": "朗姆酒 + 薄荷叶 + 青柠",
                    "url": "https://example.com/mojito",
                }],
                "cursor": "",
                "has_more": False,
            },
        })

    monkeypatch.setattr(httpx, "post", fake_post)
    result = sync_knowledge_base(query="莫吉托", limit=10)
    assert result["imported"] == 1
    assert result["skipped"] == 0
    assert result["failed"] == 0
    assert result["kb_id"] == "kb-target"
    assert len(result["items"]) == 1
    assert result["items"][0]["status"] == "imported"
    assert result["items"][0]["doc_id"]


def test_sync_knowledge_base_dedup(monkeypatch, tmp_db):
    """重复同步 → 第二次 imported=0, skipped=1。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    from hermes_kb.ima_sync import sync_knowledge_base

    reset_settings()

    def fake_post(url, json, headers, timeout):
        return _mock_response(200, {
            "code": 0,
            "data": {
                "info_list": [{
                    "item_id": "i1",
                    "title": "经典莫吉托",
                    "content": "朗姆酒",
                    "url": "",
                }],
                "cursor": "",
                "has_more": False,
            },
        })

    monkeypatch.setattr(httpx, "post", fake_post)
    first = sync_knowledge_base(query="x", limit=5)
    second = sync_knowledge_base(query="x", limit=5)
    assert first["imported"] == 1
    assert second["imported"] == 0
    assert second["skipped"] == 1


# ---------------------------------------------------------------------------
# API 端点
# ---------------------------------------------------------------------------
def test_api_ima_list_kbs_returns_400_when_not_configured(client, monkeypatch):
    """未配置凭证 → 400 友好提示。"""
    monkeypatch.delenv("KB_IMA_CLIENT_ID", raising=False)
    monkeypatch.delenv("KB_IMA_API_KEY", raising=False)
    from hermes_kb.config import reset_settings
    reset_settings()
    resp = client.get("/api/lab/ima/knowledge-bases")
    assert resp.status_code == 400
    assert "KB_IMA_CLIENT_ID" in resp.json()["detail"]


def test_api_ima_list_kbs_returns_items(client, monkeypatch):
    """配置凭证 + mock IMA → 返回知识库列表。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    from hermes_kb.config import reset_settings
    reset_settings()

    def fake_post(url, json, headers, timeout):
        return _mock_response(200, {
            "code": 0,
            "data": {"info_list": [{"kb_id": "kb1", "kb_name": "测试库"}]},
        })
    monkeypatch.setattr(httpx, "post", fake_post)
    resp = client.get("/api/lab/ima/knowledge-bases")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["kb_id"] == "kb1"


def test_api_ima_sync_imports(client, monkeypatch):
    """POST /api/lab/ima/sync 成功导入。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    def fake_post(url, json, headers, timeout):
        return _mock_response(200, {
            "code": 0,
            "data": {
                "info_list": [{
                    "item_id": "i1",
                    "title": "玛格丽特",
                    "content": "龙舌兰 + 君度 + 青柠",
                    "url": "https://example.com/mar",
                }],
                "cursor": "",
                "has_more": False,
            },
        })
    monkeypatch.setattr(httpx, "post", fake_post)
    resp = client.post("/api/lab/ima/sync", json={"query": "玛格丽特", "limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "ima"
    assert body["imported"] == 1
    assert body["kb_id"] == "kb-target"


def test_api_ima_search_requires_query(client, monkeypatch):
    """GET /api/lab/ima/search query 为空 → 400。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    from hermes_kb.config import reset_settings
    reset_settings()
    resp = client.get("/api/lab/ima/search", params={"query": ""})
    assert resp.status_code == 400


def test_api_ima_search_returns_items(client, monkeypatch):
    """GET /api/lab/ima/search 返回检索片段。"""
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    monkeypatch.setenv("KB_IMA_KB_ID", "kb-target")
    from hermes_kb.config import reset_settings
    reset_settings()

    def fake_post(url, json, headers, timeout):
        return _mock_response(200, {
            "code": 0,
            "data": {
                "info_list": [{"title": "金汤力", "content": "金酒+汤力水"}],
                "cursor": "",
                "has_more": False,
            },
        })
    monkeypatch.setattr(httpx, "post", fake_post)
    resp = client.get("/api/lab/ima/search", params={"query": "金汤力"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["info_list"][0]["title"] == "金汤力"
