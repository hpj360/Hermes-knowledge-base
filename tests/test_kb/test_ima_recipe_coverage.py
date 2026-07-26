"""ima_sync.py + recipe_match.py 覆盖率补强测试（阶段6 批次2）。

覆盖目标：
- ima_sync.py: 非 JSON 响应/非 dict payload/无知识库/搜索失败/空 info_list/去重异常/导入失败
- recipe_match.py: _extract_ingredients_from_seed/_parse_ingredients_from_frontmatter 边界/
  _parse_ingredients_from_content 空输入/_get_recipe_ingredients 回退链/_parse_steps 续行
"""
from __future__ import annotations

import pytest


# ============================================================
# ima_sync.py 覆盖率补强
# ============================================================


def test_ima_post_non_json_response_raises(monkeypatch):
    """_post 收到非 JSON 响应时抛 IMAAPIError。"""
    from hermes_kb.ima_sync import IMAAPIError, _post

    class _FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("not json")

    def fake_post(*a, **kw):
        return _FakeResp()

    monkeypatch.setattr("hermes_kb.ima_sync.httpx.post", fake_post)
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    from hermes_kb.config import reset_settings

    reset_settings()

    with pytest.raises(IMAAPIError, match="非 JSON"):
        _post("/api/test", {})


def test_ima_post_non_dict_payload_raises(monkeypatch):
    """_post 收到非 dict JSON 响应时抛 IMAAPIError。"""
    from hermes_kb.ima_sync import IMAAPIError, _post

    class _FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return ["not", "a", "dict"]  # list 而非 dict

    def fake_post(*a, **kw):
        return _FakeResp()

    monkeypatch.setattr("hermes_kb.ima_sync.httpx.post", fake_post)
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    from hermes_kb.config import reset_settings

    reset_settings()

    with pytest.raises(IMAAPIError, match="结构异常"):
        _post("/api/test", {})


def test_resolve_kb_id_no_knowledge_bases_raises(monkeypatch):
    """resolve_kb_id 在 IMA 账号无知识库时抛 IMAConfigError。"""
    from hermes_kb.ima_sync import IMAConfigError, resolve_kb_id

    # mock list_knowledge_bases 返回空列表
    monkeypatch.setattr("hermes_kb.ima_sync.list_knowledge_bases", lambda query="", limit=10: [])

    with pytest.raises(IMAConfigError, match="未找到任何知识库"):
        resolve_kb_id()


def test_resolve_kb_id_uses_explicit_param(monkeypatch):
    """resolve_kb_id 优先使用显式传入的 kb_id 参数。"""
    from hermes_kb.ima_sync import resolve_kb_id

    assert resolve_kb_id("explicit-kb-id") == "explicit-kb-id"


def test_resolve_kb_id_uses_env_config(monkeypatch):
    """resolve_kb_id 回退到 KB_IMA_KB_ID 环境变量。"""
    from hermes_kb.ima_sync import resolve_kb_id

    monkeypatch.setenv("KB_IMA_KB_ID", "kb-from-env")
    from hermes_kb.config import reset_settings

    reset_settings()
    assert resolve_kb_id() == "kb-from-env"


def test_sync_knowledge_base_empty_info_list_breaks(monkeypatch, tmp_db):
    """sync_knowledge_base 遇到空 info_list 时中断分页（不报错）。"""
    from hermes_kb import ima_sync as ima

    # mock search_knowledge 返回空 info_list
    def fake_search(query, kb_id=None, limit=20, cursor=""):
        return {"info_list": [], "has_more": False, "cursor": ""}

    monkeypatch.setattr(ima, "search_knowledge", fake_search)
    monkeypatch.setattr(ima, "resolve_kb_id", lambda kb_id=None: "fake-kb")

    result = ima.sync_knowledge_base(query="test", limit=5)
    # 空 info_list 应导致 imported=0、items 为空
    assert result["imported"] == 0
    assert result["skipped"] == 0
    assert result["failed"] == 0
    assert result["items"] == []


def test_sync_knowledge_base_api_error_breaks_loop(monkeypatch, tmp_db):
    """sync_knowledge_base 中 search_knowledge 抛 IMAAPIError 时中断并计入 failed。"""
    from hermes_kb import ima_sync as ima
    from hermes_kb.ima_sync import IMAAPIError

    def boom_search(query, kb_id=None, limit=20, cursor=""):
        raise IMAAPIError("API down")

    monkeypatch.setattr(ima, "search_knowledge", boom_search)
    monkeypatch.setattr(ima, "resolve_kb_id", lambda kb_id=None: "fake-kb")

    result = ima.sync_knowledge_base(query="test", limit=5)
    assert result["failed"] >= 1


def test_sync_knowledge_base_dedup_exception_continues(monkeypatch, tmp_db):
    """sync_knowledge_base 中去重查询抛异常时跳过该项并继续（不中断）。"""
    from hermes_kb import ima_sync as ima

    def fake_search(query, kb_id=None, limit=20, cursor=""):
        return {
            "info_list": [
                {"title": "测试配方", "url": "http://x", "content": "内容", "doc_id": "x1"},
            ],
            "has_more": False,
            "cursor": "",
        }

    monkeypatch.setattr(ima, "search_knowledge", fake_search)
    monkeypatch.setattr(ima, "resolve_kb_id", lambda kb_id=None: "fake-kb")

    # mock get_session 抛异常（去重查询失败）
    def boom_session():
        raise RuntimeError("DB down")

    monkeypatch.setattr(ima, "get_session", boom_session)

    result = ima.sync_knowledge_base(query="test", limit=5)
    # 去重失败应计入 failed，但不中断
    assert result["failed"] >= 1


# ============================================================
# recipe_match.py 覆盖率补强
# ============================================================


def test_extract_ingredients_from_seed_found():
    """_extract_ingredients_from_seed 找到匹配的种子配方时返回材料集合。"""
    from hermes_kb.recipe_match import _extract_ingredients_from_seed
    from hermes_kb.seed_recipes import SEED_RECIPES

    # 用第一个种子配方的标题
    title = SEED_RECIPES[0]["title"]
    result = _extract_ingredients_from_seed(title)
    assert isinstance(result, set)
    assert len(result) > 0


def test_extract_ingredients_from_seed_not_found():
    """_extract_ingredients_from_seed 未找到匹配时返回空集合。"""
    from hermes_kb.recipe_match import _extract_ingredients_from_seed

    result = _extract_ingredients_from_seed("不存在的配方标题xyz123")
    assert result == set()


def test_parse_ingredients_from_frontmatter_empty_content():
    """_parse_ingredients_from_frontmatter 对空 content 返回空集合。"""
    from hermes_kb.recipe_match import _parse_ingredients_from_frontmatter

    assert _parse_ingredients_from_frontmatter("") == set()
    assert _parse_ingredients_from_frontmatter(None) == set()


def test_parse_ingredients_from_frontmatter_no_match():
    """_parse_ingredients_from_frontmatter 无 frontmatter 注释时返回空集合。"""
    from hermes_kb.recipe_match import _parse_ingredients_from_frontmatter

    content = "这是一段没有 frontmatter 的普通配方内容。"
    assert _parse_ingredients_from_frontmatter(content) == set()


def test_parse_ingredients_from_frontmatter_with_match():
    """_parse_ingredients_from_frontmatter 解析 frontmatter 注释返回材料集合。"""
    from hermes_kb.recipe_match import _parse_ingredients_from_frontmatter

    content = "<!-- ingredients: 金酒|汤力水|柠檬|冰块 -->\n\n## 配方内容"
    result = _parse_ingredients_from_frontmatter(content)
    assert "金酒" in result
    assert "汤力水" in result
    assert "柠檬" in result
    assert "冰块" in result


def test_parse_ingredients_from_content_empty():
    """_parse_ingredients_from_content 对空 content 返回空集合。"""
    from hermes_kb.recipe_match import _parse_ingredients_from_content

    assert _parse_ingredients_from_content("") == set()
    assert _parse_ingredients_from_content(None) == set()


def test_parse_ingredients_from_content_with_matches():
    """_parse_ingredients_from_content 从内容中解析标准材料名。"""
    from hermes_kb.recipe_match import _parse_ingredients_from_content

    content = "将金酒和汤力水混合，加入柠檬汁装饰。"
    result = _parse_ingredients_from_content(content)
    # 应包含标准材料名（具体取决于 ingredients.py 的 canonical 列表）
    assert isinstance(result, set)


def test_get_recipe_ingredients_frontmatter_priority():
    """_get_recipe_ingredients 优先使用 frontmatter。"""
    from hermes_kb.recipe_match import _get_recipe_ingredients

    recipe = {
        "title": "测试配方",
        "content": "<!-- ingredients: 金酒|汤力水 -->\n\n配方内容",
    }
    result = _get_recipe_ingredients(recipe)
    assert "金酒" in result
    assert "汤力水" in result


def test_get_recipe_ingredients_fallback_to_content():
    """_get_recipe_ingredients 无 frontmatter 和 seed_meta 时回退到内容解析。"""
    from hermes_kb.recipe_match import _get_recipe_ingredients

    recipe = {
        "title": "完全不存在的配方xyz",
        "content": "将金酒和汤力水混合。",
    }
    result = _get_recipe_ingredients(recipe)
    assert isinstance(result, set)


def test_parse_steps_with_continuation_line():
    """_parse_steps_from_content 处理列表项续行（多行步骤拼接）。"""
    from hermes_kb.recipe_match import _parse_steps_from_content

    content = """## 步骤

1. 第一步
这是第一部的续行
2. 第二步
"""
    steps = _parse_steps_from_content(content)
    assert len(steps) >= 2
    assert "第一步" in steps[0]
    assert "续行" in steps[0]


def test_parse_steps_empty_returns_list():
    """_parse_steps_from_content 无步骤段落时返回空列表。"""
    from hermes_kb.recipe_match import _parse_steps_from_content

    content = "这是一段没有步骤段落的内容。"
    steps = _parse_steps_from_content(content)
    assert steps == []
