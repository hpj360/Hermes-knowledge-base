"""数据源注册表测试。"""
from __future__ import annotations

import pytest

from hermes_kb.data_sources import (
    DataSourcesError,
    get_source,
    load_data_source_registry,
    validate_registry,
)
from hermes_kb.models import Document


class TestRegistry:
    def test_load_registry_has_first_wave_sources(self):
        """首波 6 个数据源存在。"""
        reg = load_data_source_registry()
        for sid in (
            "wikidata",
            "crossref",
            "iwsr_summary",
            "who_alcohol",
            "iba_official",
            "thecocktaildb",
        ):
            assert sid in reg, f"缺少数据源 {sid}"

    def test_registry_fields_complete(self):
        """每个源必填字段齐全。"""
        problems = validate_registry()
        assert problems == [], f"注册表校验失败: {problems}"

    def test_get_source_ok(self):
        src = get_source("iwsr_summary")
        assert src["name"] == "IWSR 全球酒类市场数据摘要"
        assert src["type"] == "report"

    def test_get_source_unknown_raises(self):
        with pytest.raises(DataSourcesError):
            get_source("nonexistent")


# ---------------------------------------------------------------------------
# 溯源元数据持久化
# ---------------------------------------------------------------------------
class TestProvenance:
    def test_document_default_values(self):
        """新建 Document 溯源字段默认值。"""
        doc = Document(title="溯源默认", content="内容")
        assert doc.source_authority == ""
        assert doc.source_url is None
        assert doc.source_refreshed_at is None
        assert doc.source_license is None

    def test_document_persist_provenance(self):
        """溯源字段写入后重新查询一致。"""
        from datetime import datetime, timezone

        from sqlmodel import select

        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        refreshed = datetime(2026, 8, 12, tzinfo=timezone.utc)
        with get_session() as session:
            doc = Document(
                title="溯源持久化测试",
                content="内容",
                source="iwsr_summary",
                source_authority="IWSR",
                source_url="https://www.theiwsr.com/insight/",
                source_refreshed_at=refreshed,
                source_license="open-access",
            )
            session.add(doc)
            session.commit()
            doc_id = doc.doc_id

        with get_session() as session:
            loaded = session.exec(
                select(Document).where(Document.doc_id == doc_id)
            ).first()
            assert loaded is not None
            assert loaded.source_authority == "IWSR"
            assert loaded.source_url == "https://www.theiwsr.com/insight/"
            assert loaded.source_license == "open-access"
            assert loaded.source_refreshed_at is not None

    def test_import_text_writes_provenance(self):
        """ImportService.import_text 写入溯源字段。"""
        from sqlmodel import select

        from hermes_kb.database import get_session
        from hermes_kb.models import Document
        from hermes_kb.rag import ImportService

        importer = ImportService()
        importer.import_text(
            content="IWSR 预测 2035 年全球酒类消费接近 2025 年水平。",
            title="IWSR 市场摘要测试",
            category="encyclopedia",
            source="iwsr_summary",
            source_authority="IWSR",
            source_url="https://www.theiwsr.com/insight/",
            source_license="open-access",
        )
        with get_session() as session:
            doc = session.exec(
                select(Document).where(Document.title == "IWSR 市场摘要测试")
            ).first()
            assert doc is not None
            assert doc.source_authority == "IWSR"
            assert doc.source_url == "https://www.theiwsr.com/insight/"
            assert doc.source_license == "open-access"
            assert doc.source == "iwsr_summary"


# ---------------------------------------------------------------------------
# 数据源适配器框架
# ---------------------------------------------------------------------------
class TestAdapters:
    def test_get_adapter_curated(self):
        """curated 源返回 CuratedSourceAdapter。"""
        from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter
        from hermes_kb.data_sources.registry import get_adapter

        adapter = get_adapter("iwsr_summary")
        assert isinstance(adapter, CuratedSourceAdapter)
        assert adapter.source_id == "iwsr_summary"

    def test_get_adapter_api(self):
        """api 源返回对应实时适配器。"""
        from hermes_kb.data_sources.adapters.api import CrossrefAdapter, WikidataAdapter
        from hermes_kb.data_sources.registry import get_adapter

        assert isinstance(get_adapter("wikidata"), WikidataAdapter)
        assert isinstance(get_adapter("crossref"), CrossrefAdapter)

    def test_curated_fetch_and_validate(self):
        """策划源快照可读取且通过 schema 校验。"""
        from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter

        adapter = CuratedSourceAdapter("iwsr_summary")
        raw = adapter.fetch()
        assert raw, "iwsr_summary 快照为空"
        assert adapter.validate(raw) == []

    def test_curated_validate_catches_missing(self):
        """缺字段时 validate 返回问题。"""
        from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter

        adapter = CuratedSourceAdapter("iwsr_summary")
        problems = adapter.validate([{"title": "x"}])
        assert problems, "应检测到缺失字段"

    def test_curated_import_idempotent(self):
        """curated 源导入并幂等去重。"""
        from sqlmodel import select

        from hermes_kb.database import get_session
        from hermes_kb.models import Document
        from hermes_kb.rag import ImportService
        from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter

        importer = ImportService()
        adapter = CuratedSourceAdapter("iwsr_summary")
        r1 = adapter.import_data(importer)
        assert r1["imported"] == 6, f"首次应导入 6 篇: {r1}"
        # 再次导入全部跳过（幂等）
        r2 = adapter.import_data(importer)
        assert r2["skipped"] == 6, f"二次应全部跳过: {r2}"

        with get_session() as session:
            docs = session.exec(
                select(Document).where(Document.source == "iwsr_summary")
            ).all()
            assert len(docs) == 6
            # 溯源字段写入
            assert all(d.source_authority == "IWSR" for d in docs)
            assert all(d.source_url for d in docs)


