"""M3 配方元数据字段持久化测试（Task 3.1）。

覆盖 Document 新增四字段（glassware/technique/iba_category/flavor_profile）的
默认值、持久化、seed_recipes() 回填、幂等导入、ImportService 元数据透传、
向后兼容旧文档等场景。

依赖：
- tmp_db（conftest.py autouse fixture）：每个测试独立临时 SQLite
- hermes_kb.seed.seed_recipes：导入 57 款 IBA 配方
- hermes_kb.rag.ImportService.import_text：支持四元数据参数
"""
from __future__ import annotations

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document


# ===========================================================================
# Document 默认值
# ===========================================================================
def test_document_default_values():
    """新建 Document 时不传新字段，四字段应为空字符串。"""
    doc = Document(title="默认值测试", content="内容")
    assert doc.glassware == ""
    assert doc.technique == ""
    assert doc.iba_category == ""
    assert doc.flavor_profile == ""


# ===========================================================================
# Document 元数据持久化
# ===========================================================================
def test_document_persist_metadata():
    """创建 Document 时传入四字段，commit 后重新查询应返回一致值。"""
    with get_session() as session:
        doc = Document(
            title="元数据持久化测试",
            content="测试内容",
            glassware="马天尼杯",
            technique="stir",
            iba_category="unforgettables",
            flavor_profile="juniper;botanical;herbal;dry",
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        doc_id = doc.doc_id

    # 新 session 重新查询，验证落库
    with get_session() as session:
        loaded = session.exec(
            select(Document).where(Document.doc_id == doc_id)
        ).first()
        assert loaded is not None
        assert loaded.glassware == "马天尼杯"
        assert loaded.technique == "stir"
        assert loaded.iba_category == "unforgettables"
        assert loaded.flavor_profile == "juniper;botanical;herbal;dry"


# ===========================================================================
# seed_recipes() 回填
# ===========================================================================
def test_seed_recipes_persists_metadata():
    """seed_recipes() 后 57 款配方的 technique/glassware/iba_category 应非空。"""
    from hermes_kb.seed import seed_recipes
    from hermes_kb.seed_recipes import SEED_RECIPES

    result = seed_recipes()
    expected_count = len(SEED_RECIPES)  # 57
    assert result["seeded"] == expected_count, (
        f"应导入 {expected_count} 款，实际 seeded={result['seeded']}"
    )

    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.source == "iba")
        ).all()
        assert len(docs) == expected_count
        missing_meta: list[str] = []
        for d in docs:
            if not d.technique:
                missing_meta.append(f"{d.title}(technique)")
            if not d.glassware:
                missing_meta.append(f"{d.title}(glassware)")
            if not d.iba_category:
                missing_meta.append(f"{d.title}(iba_category)")
        assert not missing_meta, f"配方缺失元数据: {missing_meta[:10]}"


def test_seed_recipes_flavor_profile_aggregated():
    """至少 50 款配方的 flavor_profile 非空（聚合自材料 tags）。

    阈值 50/57 是因为个别配方材料组合 tags 为空（如果汁类无 tags），
    实际多数配方含金酒/威士忌等带 tags 的基酒。
    """
    from hermes_kb.seed import seed_recipes

    seed_recipes()

    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.source == "iba")
        ).all()
        non_empty = sum(1 for d in docs if d.flavor_profile)
        # 至少 50/57 非空（语义断言，避免硬编码 57）
        assert non_empty >= 50, (
            f"flavor_profile 非空仅 {non_empty}/{len(docs)}，期望 >= 50"
        )


def test_seed_recipes_idempotent():
    """重复调用 seed_recipes() 不重复导入（skipped 计数正确）。"""
    from hermes_kb.seed import seed_recipes
    from hermes_kb.seed_recipes import SEED_RECIPES

    expected = len(SEED_RECIPES)
    first = seed_recipes()
    assert first["seeded"] == expected
    assert first["skipped"] == 0

    # 第二次调用：所有配方已存在，全部 skipped
    second = seed_recipes()
    assert second["seeded"] == 0
    assert second["skipped"] == expected
    # 验证 DB 中仍只有 expected 款（未重复导入）
    with get_session() as session:
        count = session.exec(
            select(Document).where(Document.source == "iba")
        ).all()
        assert len(count) == expected


# ===========================================================================
# ImportService.import_text 元数据透传
# ===========================================================================
def test_import_text_accepts_metadata():
    """ImportService.import_text 传入 technique/glassware 等参数后正确落库。"""
    from hermes_kb.rag import ImportService

    importer = ImportService()
    result = importer.import_text(
        content="测试配方内容",
        title="ImportService 元数据透传测试",
        category="recipe",
        source="local",
        technique="shake",
        glassware="高球杯",
        iba_category="contemporary_classics",
        flavor_profile="citrus;sweet",
    )
    doc_id = result["doc_id"]

    with get_session() as session:
        doc = session.exec(
            select(Document).where(Document.doc_id == doc_id)
        ).first()
        assert doc is not None
        assert doc.technique == "shake"
        assert doc.glassware == "高球杯"
        assert doc.iba_category == "contemporary_classics"
        assert doc.flavor_profile == "citrus;sweet"
        assert doc.category == "recipe"


# ===========================================================================
# 向后兼容：旧 Document 不带新字段仍可读写
# ===========================================================================
def test_backward_compat_old_documents():
    """不传新字段的 Document 仍可正常 commit 与查询（向后兼容）。

    模拟旧版本创建的文档（无四元数据），在新版本 DB 中读写无障碍。
    """
    with get_session() as session:
        # 仅传 title + content（其余字段使用模型默认值）
        doc = Document(
            title="旧版本文档向后兼容测试",
            content="这是旧版本创建的文档，没有元数据字段",
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        doc_id = doc.doc_id

    with get_session() as session:
        loaded = session.exec(
            select(Document).where(Document.doc_id == doc_id)
        ).first()
        assert loaded is not None
        assert loaded.title == "旧版本文档向后兼容测试"
        # 新字段应有默认空字符串值，不报错
        assert loaded.glassware == ""
        assert loaded.technique == ""
        assert loaded.iba_category == ""
        assert loaded.flavor_profile == ""


# ===========================================================================
# Task 4.1：difficulty / abv_bucket 字段持久化与索引查询
# ===========================================================================
class TestDifficultyAbvBucketPersistence:
    """Task 4：验证 difficulty/abv_bucket 字段的默认值、持久化与索引查询。"""

    def test_default_values(self):
        """新建 Document 时不传 difficulty/abv_bucket，两者应为空字符串。"""
        doc = Document(title="难度档位默认值测试", content="内容")
        assert doc.difficulty == ""
        assert doc.abv_bucket == ""

    def test_persist_difficulty_and_abv_bucket(self):
        """创建 Document 传入 difficulty/abv_bucket，commit 后重新查询字段保持。"""
        with get_session() as session:
            doc = Document(
                title="难度档位持久化测试",
                content="测试内容",
                difficulty="hard",
                abv_bucket="strong",
            )
            session.add(doc)
            session.commit()
            session.refresh(doc)
            doc_id = doc.doc_id

        # 新 session 重新查询，验证落库
        with get_session() as session:
            loaded = session.exec(
                select(Document).where(Document.doc_id == doc_id)
            ).first()
            assert loaded is not None
            assert loaded.difficulty == "hard"
            assert loaded.abv_bucket == "strong"

    def test_query_by_difficulty_index(self):
        """按 difficulty 索引查询：仅返回匹配条目。"""
        with get_session() as session:
            easy_doc = Document(
                title="简单配方",
                content="easy",
                difficulty="easy",
            )
            hard_doc = Document(
                title="困难配方",
                content="hard",
                difficulty="hard",
            )
            session.add(easy_doc)
            session.add(hard_doc)
            session.commit()
            session.refresh(easy_doc)
            session.refresh(hard_doc)

        # 新 session 按 difficulty="easy" 查询，应只返回 1 条
        with get_session() as session:
            easy_list = session.exec(
                select(Document).where(Document.difficulty == "easy")
            ).all()
            assert len(easy_list) == 1
            assert easy_list[0].title == "简单配方"

    def test_query_by_abv_bucket_index(self):
        """按 abv_bucket 索引查询：仅返回匹配条目。"""
        with get_session() as session:
            low_doc = Document(
                title="低度配方",
                content="low",
                abv_bucket="low",
            )
            strong_doc = Document(
                title="烈性配方",
                content="strong",
                abv_bucket="strong",
            )
            session.add(low_doc)
            session.add(strong_doc)
            session.commit()
            session.refresh(low_doc)
            session.refresh(strong_doc)

        # 新 session 按 abv_bucket="low" 查询，应只返回 1 条
        with get_session() as session:
            low_list = session.exec(
                select(Document).where(Document.abv_bucket == "low")
            ).all()
            assert len(low_list) == 1
            assert low_list[0].title == "低度配方"
