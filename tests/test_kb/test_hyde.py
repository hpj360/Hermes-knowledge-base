"""HyDE（假设文档生成）单元测试。

覆盖 hermes_kb.hyde：
- _heuristic_hyde：关键词模板匹配 / 通用模板 / 空 query
- HyDEGenerator：enable/disable、LLM 可用/不可用、超时降级、异常降级
- _llm_generate：正常返回 / 空返回
"""

from __future__ import annotations

import time

from hermes_kb.config import override_settings


# ---------------------------------------------------------------------------
# _heuristic_hyde
# ---------------------------------------------------------------------------
def test_heuristic_hyde_empty_query():
    from hermes_kb.hyde import _heuristic_hyde

    assert _heuristic_hyde("") == ""
    # 纯空白非空：不抛异常，返回通用模板（含原 query）
    result = _heuristic_hyde("   ")
    assert "这是一篇关于酒类知识的百科文章" in result


def test_heuristic_hyde_matches_keyword():
    from hermes_kb.hyde import _heuristic_hyde

    result = _heuristic_hyde("金酒的风味")
    assert result.startswith("金酒的风味。")
    # 命中金酒模板
    assert "杜松子" in result


def test_heuristic_hyde_matches_multiple_keywords():
    from hermes_kb.hyde import _heuristic_hyde

    result = _heuristic_hyde("金酒和威士忌哪个烈")
    assert "杜松子" in result  # 金酒模板
    assert "威士忌（Whisky）" in result  # 威士忌模板


def test_heuristic_hyde_no_match_uses_generic():
    from hermes_kb.hyde import _heuristic_hyde

    result = _heuristic_hyde("如何调制鸡尾酒")
    assert result.startswith("如何调制鸡尾酒。")
    assert "这是一篇关于酒类知识的百科文章" in result


def test_heuristic_hyde_keeps_query_semantics():
    from hermes_kb.hyde import _heuristic_hyde

    query = "龙舌兰日出怎么做"
    result = _heuristic_hyde(query)
    assert result.startswith(query)


# ---------------------------------------------------------------------------
# HyDEGenerator：构造
# ---------------------------------------------------------------------------
def test_generator_init_uses_default_llm():
    from hermes_kb.hyde import HyDEGenerator
    from hermes_kb.llm import LLMClient

    override_settings(hyde_enabled=False)
    gen = HyDEGenerator()
    assert isinstance(gen.llm, LLMClient)
    assert gen.enabled is False  # hyde_enabled=False 时关闭


def test_generator_init_custom_llm():
    from hermes_kb.hyde import HyDEGenerator

    class _FakeLLM:
        def chat(self, messages):
            return type("R", (), {"content": "假设文档"})()

    gen = HyDEGenerator(llm_client=_FakeLLM())
    assert gen.llm is not None


# ---------------------------------------------------------------------------
# HyDEGenerator：generate 分支
# ---------------------------------------------------------------------------
def test_generate_empty_query():
    from hermes_kb.hyde import HyDEGenerator

    gen = HyDEGenerator()
    assert gen.generate("") == ""
    assert gen.generate("   ") == "   "


def test_generate_disabled_returns_query():
    from hermes_kb.hyde import HyDEGenerator

    override_settings(hyde_enabled=False)
    gen = HyDEGenerator()
    assert gen.enabled is False
    assert gen.generate("金酒的风味") == "金酒的风味"


def test_generate_llm_unavailable_uses_heuristic():
    from hermes_kb.hyde import HyDEGenerator

    override_settings(hyde_enabled=True, llm_provider="mock", llm_api_key="")
    gen = HyDEGenerator()
    result = gen.generate("金酒的风味")
    assert "杜松子" in result  # 启发式命中模板


def test_generate_llm_available_success():
    from hermes_kb.hyde import HyDEGenerator

    class _FakeLLM:
        def chat(self, messages):
            return type("R", (), {"content": "  金酒以杜松子为香料。  "})()

    override_settings(hyde_enabled=True, llm_provider="openai", llm_api_key="test-key")
    gen = HyDEGenerator(llm_client=_FakeLLM())
    result = gen.generate("金酒是什么")
    assert result == "金酒以杜松子为香料。"  # 去除首尾空白


def test_generate_llm_returns_empty_falls_back():
    """LLM 返回空 → 回退启发式。"""
    from hermes_kb.hyde import HyDEGenerator

    class _FakeLLM:
        def chat(self, messages):
            return type("R", (), {"content": ""})()

    override_settings(hyde_enabled=True, llm_provider="openai", llm_api_key="test-key")
    gen = HyDEGenerator(llm_client=_FakeLLM())
    result = gen.generate("金酒是什么")
    assert "杜松子" in result


def test_generate_llm_timeout_falls_back(monkeypatch):
    """LLM 超时 → 回退启发式（不阻塞）。"""
    import hermes_kb.hyde as hyde_mod
    from hermes_kb.hyde import HyDEGenerator

    class _SlowLLM:
        def chat(self, messages):
            time.sleep(0.2)
            return type("R", (), {"content": "慢响应"})()

    monkeypatch.setattr(hyde_mod, "_HYDE_TIMEOUT_SEC", 0.05)
    override_settings(hyde_enabled=True, llm_provider="openai", llm_api_key="test-key")
    gen = HyDEGenerator(llm_client=_SlowLLM())
    result = gen.generate("金酒是什么")
    assert "杜松子" in result  # 超时后回退启发式


def test_generate_llm_exception_falls_back():
    """LLM 抛异常 → 回退启发式。"""
    from hermes_kb.hyde import HyDEGenerator

    class _BoomLLM:
        def chat(self, messages):
            raise RuntimeError("llm down")

    override_settings(hyde_enabled=True, llm_provider="openai", llm_api_key="test-key")
    gen = HyDEGenerator(llm_client=_BoomLLM())
    result = gen.generate("威士忌的产地")
    assert "威士忌（Whisky）" in result


# ---------------------------------------------------------------------------
# HyDEGenerator：_llm_generate
# ---------------------------------------------------------------------------
def test_llm_generate_passes_system_prompt():
    from hermes_kb.hyde import HyDEGenerator

    captured: list[list[dict]] = []

    class _CaptureLLM:
        def chat(self, messages):
            captured.append(messages)
            return type("R", (), {"content": "  假设文档内容  "})()

    override_settings(hyde_enabled=True, llm_provider="openai", llm_api_key="test-key")
    gen = HyDEGenerator(llm_client=_CaptureLLM())
    result = gen._llm_generate("龙舌兰是什么")
    assert result == "假设文档内容"
    assert len(captured) == 1
    roles = [m["role"] for m in captured[0]]
    assert roles == ["system", "user"]
    assert "龙舌兰" in captured[0][1]["content"]
