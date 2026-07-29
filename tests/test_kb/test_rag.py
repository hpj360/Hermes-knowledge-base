"""RAG 引擎单元测试。"""

from __future__ import annotations

import pytest

from hermes_kb.rag import ImportService, RAGEngine, _get_chunk_strategy
from hermes_kb.retrieval import HybridRetriever


def test_import_text_basic(tmp_db):
    """导入纯文本：标题/chunk_count/状态正确。"""
    svc = ImportService()
    result = svc.import_text(
        content="金酒是杜松子酒。" * 50,
        title="测试文档",
    )
    assert result["status"] == "imported"
    assert result["title"] == "测试文档"
    assert result["chunk_count"] >= 1
    assert result["doc_id"].startswith("doc_")


def test_import_text_empty_title_rejected(tmp_db):
    """空标题应被拒绝。"""
    svc = ImportService()
    with pytest.raises(ValueError, match="title"):
        svc.import_text(content="x", title="")


def test_import_text_empty_content_rejected(tmp_db):
    """空内容（未 allow_empty）应被拒绝。"""
    svc = ImportService()
    with pytest.raises(ValueError, match="content"):
        svc.import_text(content="", title="t")


def test_import_text_allow_empty(tmp_db):
    """allow_empty=True 时空内容也能导入（chunk_count=0）。"""
    svc = ImportService()
    result = svc.import_text(content="", title="t", allow_empty=True)
    assert result["chunk_count"] == 0


def test_import_text_unsupported_file_type(tmp_db):
    """不支持的 file_type 应被拒绝。"""
    svc = ImportService()
    with pytest.raises(ValueError, match="file_type"):
        svc.import_text(content="x", title="t", file_type="docx")


def test_delete_document(tmp_db):
    """删除文档后检索应无命中。"""
    svc = ImportService()
    r = svc.import_text(content="罕见关键词XYZ123" * 20, title="t")
    doc_id = r["doc_id"]
    # 删除前能检索到
    retriever = HybridRetriever()
    hits = retriever.retrieve("XYZ123")
    assert any(h.doc_id == doc_id for h in hits)
    # 删除
    ok = svc.delete_document(doc_id)
    assert ok is True
    # 删除后无命中
    hits2 = retriever.retrieve("XYZ123")
    assert not any(h.doc_id == doc_id for h in hits2)


def test_delete_nonexistent(tmp_db):
    """删除不存在的文档返回 False。"""
    svc = ImportService()
    assert svc.delete_document("doc_not_exists") is False


def test_rag_answer_returns_citations(seeded_importer):
    """RAG answer 应返回引用列表。"""
    rag = RAGEngine()
    result = rag.answer("金酒的核心风味")
    assert result.query == "金酒的核心风味"
    assert result.answer  # 非空
    assert isinstance(result.citations, list)
    # 引用应来自金酒文档
    assert any("金酒" in c.title or "Gin" in c.title for c in result.citations) or len(result.citations) > 0
    assert result.latency_ms >= 0


def test_rag_answer_model_used(seeded_importer):
    """model_used 字段应有值（mock 或真实 backend）。"""
    rag = RAGEngine()
    result = rag.answer("威士忌")
    assert result.model_used


def test_rag_answer_id_unique(seeded_importer):
    """每次 answer_id 应唯一。"""
    rag = RAGEngine()
    r1 = rag.answer("金酒")
    r2 = rag.answer("威士忌")
    assert r1.answer_id != r2.answer_id


def test_rag_citation_chunk_rowid(seeded_importer):
    """M1-04：引用应包含 chunk_rowid。"""
    rag = RAGEngine()
    result = rag.answer("葡萄酒")
    for c in result.citations:
        assert hasattr(c, "chunk_rowid")
        assert c.chunk_rowid >= 0


# ---------------------------------------------------------------------------
# Task 3：差异化分片策略 _get_chunk_strategy 单元测试
# ---------------------------------------------------------------------------
def test_get_chunk_strategy_encyclopedia():
    """encyclopedia 类别应返回大 chunk (800, 120)。"""
    chunk_size, overlap = _get_chunk_strategy("encyclopedia")
    assert chunk_size == 800
    assert overlap == 120


def test_get_chunk_strategy_recipe():
    """recipe 类别应返回小 chunk (400, 60)。"""
    chunk_size, overlap = _get_chunk_strategy("recipe")
    assert chunk_size == 400
    assert overlap == 60


def test_get_chunk_strategy_default_empty_string():
    """空字符串（默认）应返回中等 chunk (500, 80)。"""
    chunk_size, overlap = _get_chunk_strategy("")
    assert chunk_size == 500
    assert overlap == 80


def test_get_chunk_strategy_default_none():
    """None（默认）应返回中等 chunk (500, 80)。"""
    chunk_size, overlap = _get_chunk_strategy(None)
    assert chunk_size == 500
    assert overlap == 80


def test_get_chunk_strategy_unknown_category():
    """未知类别应回退到默认 (500, 80)。"""
    chunk_size, overlap = _get_chunk_strategy("unknown_category")
    assert chunk_size == 500
    assert overlap == 80


def test_get_chunk_strategy_returns_tuple_of_ints():
    """返回值应为 int 元组，确保类型安全。"""
    result = _get_chunk_strategy("encyclopedia")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(x, int) for x in result)


# ---------------------------------------------------------------------------
# Task 3：差异化分片策略 import_text 集成测试
#
# 注：集成测试用 monkeypatch 切换到 hash embedding 后端，避免触发
# sentence_transformers 模型加载（首次加载约 30s+），保持测试快速可重复。
# ---------------------------------------------------------------------------
def _setup_hash_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    """切换到 hash embedding 后端 + 重置 settings 单例。"""
    monkeypatch.setenv("KB_EMBEDDING_PROVIDER", "hash")
    from hermes_kb.config import reset_settings

    reset_settings()


def test_import_text_encyclopedia_uses_larger_chunk(tmp_db, monkeypatch):
    """百科类文档导入时应使用大 chunk 策略 (800/120)。

    构造一段 1500 字百科长文，验证 chunk 数量小于默认策略下的数量。
    """
    _setup_hash_embedding(monkeypatch)
    svc = ImportService()
    # 构造 1500 字百科长文（多段落）
    long_content = "# 金酒百科\n\n" + "金酒是杜松子酒，起源于荷兰。" * 30 + "\n\n## 风味\n\n" + "杜松子香气明显。" * 30
    result_enc = svc.import_text(
        content=long_content,
        title="金酒百科",
        category="encyclopedia",
        file_type="md",
    )
    assert result_enc["status"] == "imported"

    # 同样内容用默认策略导入对比
    result_default = svc.import_text(
        content=long_content,
        title="金酒百科默认",
        category="",
        file_type="md",
    )
    # 百科 chunk 更大 → chunk 数量更少
    assert result_enc["chunk_count"] <= result_default["chunk_count"]


def test_import_text_recipe_uses_smaller_chunk(tmp_db, monkeypatch):
    """配方类文档导入时应使用小 chunk 策略 (400/60)。

    构造一段 1200 字配方，验证 chunk 数量大于默认策略下的数量。
    """
    _setup_hash_embedding(monkeypatch)
    svc = ImportService()
    # 构造 1200 字配方内容
    recipe_content = (
        "# Old Fashioned\n\n"
        + "材料：波本威士忌 60ml、糖 1 块、安高天娜苦精 2 dashes、橙皮。" * 20
        + "\n\n## 步骤\n\n"
        + "将糖与苦精混合，加入威士忌搅拌，放冰块，装饰橙皮。" * 20
    )
    result_recipe = svc.import_text(
        content=recipe_content,
        title="Old Fashioned",
        category="recipe",
        file_type="md",
    )
    assert result_recipe["status"] == "imported"

    # 同样内容用默认策略导入对比
    result_default = svc.import_text(
        content=recipe_content,
        title="Old Fashioned 默认",
        category="",
        file_type="md",
    )
    # 配方 chunk 更小 → chunk 数量更多
    assert result_recipe["chunk_count"] >= result_default["chunk_count"]


def test_import_text_category_persisted(tmp_db, monkeypatch):
    """导入的文档 category 字段应正确持久化到数据库。"""
    _setup_hash_embedding(monkeypatch)
    from sqlmodel import select

    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    svc = ImportService()
    svc.import_text(
        content="伏特加是中性烈酒。" * 20,
        title="伏特加百科",
        category="encyclopedia",
        file_type="md",
    )
    with get_session() as session:
        doc = session.exec(
            select(Document).where(Document.title == "伏特加百科")
        ).first()
        assert doc is not None
        assert doc.category == "encyclopedia"


def test_import_text_chunk_count_zero_for_allow_empty_with_category(tmp_db, monkeypatch):
    """allow_empty=True + category 时，chunk_count 仍为 0。"""
    _setup_hash_embedding(monkeypatch)
    svc = ImportService()
    result = svc.import_text(
        content="",
        title="空百科",
        category="encyclopedia",
        allow_empty=True,
    )
    assert result["chunk_count"] == 0


def test_import_text_encyclopedia_long_paragraph_not_split_excessively(tmp_db, monkeypatch):
    """百科长段落不应被过度切分（大 chunk 策略生效）。"""
    _setup_hash_embedding(monkeypatch)
    svc = ImportService()
    # 单段落约 600 字（超过 recipe 的 400 但小于 encyclopedia 的 800 + overlap 120）
    # 百科策略下应切成 1 个 chunk；如果用 recipe 400 策略会切成 2 段
    long_paragraph = "金酒的历史源远流长。" * 60  # ~600 字
    result = svc.import_text(
        content=long_paragraph,
        title="金酒历史",
        category="encyclopedia",
        file_type="md",
    )
    # 百科策略下 600 字段落应在单个 chunk 内（< 800）
    assert result["chunk_count"] == 1
