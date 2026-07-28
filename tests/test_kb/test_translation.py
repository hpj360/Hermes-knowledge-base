"""P1 翻译服务测试。"""
from __future__ import annotations

import pytest

from hermes_kb.database import get_session
from hermes_kb.models import Document
from hermes_kb.translation import (
    _COMMON_TRANSLATIONS,
    _mock_translate,
    batch_translate_titles,
    translate_title,
)


def test_mock_translate_known():
    """常用鸡尾酒名能翻译。"""
    assert _mock_translate("Mojito") == "莫吉托"
    assert _mock_translate("MARGARITA") == "玛格丽特"
    assert _mock_translate("Old Fashioned") == "古典鸡尾酒"


def test_mock_translate_unknown_keeps_original():
    """未知鸡尾酒名保留原文。"""
    assert _mock_translate("Some Random Drink") == "Some Random Drink"


def test_mock_translate_fuzzy_substring_match():
    """模糊子串匹配：'spiced margarita' 命中 'margarita'。"""
    # 'margarita' 是 _COMMON_TRANSLATIONS 的 key，'spiced margarita' 不是
    # 但 fuzzy 分支会匹配 'margarita' in 'spiced margarita'
    assert _mock_translate("Spiced Margarita") == "玛格丽特"
    # 'mojito' 是 key，'spiced mojito' 不是，fuzzy 匹配 'mojito' in 'spiced mojito'
    assert _mock_translate("Spiced Mojito") == "莫吉托"


def test_translate_title_cjk_skip():
    """已含中文的标题跳过翻译。"""
    assert translate_title("莫吉托") == "莫吉托"
    assert translate_title("长岛冰茶") == "长岛冰茶"


def test_translate_title_empty():
    """空字符串安全处理。"""
    assert translate_title("") == ""
    assert translate_title("   ") == "   "


def test_translate_title_mock_backend():
    """Mock 后端翻译。"""
    result = translate_title("Negroni")
    assert result == "尼格罗尼"


def test_translate_title_real_llm_backend_success():
    """非 Mock 后端：自定义 llm_client.chat() 返回译名。"""

    class FakeLLMResponse:
        def __init__(self, content: str) -> None:
            self.content = content

    class FakeLLMClient:
        backend_name = "OpenAICompatBackend"

        def chat(self, messages):
            # 验证 messages 结构
            assert messages[0]["role"] == "system"
            assert "翻译" in messages[1]["content"]
            return FakeLLMResponse("莫吉托")

    result = translate_title("Mojito", llm_client=FakeLLMClient())
    assert result == "莫吉托"


def test_translate_title_real_llm_backend_strips_quotes():
    """非 Mock 后端：译名带引号时被剥离。"""

    class FakeLLMResponse:
        def __init__(self, content: str) -> None:
            self.content = content

    class FakeLLMClient:
        backend_name = "OpenAICompatBackend"

        def chat(self, messages):
            # 模拟 LLM 输出带多余引号
            return FakeLLMResponse('"玛格丽特"')

    result = translate_title("Margarita", llm_client=FakeLLMClient())
    assert result == "玛格丽特"


def test_translate_title_real_llm_backend_empty_response_returns_original():
    """非 Mock 后端：译名为空时返回原标题（不回退 mock）。"""

    class FakeLLMResponse:
        def __init__(self, content: str) -> None:
            self.content = content

    class FakeLLMClient:
        backend_name = "OpenAICompatBackend"

        def chat(self, messages):
            return FakeLLMResponse("   ")  # 空白

    result = translate_title("Negroni", llm_client=FakeLLMClient())
    # LLM 返回空 → 返回原标题（不回退 mock，行为见 translation.py:124）
    assert result == "Negroni"


def test_translate_title_llm_exception_fallback_to_mock():
    """非 Mock 后端：chat 抛异常时回退到 _mock_translate。"""

    class FakeLLMClient:
        backend_name = "OpenAICompatBackend"

        def chat(self, messages):
            raise RuntimeError("LLM service down")

    # 不应抛异常，回退到 mock 翻译
    result = translate_title("Negroni", llm_client=FakeLLMClient())
    assert result == "尼格罗尼"


def test_batch_translate_updates_db(tmp_db):
    """批量翻译更新数据库标题。"""
    with get_session() as session:
        doc = Document(
            title="Mojito",
            content="test",
            category="recipe",
            source="iba",
        )
        session.add(doc)
        session.commit()
        doc_id = doc.doc_id

    result = batch_translate_titles(source="iba", limit=10)
    assert result["translated"] >= 1
    assert result["model_used"] == "MockLLMBackend"

    with get_session() as session:
        updated = session.get(Document, doc_id)
        assert updated.title == "莫吉托"


def test_batch_translate_skips_cjk(tmp_db):
    """已含中文的配方跳过。"""
    with get_session() as session:
        doc = Document(
            title="莫吉托",
            content="test",
            category="recipe",
            source="iba",
        )
        session.add(doc)
        session.commit()

    result = batch_translate_titles(source="iba", limit=10)
    assert result["translated"] == 0
    assert result["skipped"] >= 1


def test_batch_translate_with_doc_ids_filter(tmp_db):
    """doc_ids 过滤：只翻译指定文档。"""
    with get_session() as session:
        doc1 = Document(title="Mojito", content="t", category="recipe", source="iba")
        doc2 = Document(title="Negroni", content="t", category="recipe", source="iba")
        session.add(doc1)
        session.add(doc2)
        session.commit()
        doc1_id = doc1.doc_id
        doc2_id = doc2.doc_id

    # 只翻译 doc1
    result = batch_translate_titles(doc_ids=[doc1_id], limit=10)
    assert result["translated"] == 1

    with get_session() as session:
        d1 = session.get(Document, doc1_id)
        d2 = session.get(Document, doc2_id)
        assert d1.title == "莫吉托"
        # doc2 未被翻译
        assert d2.title == "Negroni"


def test_batch_translate_skips_unknown_no_translation(tmp_db):
    """未知鸡尾酒名（mock 兜底返回原文）应被 skipped。"""
    with get_session() as session:
        # 'Foobar Baz' 不在 mock 字典中，translate_title 会返回原文
        doc = Document(
            title="Foobar Baz",
            content="test",
            category="recipe",
            source="iba",
        )
        session.add(doc)
        session.commit()

    result = batch_translate_titles(source="iba", limit=10)
    assert result["translated"] == 0
    assert result["skipped"] >= 1


def test_batch_translate_failed_records_error(tmp_db, monkeypatch):
    """translate_title 抛异常时记 failed，不影响其他文档。"""
    with get_session() as session:
        doc = Document(
            title="Mojito",
            content="test",
            category="recipe",
            source="iba",
        )
        session.add(doc)
        session.commit()

    # 让 translate_title 抛异常（在 batch 内的 try/except 捕获）
    import hermes_kb.translation as tr_mod

    def boom(title, llm_client=None):
        raise RuntimeError("translate boom")

    monkeypatch.setattr(tr_mod, "translate_title", boom)

    result = batch_translate_titles(source="iba", limit=10)
    assert result["failed"] >= 1
    assert result["translated"] == 0


# ============================================================
# Task 1: 标题中文化字典扩展测试
# ============================================================


def test_title_dict_size():
    """字典规模至少 200 条。"""
    assert len(_COMMON_TRANSLATIONS) >= 200


@pytest.mark.parametrize(
    "english,expected",
    [
        ("Margarita", "玛格丽特"),
        ("Old Fashioned", "古典鸡尾酒"),
        ("Cosmopolitan", "大都会"),
        ("White Lady", "白色佳人"),
        ("Boulevardier", "林荫道"),
        ("Singapore Sling", "新加坡司令"),
        ("Mint Julep", "薄荷茱莉普"),
        ("Paper Plane", "纸飞机"),
        ("Amaretto Sour", "杏仁酸"),
        ("Blue Hawaiian", "蓝色夏威夷"),
    ],
)
def test_sample_translations(english, expected):
    """抽样验证 10 条标题翻译正确性（含原有与新增映射）。"""
    assert translate_title(english) == expected


def test_unmapped_title_returns_original():
    """未命中字典的标题返回英文原值。"""
    original = "Totally Fictional Concoction XYZ123"
    assert translate_title(original) == original


def test_no_duplicate_values():
    """所有中文值唯一，避免一词多译。"""
    values = list(_COMMON_TRANSLATIONS.values())
    assert len(values) == len(set(values)), "存在重复的中文值"
