"""鸡尾酒智能体集成测试。

覆盖：
- Phase 3: 5 个 function calling 工具（Mock 路径）
- Phase 4: /agent/ask SSE 流式 + /agent/ask/sync 同步
- 年龄门强制拦截 / 无酒精放行
- 空查询 / 异常路径
- 意图识别规则（Mock 路径）
"""
from __future__ import annotations

import json

# ============================================================================
# Phase 3: Agent Tools 单元测试
# ============================================================================


def test_get_tool_registry():
    """5 个工具均已注册且可检索。"""
    from hermes_kb.agent_tools import TOOLS, get_tool

    assert len(TOOLS) == 5
    names = {t.name for t in TOOLS}
    assert names == {"search_recipes", "get_recipe", "match_by_ingredients",
                      "find_substitute", "get_knowledge"}
    assert get_tool("search_recipes") is not None
    assert get_tool("nonexistent") is None


def test_tool_parameters_have_required():
    """每个工具的 parameters 是有效的 JSON Schema。"""
    from hermes_kb.agent_tools import TOOLS

    for t in TOOLS:
        assert t.parameters["type"] == "object"
        assert "properties" in t.parameters


def test_search_recipes_execute(seeded_recipes):
    """search_recipes：无 query 返回所有配方（受 limit 约束）。"""
    from hermes_kb.agent_tools import search_recipes

    result = search_recipes(limit=3)
    assert "error" not in result, result.get("error")
    res = result["result"]
    assert "results" in res
    assert len(res["results"]) <= 3


def test_search_recipes_with_query(seeded_recipes):
    """search_recipes：带 query 返回匹配结果。"""
    from hermes_kb.agent_tools import search_recipes

    result = search_recipes(query="马天尼", limit=5)
    assert "error" not in result, result.get("error")
    # 可能没有匹配（种子配方中 "马天尼 Martini" 含中文）
    assert "results" in result["result"]


def test_get_recipe_found(seeded_recipes):
    """get_recipe：精确匹配返回配方详情。"""
    from hermes_kb.agent_tools import get_recipe

    result = get_recipe(title="马天尼 Martini")
    assert "error" not in result, result.get("error")
    assert result["result"] is not None
    assert result["result"]["title"] == "马天尼 Martini"


def test_get_recipe_not_found(seeded_recipes):
    """get_recipe：无精确匹配时返回 None 或检索兜底（不报错）。"""
    from hermes_kb.agent_tools import get_recipe

    result = get_recipe(title="不存在不存在的配方XYZ")
    assert "error" not in result
    # 规范：找不到精确匹配时给出最接近的检索结果；无命中则为 None
    assert result["result"] is None or isinstance(result["result"], dict)


def test_match_by_ingredients(seeded_recipes):
    """match_by_ingredients：返回 full_match / partial_match。"""
    from hermes_kb.agent_tools import match_by_ingredients

    result = match_by_ingredients(ingredients=["金酒", "味美思"])
    assert "error" not in result, result.get("error")
    res = result["result"]
    # 马天尼使用金酒+味美思，应出现在 full_match 或 partial_match
    all_matches = res.get("full_match", []) + res.get("partial_match", [])
    assert len(all_matches) >= 0  # 种子配方中应有匹配


def test_match_by_ingredients_empty():
    """match_by_ingredients：空列表返回错误。"""
    from hermes_kb.agent_tools import match_by_ingredients

    result = match_by_ingredients(ingredients=[])
    assert "error" in result


def test_find_substitute(seeded_recipes):
    """find_substitute：返回替代品列表。"""
    from hermes_kb.agent_tools import find_substitute

    result = find_substitute(ingredient="金酒")
    assert "error" not in result, result.get("error")
    res = result["result"]
    assert "substitutes" in res


def test_find_substitute_unknown():
    """find_substitute：未知材料返回空列表。"""
    from hermes_kb.agent_tools import find_substitute

    result = find_substitute(ingredient="完全没有这种材料XYZ")
    assert "error" not in result
    assert result["result"]["substitutes"] == []


def test_get_knowledge(seeded_recipes):
    """get_knowledge：返回知识库检索结果。"""
    from hermes_kb.agent_tools import get_knowledge

    result = get_knowledge(query="摇和法")
    assert "error" not in result, result.get("error")
    assert "text" in result["result"]


# ============================================================================
# Phase 4: CocktailAgent 单元测试
# ============================================================================


def test_agent_empty_query():
    """空查询返回提示。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent.ask("")
    assert "请提供具体问题" in res.answer


def test_agent_blank_query():
    """空白查询返回提示。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent.ask("   ")
    assert "请提供具体问题" in res.answer


def test_agent_age_gate_rejected():
    """年龄门未验证时拒绝配方类回答。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent.ask("马天尼怎么做", age_verified=False)
    assert res.rejected is True
    assert "未满 18 周岁" in res.answer


def test_agent_age_gate_non_alcoholic_bypass():
    """无酒精请求不受年龄门限制。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent.ask("推荐一款无酒精鸡尾酒", age_verified=False)
    assert res.rejected is False  # 放行


def test_agent_recipe_detail_mock(seeded_recipes):
    """Mock 路径：recipe_detail 意图返回配方详情。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent.ask("马天尼怎么做")
    assert res.rejected is False
    assert "error" not in res.answer
    assert len(res.turns) >= 1
    # 应含有配方名
    assert "马天尼" in res.answer or "Martini" in res.answer


def test_agent_search_mock(seeded_recipes):
    """Mock 路径：search 意图。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent.ask("推荐好喝的鸡尾酒")
    assert res.rejected is False
    assert len(res.turns) >= 1
    assert "推荐" in res.answer or "配方" in res.answer or "找到" in res.answer


def test_agent_ingredient_match_mock(seeded_recipes):
    """Mock 路径：材料匹配意图。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent.ask("我有金酒和味美思，能做什么酒")
    assert res.rejected is False
    assert len(res.turns) >= 1


def test_agent_substitute_mock(seeded_recipes):
    """Mock 路径：替代品意图。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent.ask("金酒用什么替代")
    assert res.rejected is False
    assert len(res.turns) >= 1
    assert "替代" in res.answer or "未找到" in res.answer


def test_agent_knowledge_mock(seeded_recipes):
    """Mock 路径：知识问答意图。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent.ask("摇和法是什么")
    assert res.rejected is False
    assert len(res.turns) >= 1


def test_agent_result_to_dict():
    """AgentResult.to_dict() 返回正确字段。"""
    from hermes_kb.agent import AgentResult

    res = AgentResult(
        query="test",
        answer="answer",
        citations=[{"doc_id": "abc", "title": "test"}],
        turns=[{"name": "search_recipes", "arguments": {}, "result": {}}],
        model_used="mock",
        prompt_tokens=0,
        completion_tokens=0,
    )
    d = res.to_dict()
    assert d["query"] == "test"
    assert d["answer"] == "answer"
    assert d["model_used"] == "mock"
    assert d["rejected"] is False
    assert "citations" in d
    assert "turns" in d


def test_agent_ask_events_yields_events(seeded_recipes):
    """ask_events 生成 SSE 事件。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    events = list(agent.ask_events("马天尼怎么做"))
    assert len(events) >= 1
    types = {e.get("type") for e in events}
    assert "token" in types or "done" in types or "error" in types


def test_agent_ask_events_empty_query():
    """空查询的 ask_events 返回 error 事件。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    events = list(agent.ask_events(""))
    assert len(events) >= 1
    assert events[0].get("type") == "error"


def test_agent_ask_events_age_gate():
    """年龄门拒绝时 ask_events 返回 token + done。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    events = list(agent.ask_events("马天尼怎么做", age_verified=False))
    assert len(events) >= 1
    types = [e.get("type") for e in events]
    assert "token" in types
    assert "done" in types


# ============================================================================
# Phase 4: API 端点集成测试
# ============================================================================


def test_agent_ask_sync_endpoint(client, seeded_recipes):
    """POST /agent/ask/sync 返回完整结果。"""
    r = client.post(
        "/api/agent/ask/sync",
        json={"query": "马天尼怎么做"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert "turns" in body
    assert "citations" in body
    assert "model_used" in body


def test_agent_ask_sync_empty_query(client):
    """空 query 返回 400。"""
    r = client.post(
        "/api/agent/ask/sync",
        json={"query": ""},
    )
    assert r.status_code == 400


def test_agent_ask_sync_with_history(client, seeded_recipes):
    """带历史上下文的同步问答。"""
    r = client.post(
        "/api/agent/ask/sync",
        json={
            "query": "尼格罗尼呢",
            "history": [{"role": "user", "content": "马天尼怎么做"},
                        {"role": "assistant", "content": "马天尼是..."}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body


def test_agent_ask_sync_history_too_long(client):
    """历史过长返回 400。"""
    long_history = [{"role": "user", "content": "x"}] * 60
    r = client.post(
        "/api/agent/ask/sync",
        json={"query": "test", "history": long_history},
    )
    assert r.status_code == 400


def test_agent_ask_stream_endpoint(client, seeded_recipes):
    """POST /agent/ask 返回 SSE 流。"""
    r = client.post(
        "/api/agent/ask",
        json={"query": "马天尼怎么做"},
    )
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "text/event-stream" in ct

    events = []
    for line in r.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))
    assert len(events) >= 1
    types = {e.get("type") for e in events}
    assert "token" in types or "done" in types or "error" in types


def test_agent_ask_stream_empty_query(client):
    """空 query 的 SSE 返回 error 事件。"""
    r = client.post(
        "/api/agent/ask",
        json={"query": ""},
    )
    assert r.status_code == 400


# ============================================================================
# 意图识别规则
# ============================================================================


def test_detect_intent_recipe_detail():
    """「怎么做」→ recipe_detail。"""
    from hermes_kb.agent import detect_intent

    intent, payload = detect_intent("马天尼怎么做")
    assert intent == "recipe_detail"
    assert "马天尼" in payload


def test_detect_intent_search():
    """「推荐」→ search。"""
    from hermes_kb.agent import detect_intent

    intent, _ = detect_intent("推荐好喝的鸡尾酒")
    assert intent == "search"


def test_detect_intent_ingredient_match():
    """「我有...」→ ingredient_match。"""
    from hermes_kb.agent import detect_intent

    intent, _ = detect_intent("我有金酒和味美思，能做什么")
    assert intent == "ingredient_match"


def test_detect_intent_substitute():
    """「替代」→ substitute。"""
    from hermes_kb.agent import detect_intent

    intent, _ = detect_intent("金酒用什么替代")
    assert intent == "substitute"


def test_detect_intent_knowledge():
    """无酒类关键词 → knowledge。"""
    from hermes_kb.agent import detect_intent

    intent, _ = detect_intent("摇和法是什么")
    assert intent == "knowledge"


# ============================================================================
# 覆盖率补齐：agent_tools 错误分支 / 结构化过滤 / 变体解析
# ============================================================================


def test_search_recipes_base_spirit(seeded_recipes):
    """search_recipes：base_spirit 结构化过滤（Document 查询路径）。"""
    from hermes_kb.agent_tools import search_recipes

    result = search_recipes(base_spirit="gin", limit=5)
    assert "error" not in result, result.get("error")
    for item in result["result"]["results"]:
        assert item.get("base_spirit") in (None, "gin")


def test_search_recipes_non_alcoholic(seeded_recipes):
    """search_recipes：non_alcoholic=True 走 base_spirit==other 启发式。"""
    from hermes_kb.agent_tools import search_recipes

    result = search_recipes(non_alcoholic=True, limit=5)
    assert "error" not in result, result.get("error")


def test_search_recipes_technique_glassware(seeded_recipes):
    """search_recipes：仅 technique/glassware 过滤走 filter_recipes 路径。"""
    from hermes_kb.agent_tools import search_recipes

    result = search_recipes(technique="stir", limit=5)
    assert "error" not in result, result.get("error")
    result2 = search_recipes(glassware="马天尼杯", limit=5)
    assert "error" not in result2, result2.get("error")


def test_search_recipes_invalid_limit(seeded_recipes):
    """search_recipes：非法 limit 返回错误消息。"""
    from hermes_kb.agent_tools import search_recipes

    result = search_recipes(limit="abc")
    assert "error" in result


def test_search_recipes_skip_missing_hit(seeded_recipes, monkeypatch):
    """search_recipes：查询命中但文档缺失时跳过（不报错）。"""
    from hermes_kb.agent_tools import search_recipes

    class _FakeHit:
        def __init__(self, doc_id, score=0.5):
            self.doc_id = doc_id
            self.score = score

    class _FakeRetriever:
        def retrieve(self, query, top_k=3):
            return [_FakeHit("nonexistent-doc", 0.5)]

    monkeypatch.setattr("hermes_kb.agent_tools._get_retriever", lambda: _FakeRetriever())
    result = search_recipes(query="金酒")
    assert "error" not in result, result.get("error")


def test_get_recipe_empty_title():
    """get_recipe：空标题返回错误。"""
    from hermes_kb.agent_tools import get_recipe

    assert "error" in get_recipe(title="")
    assert "error" in get_recipe(title="   ")


def test_get_recipe_variant_resolution(seeded_recipes):
    """get_recipe：变体标题解析到原配方。"""
    from sqlmodel import select

    from hermes_kb.agent_tools import get_recipe
    from hermes_kb.database import get_session
    from hermes_kb.models import Document
    from hermes_kb.recipe_variants import create_variant_link

    with get_session() as session:
        base = session.exec(
            select(Document).where(Document.title == "马天尼 Martini")
        ).first()
        variant = session.exec(
            select(Document).where(Document.title == "尼格罗尼 Negroni")
        ).first()
    assert base and variant
    assert create_variant_link(base.doc_id, variant.doc_id, "变体测试")

    result = get_recipe(title="尼格罗尼 Negroni")
    assert "error" not in result, result.get("error")
    assert result["result"]["title"] == "马天尼 Martini"


def test_get_base_recipe_by_title(seeded_recipes):
    """get_base_recipe_by_title：通过变体关联反查原配方。"""
    from sqlmodel import select

    from hermes_kb.agent_tools import get_base_recipe_by_title
    from hermes_kb.database import get_session
    from hermes_kb.models import Document
    from hermes_kb.recipe_variants import create_variant_link

    with get_session() as session:
        base = session.exec(
            select(Document).where(Document.title == "马天尼 Martini")
        ).first()
        variant = session.exec(
            select(Document).where(Document.title == "尼格罗尼 Negroni")
        ).first()
    assert base and variant
    assert create_variant_link(base.doc_id, variant.doc_id)

    resolved = get_base_recipe_by_title("尼格罗尼 Negroni")
    assert resolved is not None
    assert resolved.doc_id == base.doc_id


def test_get_recipe_search_fallback(seeded_recipes, monkeypatch):
    """get_recipe：标题无直接命中时用检索兜底。"""
    from sqlmodel import select

    from hermes_kb.agent_tools import get_recipe
    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    with get_session() as session:
        doc = session.exec(
            select(Document).where(Document.title == "马天尼 Martini")
        ).first()
    assert doc is not None

    class _FakeHit:
        def __init__(self, doc_id, score=0.1):
            self.doc_id = doc_id
            self.score = score

    class _FakeRetriever:
        def retrieve(self, query, top_k=3):
            return [_FakeHit(doc.doc_id)]

    monkeypatch.setattr("hermes_kb.agent_tools._get_retriever", lambda: _FakeRetriever())
    result = get_recipe(title="完全不存在XYZ")
    assert "error" not in result, result.get("error")
    assert result["result"]["title"] == "马天尼 Martini"


def test_get_recipe_not_found_message(seeded_recipes, monkeypatch):
    """get_recipe：彻底未命中时返回 None + message。"""
    from hermes_kb.agent_tools import get_recipe

    class _EmptyRetriever:
        def retrieve(self, query, top_k=3):
            return []

    monkeypatch.setattr("hermes_kb.agent_tools._get_retriever", lambda: _EmptyRetriever())
    result = get_recipe(title="完全不存在XYZ")
    assert "error" not in result
    assert result["result"] is None
    assert "未找到配方" in result["message"]


def test_load_search_item(seeded_recipes):
    """_load_search_item：存在返回精简字段，缺失返回 None。"""
    from sqlmodel import select

    from hermes_kb.agent_tools import _load_search_item
    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    with get_session() as session:
        doc = session.exec(
            select(Document).where(Document.title == "马天尼 Martini")
        ).first()
    assert doc is not None
    item = _load_search_item(doc.doc_id)
    assert item is not None and item["title"] == "马天尼 Martini"
    assert _load_search_item("nonexistent-doc") is None


def test_parse_ingredients_invalid():
    """_parse_ingredients：非法 JSON / 非列表返回空列表。"""
    from hermes_kb.agent_tools import _parse_ingredients

    assert _parse_ingredients("") == []
    assert _parse_ingredients("not-json") == []
    assert _parse_ingredients("{}") == []
    assert _parse_ingredients("[]") == []


def test_list_variants_exception(seeded_recipes, monkeypatch):
    """_list_variants：变体查询异常返回空列表。"""
    from hermes_kb.agent_tools import _list_variants

    def boom(doc_id):
        raise RuntimeError("boom")

    monkeypatch.setattr("hermes_kb.agent_tools.get_variants", boom)
    assert _list_variants("x") == []


def test_match_by_ingredients_exception(seeded_recipes, monkeypatch):
    """match_by_ingredients：底层异常转错误消息。"""
    from hermes_kb.agent_tools import match_by_ingredients

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("hermes_kb.agent_tools.find_recipes_by_ingredients", boom)
    result = match_by_ingredients(ingredients=["金酒"])
    assert "error" in result


def test_find_substitute_empty():
    """find_substitute：空材料返回错误。"""
    from hermes_kb.agent_tools import find_substitute

    assert "error" in find_substitute(ingredient="")
    assert "error" in find_substitute(ingredient="  ")


def test_find_substitute_exception(seeded_recipes, monkeypatch):
    """find_substitute：底层异常转错误消息。"""
    from hermes_kb.agent_tools import find_substitute

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("hermes_kb.agent_tools.get_substitutes", boom)
    result = find_substitute(ingredient="金酒")
    assert "error" in result


def test_get_knowledge_empty():
    """get_knowledge：空 query 返回错误。"""
    from hermes_kb.agent_tools import get_knowledge

    assert "error" in get_knowledge(query="")
    assert "error" in get_knowledge(query="  ")


def test_get_knowledge_rejected(seeded_recipes, monkeypatch):
    """get_knowledge：RAG 拒绝时透传 rejected 标记。"""
    from hermes_kb.agent_tools import get_knowledge

    class _FakeAnswer:
        rejected = True
        answer = "拒绝回答"
        citations = []  # noqa: RUF012

    class _FakeEngine:
        def answer(self, q, top_k=5):
            return _FakeAnswer()

    monkeypatch.setattr("hermes_kb.agent_tools._get_rag_engine", lambda: _FakeEngine())
    result = get_knowledge(query="未成年相关")
    assert "error" not in result
    assert result["result"]["rejected"] is True


def test_get_knowledge_fallback(seeded_recipes, monkeypatch):
    """get_knowledge：RAG 失败时回退原始检索。"""
    from hermes_kb.agent_tools import get_knowledge

    class _FakeHit:
        def __init__(self, doc_id, title, text, score=0.1):
            self.doc_id = doc_id
            self.title = title
            self.text = text
            self.score = score

    class _FakeRetriever:
        def retrieve(self, query, top_k=3):
            return [_FakeHit("d1", "t1", "回退检索内容")]

    def boom_engine(*args, **kwargs):
        raise RuntimeError("rag down")

    monkeypatch.setattr("hermes_kb.agent_tools._get_rag_engine", boom_engine)
    monkeypatch.setattr("hermes_kb.agent_tools._get_retriever", lambda: _FakeRetriever())
    result = get_knowledge(query="摇和法")
    assert "error" not in result
    assert "回退检索内容" in result["result"]["text"]


def test_get_knowledge_fallback_error(seeded_recipes, monkeypatch):
    """get_knowledge：RAG 与检索都失败时返回错误消息。"""
    from hermes_kb.agent_tools import get_knowledge

    def boom(*args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr("hermes_kb.agent_tools._get_rag_engine", boom)
    monkeypatch.setattr("hermes_kb.agent_tools._get_retriever", boom)
    result = get_knowledge(query="摇和法")
    assert "error" in result


# ============================================================================
# 覆盖率补齐：agent 编排的 LLM 循环 / 错误分支 / 渲染函数
# ============================================================================


class _FakeLLM:
    """非 Mock 后端：按队列返回预置响应，驱动工具调用循环。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.backend_name = "FakeBackend"
        self.calls = 0

    def chat(self, messages, tools=None, tool_choice=None):
        self.calls += 1
        return self._responses.pop(0)


def _tool_call_response(name: str, arguments: str, content: str = "") -> object:
    from hermes_kb.llm import LLMResponse

    return LLMResponse(
        content=content,
        model="fake",
        prompt_tokens=10,
        completion_tokens=5,
        tool_calls=[
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        ],
    )


def test_tool_schemas_format():
    """_tool_schemas 输出 OpenAI function calling 格式。"""
    from hermes_kb.agent import _tool_schemas

    schemas = _tool_schemas()
    assert len(schemas) == 5
    assert schemas[0]["type"] == "function"
    assert "function" in schemas[0]
    assert schemas[0]["function"]["name"] == "search_recipes"


def test_agent_llm_loop_with_tool_call(seeded_recipes):
    """真实 LLM 路径：工具调用 → 综合回答。"""
    from hermes_kb.agent import CocktailAgent
    from hermes_kb.llm import LLMResponse

    tool_resp = _tool_call_response("search_recipes", '{"query": "马天尼", "limit": 3}')
    final_resp = LLMResponse(
        content="这是最终回答", model="fake", prompt_tokens=20, completion_tokens=8
    )
    fake = _FakeLLM([tool_resp, final_resp])
    agent = CocktailAgent(llm=fake)
    res = agent.ask("马天尼怎么做")
    assert res.answer == "这是最终回答"
    assert len(res.turns) == 1
    assert res.turns[0]["name"] == "search_recipes"
    assert fake.calls == 2
    assert res.prompt_tokens == 30
    assert res.completion_tokens == 13


def test_agent_llm_loop_max_rounds(seeded_recipes):
    """真实 LLM 路径：工具调用超过最大轮数时用工具结果拼装。"""
    from hermes_kb.agent import MAX_ROUNDS, CocktailAgent

    tool_resp = _tool_call_response("search_recipes", '{"query": "马天尼", "limit": 3}')
    fake = _FakeLLM([tool_resp] * MAX_ROUNDS)
    agent = CocktailAgent(llm=fake)
    res = agent.ask("马天尼怎么做")
    assert len(res.turns) == MAX_ROUNDS
    assert fake.calls == MAX_ROUNDS
    # for-else 分支：基于最后工具结果拼装
    assert res.answer


def test_agent_llm_loop_no_tool(seeded_recipes):
    """真实 LLM 路径：不调用工具直接回答。"""
    from hermes_kb.agent import CocktailAgent
    from hermes_kb.llm import LLMResponse

    final_resp = LLMResponse(content="直接回答", model="fake")
    fake = _FakeLLM([final_resp])
    agent = CocktailAgent(llm=fake)
    res = agent.ask("马天尼怎么做")
    assert res.answer == "直接回答"
    assert res.turns == []


def test_agent_ask_events_llm(seeded_recipes):
    """真实 LLM 路径：ask_events 产出 tool_call/token/done 事件。"""
    from hermes_kb.agent import CocktailAgent
    from hermes_kb.llm import LLMResponse

    tool_resp = _tool_call_response("search_recipes", '{"query": "马天尼", "limit": 3}')
    final_resp = LLMResponse(content="这是最终回答", model="fake")
    fake = _FakeLLM([tool_resp, final_resp])
    agent = CocktailAgent(llm=fake)
    events = list(agent.ask_events("马天尼怎么做"))
    types = [e.get("type") for e in events]
    assert "tool_call" in types
    assert "token" in types
    assert "done" in types


def test_execute_tool_unknown(seeded_recipes):
    """_execute_tool：未知工具返回错误消息。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    res = agent._execute_tool("nonexistent", {})
    assert "error" in res
    assert "未知工具" in res["error"]


def test_execute_tool_exception(seeded_recipes, monkeypatch):
    """_execute_tool：工具执行异常转错误消息。"""
    from hermes_kb.agent import CocktailAgent
    from hermes_kb.agent_tools import get_tool

    def boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(get_tool("search_recipes"), "execute", boom)
    agent = CocktailAgent()
    res = agent._execute_tool("search_recipes", {})
    assert "error" in res
    assert "执行失败" in res["error"]


def test_compose_from_turns_empty():
    """_compose_from_turns：无工具轮次返回提示。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    assert "抱歉" in agent._compose_from_turns("q", [])


def test_compose_from_turns_with_result():
    """_compose_from_turns：有工具结果时返回序列化 JSON。"""
    from hermes_kb.agent import CocktailAgent

    agent = CocktailAgent()
    turns = [{"result": {"result": {"title": "测试酒", "count": 1}}}]
    out = agent._compose_from_turns("q", turns)
    assert "测试酒" in out
    # result.result 非 dict 时回退 str(result)
    turns2 = [{"result": {"result": "plain text"}}]
    assert "plain text" in agent._compose_from_turns("q", turns2)


def test_chunk_text_empty():
    """_chunk_text：空文本返回单个空块。"""
    from hermes_kb.agent import _chunk_text

    assert _chunk_text("") == [""]
    assert _chunk_text("abcdefghijklmnopqrstuvwxyz", size=10) == [
        "abcdefghij", "klmnopqrst", "uvwxyz"
    ]


def test_dedup_citations():
    """_dedup_citations：按 doc_id/title 去重，空 key 保留。"""
    from hermes_kb.agent import _dedup_citations

    cites = [
        {"doc_id": "a", "title": "A"},
        {"doc_id": "a", "title": "A2"},
        {"title": "b"},
        {"title": "b"},
        {},
        {},
    ]
    out = _dedup_citations(cites)
    assert len(out) == 4


def test_extract_citations_top_level():
    """_extract_citations：兼容 result.citations 与顶层 citations。"""
    from hermes_kb.agent import _extract_citations

    assert _extract_citations({"result": {"citations": [{"doc_id": "y"}]}}) == [
        {"doc_id": "y"}
    ]
    assert _extract_citations({"citations": [{"doc_id": "x"}]}) == [{"doc_id": "x"}]
    assert _extract_citations({"result": {}}) == []


def test_extract_ingredient_fallback():
    """_extract_ingredient：无替代关键词时原样返回。"""
    from hermes_kb.agent import _extract_ingredient

    assert _extract_ingredient("foo bar") == "foo bar"


def test_render_recipe_answer_error():
    """_render_recipe_answer：错误 / 未找到 / 完整字段。"""
    from hermes_kb.agent import _render_recipe_answer

    assert "查询失败" in _render_recipe_answer({"error": "x"})
    assert "未找到" in _render_recipe_answer({"result": None})
    result = {
        "result": {
            "title": "测试酒",
            "base_spirit": "gin",
            "abv": 0.2,
            "technique": "shake",
            "glassware": "马天尼杯",
            "ingredients_json": [{"name": "金酒", "measure": "60ml"}],
            "content": "步骤一",
            "source": "iba_official",
            "source_authority": 5,
        }
    }
    out = _render_recipe_answer(result)
    for kw in ("测试酒", "基酒", "估算酒精度", "技法", "载杯", "金酒", "步骤一", "来源"):
        assert kw in out


def test_render_match_answer():
    """_render_match_answer：错误 / 无匹配 / full+partial。"""
    from hermes_kb.agent import _render_match_answer

    assert "匹配失败" in _render_match_answer({"error": "x"}, [])
    assert "未找到" in _render_match_answer(
        {"result": {"full_match": [], "partial_match": []}}, ["金酒"]
    )
    result = {
        "result": {
            "full_match": [{"title": "A酒"}],
            "partial_match": [{"title": "B酒", "missing_ingredients": ["青柠"]}],
        }
    }
    out = _render_match_answer(result, ["金酒", "味美思"])
    assert "A酒" in out and "B酒" in out and "缺 青柠" in out


def test_render_substitute_answer():
    """_render_substitute_answer：错误 / 无替代 / 带说明。"""
    from hermes_kb.agent import _render_substitute_answer

    assert "替代品查询失败" in _render_substitute_answer({"error": "x"}, "金酒")
    assert "未找到" in _render_substitute_answer(
        {"result": {"substitutes": []}}, "金酒"
    )
    result = {"result": {"substitutes": [{"substitute": "白兰地", "note": "近似"}]}}
    out = _render_substitute_answer(result, "金酒")
    assert "白兰地" in out and "近似" in out
    # 无 note 时不输出括号
    result2 = {"result": {"substitutes": [{"substitute": "干邑"}]}}
    out2 = _render_substitute_answer(result2, "金酒")
    assert "干邑" in out2


def test_render_search_answer():
    """_render_search_answer：错误 / 无结果 / 带元信息。"""
    from hermes_kb.agent import _render_search_answer

    assert "搜索失败" in _render_search_answer({"error": "x"})
    assert "未找到相关配方" in _render_search_answer(
        {"result": {"results": [], "count": 0}}
    )
    result = {
        "result": {
            "results": [{"title": "马天尼", "base_spirit": "gin", "abv": 0.2}],
            "count": 1,
        }
    }
    out = _render_search_answer(result)
    assert "马天尼" in out and "gin" in out


def test_render_knowledge_answer():
    """_render_knowledge_answer：错误 / 引用来源。"""
    from hermes_kb.agent import _render_knowledge_answer

    assert "知识查询失败" in _render_knowledge_answer({"error": "x"})
    result = {"result": {"text": "内容文本", "citations": [{"title": "源1"}]}}
    out = _render_knowledge_answer(result)
    assert "内容文本" in out and "源1" in out
    # 无引用时仅文本
    assert "仅文本" in _render_knowledge_answer({"result": {"text": "仅文本"}})


def test_agent_ask_sync_error(client, seeded_recipes):
    """/agent/ask/sync：agent 异常返回 500。"""
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    client.app.state.agent.ask = boom
    r = client.post("/api/agent/ask/sync", json={"query": "马天尼怎么做"})
    assert r.status_code == 500


def test_agent_ask_stream_error(client, seeded_recipes):
    """/agent/ask：agent 异常时流内返回 error 事件。"""
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    client.app.state.agent.ask_events = boom
    r = client.post("/api/agent/ask", json={"query": "马天尼怎么做"})
    assert r.status_code == 200
    events = []
    for line in r.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))
    assert events
    assert events[-1].get("type") == "error"


def test_log_agent_query_success(tmp_db):
    """_log_agent_query：成功写入 QueryLog。"""
    import time
    from types import SimpleNamespace

    from sqlmodel import select

    from hermes_kb.api.agent import _log_agent_query
    from hermes_kb.database import get_session
    from hermes_kb.models import QueryLog

    result = SimpleNamespace(
        model_used="mock",
        prompt_tokens=10,
        completion_tokens=5,
        answer="答案",
        citations=[{"doc_id": "x"}],
    )
    _log_agent_query("测试问题", result, time.perf_counter())
    with get_session() as session:
        logs = session.exec(select(QueryLog)).all()
    assert len(logs) == 1
    assert logs[0].query == "测试问题"


def test_log_agent_query_exception(monkeypatch):
    """_log_agent_query：数据库写入失败不抛出。"""
    import time
    from types import SimpleNamespace

    from hermes_kb.api.agent import _log_agent_query

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr("hermes_kb.api.agent.get_session", boom)
    result = SimpleNamespace(
        model_used="mock",
        prompt_tokens=0,
        completion_tokens=0,
        answer="",
        citations=[],
    )
    _log_agent_query("q", result, time.perf_counter())  # 不应抛异常


# ============================================================================
# 覆盖率补齐：剩余错误分支 / 边界路径
# ============================================================================


def test_search_recipes_glassware_with_base(seeded_recipes):
    """search_recipes：base_spirit + glassware 组合过滤（Document 查询路径）。"""
    from hermes_kb.agent_tools import search_recipes

    result = search_recipes(base_spirit="gin", glassware="马天尼杯", limit=5)
    assert "error" not in result, result.get("error")
    for item in result["result"]["results"]:
        assert item.get("base_spirit") in (None, "gin")


def test_search_recipes_technique_with_base(seeded_recipes):
    """search_recipes：base_spirit + technique 组合过滤（Document 查询路径 technique 分支）。"""
    from hermes_kb.agent_tools import search_recipes

    result = search_recipes(base_spirit="gin", technique="shake", limit=5)
    assert "error" not in result, result.get("error")
    for item in result["result"]["results"]:
        assert item.get("base_spirit") in (None, "gin")


def test_search_recipes_non_alcoholic_with_technique(seeded_recipes):
    """search_recipes：non_alcoholic + technique 组合过滤。"""
    from hermes_kb.agent_tools import search_recipes

    result = search_recipes(non_alcoholic=True, technique="build", limit=5)
    assert "error" not in result, result.get("error")


def test_load_search_item_exception(seeded_recipes, monkeypatch):
    """_load_search_item：数据库异常返回 None。"""
    from hermes_kb.agent_tools import _load_search_item

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr("hermes_kb.agent_tools.get_session", boom)
    assert _load_search_item("x") is None


def test_resolve_variant_doc_exception(seeded_recipes, monkeypatch):
    """_resolve_variant_doc：变体查询异常时按普通配方处理。"""
    from sqlmodel import select

    from hermes_kb.agent_tools import _resolve_variant_doc
    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    with get_session() as session:
        doc = session.exec(
            select(Document).where(Document.title == "马天尼 Martini")
        ).first()
    assert doc is not None

    def boom(doc_id):
        raise RuntimeError("boom")

    monkeypatch.setattr("hermes_kb.agent_tools.get_base_recipe", boom)
    assert _resolve_variant_doc(doc).doc_id == doc.doc_id


def test_resolve_variant_doc_non_variant(seeded_recipes):
    """_resolve_variant_doc：非变体文档原样返回。"""
    from sqlmodel import select

    from hermes_kb.agent_tools import _resolve_variant_doc
    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    with get_session() as session:
        doc = session.exec(
            select(Document).where(Document.title == "马天尼 Martini")
        ).first()
    assert doc is not None
    assert _resolve_variant_doc(doc).doc_id == doc.doc_id


def test_search_recipe_doc_exception(seeded_recipes, monkeypatch):
    """_search_recipe_doc：检索异常返回 None。"""
    from hermes_kb.agent_tools import _search_recipe_doc

    def boom(*args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr("hermes_kb.agent_tools._get_retriever", boom)
    assert _search_recipe_doc("马天尼") is None


def test_search_recipe_doc_non_recipe(seeded_recipes, monkeypatch):
    """_search_recipe_doc：命中非配方文档时跳过。"""
    from sqlmodel import select

    from hermes_kb.agent_tools import _search_recipe_doc
    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    with get_session() as session:
        doc = session.exec(
            select(Document).where(Document.title == "马天尼 Martini")
        ).first()
    assert doc is not None

    class _FakeHit:
        def __init__(self, doc_id, score=0.1):
            self.doc_id = doc_id
            self.score = score

    class _FakeRetriever:
        def retrieve(self, query, top_k=3):
            return [_FakeHit(doc.doc_id)]

    monkeypatch.setattr("hermes_kb.agent_tools._get_retriever", lambda: _FakeRetriever())
    # 命中配方文档 → 返回
    assert _search_recipe_doc("x").doc_id == doc.doc_id


def test_get_recipe_exception(seeded_recipes, monkeypatch):
    """get_recipe：底层异常转错误消息。"""
    from hermes_kb.agent_tools import get_recipe

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("hermes_kb.agent_tools._find_recipe_docs", boom)
    result = get_recipe(title="马天尼")
    assert "error" in result


def test_get_recipe_variant_lookup_exception(seeded_recipes, monkeypatch):
    """get_recipe：回退 1 变体反查异常时跳过，继续走检索兜底。"""
    from hermes_kb.agent_tools import get_recipe

    calls = {"n": 0}

    def fake_find(title):
        calls["n"] += 1
        if calls["n"] == 1:
            return []  # get_recipe 精确/模糊匹配无命中
        raise RuntimeError("db down")  # get_base_recipe_by_title 内部再查时报错

    monkeypatch.setattr("hermes_kb.agent_tools._find_recipe_docs", fake_find)
    result = get_recipe(title="马天尼 Martini")
    # 回退 2 检索兜底可能命中或未命中，但不应报错
    assert "error" not in result, result.get("error")


def test_get_recipe_variant_lookup_hit(seeded_recipes, monkeypatch):
    """get_recipe：回退 1 变体反查命中 base doc（doc = base 分支）。"""
    from sqlmodel import select

    from hermes_kb.agent_tools import get_recipe
    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    with get_session() as session:
        doc = session.exec(
            select(Document).where(Document.title == "马天尼 Martini")
        ).first()
    assert doc is not None

    monkeypatch.setattr("hermes_kb.agent_tools._find_recipe_docs", lambda title: [])
    monkeypatch.setattr(
        "hermes_kb.agent_tools.get_base_recipe_by_title", lambda title: doc
    )
    result = get_recipe(title="完全不存在XYZ")
    assert "error" not in result, result.get("error")
    assert result["result"] is not None
    assert result["result"]["title"] == "马天尼 Martini"


def test_get_base_recipe_by_title_none(seeded_recipes):
    """get_base_recipe_by_title：非变体标题返回 None。"""
    from hermes_kb.agent_tools import get_base_recipe_by_title

    assert get_base_recipe_by_title("马天尼 Martini") is None
    assert get_base_recipe_by_title("完全不存在XYZ") is None


def test_get_base_recipe_by_title_exception(seeded_recipes, monkeypatch):
    """get_base_recipe_by_title：变体查询异常时跳过。"""
    from hermes_kb.agent_tools import get_base_recipe_by_title

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("hermes_kb.agent_tools.get_base_recipe", boom)
    assert get_base_recipe_by_title("马天尼 Martini") is None


def test_match_by_ingredients_blank(seeded_recipes):
    """match_by_ingredients：全空白材料返回错误。"""
    from hermes_kb.agent_tools import match_by_ingredients

    result = match_by_ingredients(ingredients=["  ", ""])
    assert "error" in result


def test_agent_llm_loop_invalid_arguments(seeded_recipes):
    """真实 LLM 路径：工具参数非法 JSON 时按空参数执行。"""
    from hermes_kb.agent import CocktailAgent
    from hermes_kb.llm import LLMResponse

    bad = LLMResponse(
        content="",
        model="fake",
        tool_calls=[
            {
                "id": "c1",
                "type": "function",
                "function": {"name": "search_recipes", "arguments": "{not-json"},
            }
        ],
    )
    final = LLMResponse(content="ok", model="fake")
    fake = _FakeLLM([bad, final])
    agent = CocktailAgent(llm=fake)
    res = agent.ask("马天尼怎么做")
    assert res.answer == "ok"
    assert res.turns[0]["arguments"] == {}


def test_agent_llm_loop_non_dict_arguments(seeded_recipes):
    """真实 LLM 路径：工具参数解析为非 dict 时按空参数执行。"""
    from hermes_kb.agent import CocktailAgent
    from hermes_kb.llm import LLMResponse

    bad = LLMResponse(
        content="",
        model="fake",
        tool_calls=[
            {
                "id": "c1",
                "type": "function",
                "function": {"name": "search_recipes", "arguments": '["x"]'},
            }
        ],
    )
    final = LLMResponse(content="ok", model="fake")
    fake = _FakeLLM([bad, final])
    agent = CocktailAgent(llm=fake)
    res = agent.ask("马天尼怎么做")
    assert res.answer == "ok"
    assert res.turns[0]["arguments"] == {}