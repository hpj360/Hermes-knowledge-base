"""网关检索契约端点（GET /kb/search）契约测试。

对应主仓 hermes ``workbench/server_routes/kb.py::h_get_kb_search`` 的上游契约：
GET /kb/search?q=... → 200 {"query", "results", "count", "engine"}。
此前 kb 侧无该路径，主仓代理永远 502（P2-1 契约缺口）。
"""

from __future__ import annotations


def test_kb_search_returns_hits(client, seeded_importer) -> None:
    resp = client.get("/kb/search", params={"q": "威士忌", "top_k": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "威士忌"
    assert isinstance(data["results"], list)
    assert 1 <= len(data["results"]) <= 5
    for hit in data["results"]:
        assert set(hit) == {"doc_id", "title", "snippet", "score", "source"}
        assert hit["snippet"]
        assert isinstance(hit["score"], float)
    assert data["count"] == len(data["results"])


def test_kb_search_empty_query_rejected(client) -> None:
    assert client.get("/kb/search", params={"q": " "}).status_code == 422
    assert client.get("/kb/search").status_code == 422


def test_kb_search_top_k_bounds(client, seeded_importer) -> None:
    assert client.get("/kb/search", params={"q": "酒", "top_k": 0}).status_code == 422
    assert client.get("/kb/search", params={"q": "酒", "top_k": 999}).status_code == 422
