"""P1 翻译服务测试。"""
from __future__ import annotations

from hermes_kb.translation import _mock_translate, translate_title, batch_translate_titles
from hermes_kb.models import Document
from hermes_kb.database import get_session


def test_mock_translate_known():
    """常用鸡尾酒名能翻译。"""
    assert _mock_translate("Mojito") == "莫吉托"
    assert _mock_translate("MARGARITA") == "玛格丽特"
    assert _mock_translate("Old Fashioned") == "古典鸡尾酒"


def test_mock_translate_unknown_keeps_original():
    """未知鸡尾酒名保留原文。"""
    assert _mock_translate("Some Random Drink") == "Some Random Drink"


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
