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

        from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter
        from hermes_kb.database import get_session
        from hermes_kb.models import Document
        from hermes_kb.rag import ImportService

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


# ---------------------------------------------------------------------------
# 注册表错误路径
# ---------------------------------------------------------------------------
class TestRegistryErrors:
    def test_load_registry_not_object_raises(self, tmp_path, monkeypatch):
        """registry.json 顶层非对象 → DataSourcesError。"""
        import hermes_kb.data_sources as ds

        bad = tmp_path / "registry.json"
        bad.write_text("[]", encoding="utf-8")
        monkeypatch.setattr(ds, "_REGISTRY_PATH", bad)
        with pytest.raises(DataSourcesError):
            ds.load_data_source_registry()

    def test_validate_registry_detects_all_problems(self, monkeypatch):
        """校验能发现 id 不一致 / 缺必填 / 非法枚举 / 越界等级。"""
        import hermes_kb.data_sources as ds

        bad = {
            "a": {"id": "b"},  # id 与键不一致
            "c": {},  # 全部必填缺失
            "d": {
                "id": "d",
                "type": "bad",
                "access": "bad",
                "status": "bad",
                "authority_level": 9,
            },
        }
        monkeypatch.setattr(ds, "_load_raw", lambda: bad)
        problems = ds.validate_registry()
        assert any("id 与键不一致" in p for p in problems)
        assert any("缺少必填字段" in p for p in problems)
        assert any("非法 type" in p for p in problems)
        assert any("非法 access" in p for p in problems)
        assert any("非法 status" in p for p in problems)
        assert any("authority_level 需为 1..5" in p for p in problems)

    def test_validate_registry_duplicate_id(self, monkeypatch):
        """存在重复 id 时报告。"""
        import hermes_kb.data_sources as ds

        dup = {"a": {"id": "x"}, "b": {"id": "x"}}
        monkeypatch.setattr(ds, "_load_raw", lambda: dup)
        problems = ds.validate_registry()
        assert any("重复 id" in p for p in problems)

    def test_get_source_not_found_raises(self, monkeypatch):
        """get_source 缺失 → DataSourcesError。"""
        import hermes_kb.data_sources as ds

        monkeypatch.setattr(ds, "_load_raw", lambda: {"a": {"id": "a"}})
        with pytest.raises(DataSourcesError):
            ds.get_source("missing")


# ---------------------------------------------------------------------------
# 适配器注册表（get_adapter 全映射）
# ---------------------------------------------------------------------------
class TestAdapterRegistryMapping:
    @pytest.mark.parametrize(
        "source_id,cls_name",
        [
            ("thecocktaildb", "TheCocktailDBAdapter"),
            ("wikipedia", "WikipediaAdapter"),
            ("openfoodfacts", "OpenFoodFactsAdapter"),
            ("usda_fooddata", "USDAFoodDataAdapter"),
            ("dbpedia", "DBpediaAdapter"),
            ("bar_assistant_cocktails", "BarAssistantCocktailsAdapter"),
            ("bar_assistant_ingredients", "BarAssistantIngredientsAdapter"),
            ("wikidata_cocktails", "WikidataCocktailsAdapter"),
        ],
    )
    def test_get_adapter_api_mapping(self, source_id, cls_name):
        from hermes_kb.data_sources.registry import get_adapter

        adapter = get_adapter(source_id)
        assert adapter.__class__.__name__ == cls_name

    def test_get_adapter_no_matching_raises(self, monkeypatch):
        """access=api 且无匹配 import_adapter → DataSourcesError。"""
        import hermes_kb.data_sources.registry as reg
        from hermes_kb.data_sources import DataSourcesError
        from hermes_kb.data_sources.registry import get_adapter

        monkeypatch.setattr(
            reg, "get_source", lambda sid: {"access": "api", "import_adapter": "nope"}
        )
        with pytest.raises(DataSourcesError):
            get_adapter("whatever")


# ---------------------------------------------------------------------------
# DataSourceAdapter 基类：run() 编排
# ---------------------------------------------------------------------------
class TestAdapterRun:
    def _make_adapter(self, problems, summary):
        from hermes_kb.data_sources.base import DataSourceAdapter

        class _Adapter(DataSourceAdapter):
            source_id = "test_adapter"

            def fetch(self):
                return [{"title": "a"}, {"title": "b"}]

            def validate(self, raw):
                return problems

            def import_data(self, importer):
                return summary

        return _Adapter()

    def test_run_failed_when_validate_problems(self):
        result = self._make_adapter(["problem"], {}).run(None)
        assert result["failed"] == 2
        assert result["errors"] == ["problem"]
        assert result["imported"] == 0

    def test_run_success_delegates_import(self):
        summary = {"imported": 2, "skipped": 0, "failed": 0, "errors": []}
        result = self._make_adapter([], summary).run(None)
        assert result == summary


# ---------------------------------------------------------------------------
# CuratedSourceAdapter：错误路径
# ---------------------------------------------------------------------------
class TestCuratedAdapterErrors:
    def test_fetch_missing_snapshot_raises(self):
        from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter

        adapter = CuratedSourceAdapter("nonexistent_source")
        with pytest.raises(FileNotFoundError):
            adapter.fetch()

    def test_fetch_not_list_raises(self, tmp_path, monkeypatch):
        import json

        import hermes_kb.data_sources.adapters.curated as curated_mod
        from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter

        snap = tmp_path / "bad.json"
        snap.write_text(json.dumps({"a": 1}), encoding="utf-8")
        monkeypatch.setattr(curated_mod, "_SOURCES_DIR", tmp_path)
        adapter = CuratedSourceAdapter("bad")
        with pytest.raises(ValueError):
            adapter.fetch()

    def test_validate_content_too_short(self):
        from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter

        adapter = CuratedSourceAdapter("iwsr_summary")
        item = {
            "title": "t",
            "content": "太短",
            "source_url": "u",
            "refreshed_at": "2026-01-01",
            "license": "cc",
            "category": "encyclopedia",
            "source_authority": "a",
        }
        problems = adapter.validate([item])
        assert any("内容过短" in p for p in problems)

    def test_import_data_exception_marks_failed(self):
        from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter
        from hermes_kb.rag import ImportService

        adapter = CuratedSourceAdapter("iwsr_summary")
        importer = ImportService()

        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        importer.import_text = boom  # type: ignore[method-assign]
        result = adapter.import_data(importer)
        assert result["imported"] == 0
        assert result["failed"] == 6
        assert all("boom" in e for e in result["errors"])

    def test_parse_date_valid(self):
        from hermes_kb.data_sources.adapters.curated import _parse_date

        d = _parse_date("2026-08-12T10:00:00")
        assert d is not None
        assert d.tzinfo is not None

    def test_parse_date_invalid_returns_none(self):
        from hermes_kb.data_sources.adapters.curated import _parse_date

        assert _parse_date(None) is None
        assert _parse_date("") is None
        assert _parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# API 适配器：_get 网络层 + import_data 编排
# ---------------------------------------------------------------------------
def _make_api_test_adapter(raw, validate_problems=None):
    """构造最小 API 适配器测试桩（闭包注入 fetch/validate 结果）。"""
    from hermes_kb.data_sources.adapters.api import _ApiAdapter

    problems = validate_problems or []

    class _Impl(_ApiAdapter):
        source_id = "api_test"

        def fetch(self):
            return raw

        def validate(self, r):
            return problems

    return _Impl()


class TestApiAdapterNetwork:
    def _patch_get(self, monkeypatch, responder):
        import hermes_kb.data_sources.adapters.api as api_mod

        def fake_get(url, headers=None):
            return responder(url, headers or {})

        monkeypatch.setattr(api_mod._ApiAdapter, "_get", staticmethod(fake_get))

    def test_get_with_proxy(self, monkeypatch):
        """设置 HTTPS_PROXY 时走 ProxyHandler。"""
        import urllib.request

        import hermes_kb.data_sources.adapters.api as api_mod

        monkeypatch.setenv("HTTPS_PROXY", "http://proxy:8080")
        monkeypatch.delenv("HTTP_PROXY", raising=False)

        captured: dict = {}

        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"ok": 1}'

        class _FakeOpener:
            def open(self, req, timeout=None):
                captured["timeout"] = timeout
                return _FakeResp()

        def fake_build(handler=None):
            captured["handler"] = handler
            return _FakeOpener()

        monkeypatch.setattr(urllib.request, "build_opener", fake_build)
        result = api_mod._ApiAdapter._get("http://example.com/x")
        assert result == {"ok": 1}
        assert captured["handler"] is not None

    def test_get_without_proxy(self, monkeypatch):
        """无代理设置时 handler 为 None。"""
        import urllib.request

        import hermes_kb.data_sources.adapters.api as api_mod

        monkeypatch.delenv("HTTPS_PROXY", raising=False)
        monkeypatch.delenv("HTTP_PROXY", raising=False)

        captured: dict = {}

        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b"[]"

        class _FakeOpener:
            def open(self, req, timeout=None):
                captured["timeout"] = timeout
                return _FakeResp()

        def fake_build(handler=None):
            captured["handler"] = handler
            return _FakeOpener()

        monkeypatch.setattr(urllib.request, "build_opener", fake_build)
        result = api_mod._ApiAdapter._get("http://example.com/x")
        assert result == []
        assert captured["handler"] is None


class TestApiAdapterImport:
    def test_import_fetch_error_graceful(self):
        """fetch 抛异常 → 优雅返回失败。"""
        from hermes_kb.data_sources.adapters import api as api_mod
        from hermes_kb.rag import ImportService

        class _Boom(api_mod._ApiAdapter):
            source_id = "api_test"

            def fetch(self):
                raise RuntimeError("network unreachable")

            def validate(self, raw):
                return []

        result = _Boom().import_data(ImportService())
        assert result["imported"] == 0
        assert result["errors"] == ["network unreachable"]

    def test_import_validate_problems_marks_failed(self):
        """validate 有问题 → 全部标记失败。"""
        adapter = _make_api_test_adapter(
            [{"title": "a"}, {"title": "b"}], validate_problems=["bad"]
        )
        result = adapter.import_data(None)
        assert result["failed"] == 2
        assert result["errors"] == ["bad"]

    def test_import_dedup_skips_existing(self):
        """已存在标题跳过（幂等），其余导入。"""
        from hermes_kb.rag import ImportService

        importer = ImportService()
        importer.import_text(
            content="已有内容",
            title="T1",
            source_type="seed",
            file_type="md",
            category="encyclopedia",
            source="api_test",
        )
        adapter = _make_api_test_adapter(
            [{"title": "T1", "content": "c1"}, {"title": "T2", "content": "c2"}]
        )
        result = adapter.import_data(importer)
        assert result["imported"] == 1
        assert result["skipped"] == 1
        assert result["failed"] == 0

    def test_import_missing_title_marks_failed(self):
        """item 缺 title → KeyError 计入失败。"""
        from hermes_kb.rag import ImportService

        adapter = _make_api_test_adapter([{"content": "no title"}])
        result = adapter.import_data(ImportService())
        assert result["failed"] == 1
        assert result["imported"] == 0


# ---------------------------------------------------------------------------
# API 适配器：fetch 解析（mock _get）
# ---------------------------------------------------------------------------
class TestApiAdapterFetch:
    def _patch_get(self, monkeypatch, responder):
        import hermes_kb.data_sources.adapters.api as api_mod

        def fake_get(url, headers=None):
            return responder(url, headers or {})

        monkeypatch.setattr(api_mod._ApiAdapter, "_get", staticmethod(fake_get))

    def test_wikidata_fetch(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import WikidataAdapter

        data = {
            "results": {
                "bindings": [
                    {
                        "item": {"value": "http://www.wikidata.org/entity/Q11416"},
                        "label": {"value": "Gin"},
                        "zh": {"value": "金酒"},
                        "desc": {"value": "以杜松子为主的烈酒"},
                    }
                ]
            }
        }
        self._patch_get(monkeypatch, lambda url, h: data)
        adapter = WikidataAdapter()
        items = adapter.fetch()
        assert len(items) == 1
        assert items[0]["title"] == "金酒"
        assert items[0]["license"] == "CC0"
        assert "Q11416" in items[0]["source_url"]
        assert adapter.validate(items) == []

    def test_wikidata_cocktails_fetch(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import WikidataCocktailsAdapter

        sparql = {
            "results": {
                "bindings": [
                    {"item": {"value": "http://www.wikidata.org/entity/Q123"}},
                    {"item": {"value": "http://www.wikidata.org/entity/Q456"}},
                ]
            }
        }
        ents = {
            "entities": {
                "Q123": {
                    "labels": {"zh": {"value": "金菲士"}, "en": {"value": "Gin Fizz"}},
                    "aliases": {"zh": [{"value": "金菲士"}]},
                    "descriptions": {"zh": {"value": "一款经典鸡尾酒"}},
                },
                "Q456": {
                    "labels": {"en": {"value": "Old Fashioned"}},
                    "aliases": {},
                    "descriptions": {},
                },
            }
        }

        def responder(url, headers):
            if "sparql" in url:
                return sparql
            return ents

        self._patch_get(monkeypatch, responder)
        adapter = WikidataCocktailsAdapter()
        items = adapter.fetch()
        titles = [i["title"] for i in items]
        assert "金菲士" in titles
        assert "古典鸡尾酒" in titles  # 英文名经词典翻译兜底
        assert adapter.validate(items) == []

    def test_wikidata_cocktails_build_items_qid_fallback(self):
        """无任何 label 时用 QID 兜底。"""
        from hermes_kb.data_sources.adapters.api import WikidataCocktailsAdapter

        items = WikidataCocktailsAdapter()._build_items(
            ["Q999"],
            {"Q999": {"labels": {}, "aliases": {}, "descriptions": {}}},
        )
        assert items[0]["title"] == "Q999"

    def test_wikidata_cocktails_build_items_dedup(self):
        """相同标题的实体只保留首个。"""
        from hermes_kb.data_sources.adapters.api import WikidataCocktailsAdapter

        ent = {
            "labels": {"en": {"value": "Old Fashioned"}},
            "aliases": {},
            "descriptions": {},
        }
        items = WikidataCocktailsAdapter()._build_items(["Q1", "Q2"], {"Q1": ent, "Q2": ent})
        assert len(items) == 1

    def test_wikidata_cocktails_pick_zh_labels_dedup(self):
        from hermes_kb.data_sources.adapters.api import WikidataCocktailsAdapter

        ent = {
            "labels": {
                "zh": {"value": "金菲士"},
                "zh-hans": {"value": "金菲士"},
                "zh-tw": {"value": "琴費士"},
            }
        }
        result = WikidataCocktailsAdapter._pick_zh(ent, "labels")
        assert result == ["金菲士", "琴費士"]

    def test_wikidata_cocktails_pick_zh_aliases(self):
        from hermes_kb.data_sources.adapters.api import WikidataCocktailsAdapter

        ent = {"aliases": {"zh": [{"value": "琴費士"}, {"value": "金菲士"}]}}
        result = WikidataCocktailsAdapter._pick_zh(ent, "aliases")
        assert result == ["琴費士", "金菲士"]

    def test_crossref_fetch(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import CrossrefAdapter

        data = {
            "message": {
                "items": [
                    {
                        "title": ["Spirits and Fermentation Chemistry"],
                        "DOI": "10.1000/xyz",
                        "container-title": ["Journal of Brewing"],
                        "abstract": "<jats:p>Abstract text.</jats:p>",
                    },
                    {"title": ["Spirits and Fermentation Chemistry"]},  # 重复
                    {"title": [""]},  # 无标题
                ]
            }
        }
        self._patch_get(monkeypatch, lambda url, h: data)
        adapter = CrossrefAdapter()
        items = adapter.fetch()
        assert len(items) == 1
        assert "Abstract text." in items[0]["content"]
        assert "10.1000/xyz" in items[0]["source_url"]
        assert adapter.validate(items) == []

    def test_crossref_fetch_all_requests_fail(self, monkeypatch):
        """所有请求抛异常 → 返回空列表。"""
        from hermes_kb.data_sources.adapters.api import CrossrefAdapter

        def boom(url, headers):
            raise RuntimeError("net down")

        self._patch_get(monkeypatch, boom)
        assert CrossrefAdapter().fetch() == []

    def test_wikipedia_fetch(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import WikipediaAdapter

        long_extract = "这是一段足够长的中文百科正文。" * 30
        pages = {
            "1": {"title": "金酒", "extract": long_extract},
            "2": {"title": "过短", "extract": "short"},
        }
        self._patch_get(
            monkeypatch, lambda url, h: {"query": {"pages": pages}}
        )
        adapter = WikipediaAdapter()
        items = adapter.fetch()
        assert len(items) == 1
        assert items[0]["title"] == "金酒"
        assert items[0]["license"] == "CC BY-SA"
        assert adapter.validate(items) == []

    def test_wikipedia_fetch_requests_fail(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import WikipediaAdapter

        def boom(url, headers):
            raise RuntimeError("net down")

        self._patch_get(monkeypatch, boom)
        assert WikipediaAdapter().fetch() == []

    def test_openfoodfacts_fetch(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import OpenFoodFactsAdapter

        data = {
            "products": [
                {
                    "product_name": "London Dry Gin",
                    "brands": "Beefeater",
                    "alcohol": "40",
                    "ingredients_text": "Juniper berries, water, neutral spirit",
                    "nutriments": {
                        "energy-kcal_100g": 222,
                        "carbohydrates_100g": 1.5,
                        "sugars_100g": 0.5,
                        "fat_100g": 0.1,
                    },
                    "code": "5000000000000",
                },
                {"product_name": ""},  # 无产品名
                {"product_name": "x"},  # 内容过短被过滤
            ]
        }
        self._patch_get(monkeypatch, lambda url, h: data)
        adapter = OpenFoodFactsAdapter()
        items = adapter.fetch()
        assert len(items) == 1
        assert "Beefeater" in items[0]["content"]
        assert "222" in items[0]["content"]
        assert adapter.validate(items) == []

    def test_usda_fooddata_fetch(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import USDAFoodDataAdapter

        data = [
            {
                "fdcId": 1,
                "description": "Beer, regular, all varieties, 5% alcohol by volume",
                "foodNutrients": [
                    {"nutrientName": "Energy (kilocalories)", "amount": 43, "unitName": "KCAL"},
                    {"nutrientName": "Carbohydrate, by difference (grams)", "amount": 3.6, "unitName": "G"},
                    {"nutrientName": "Protein (grams)", "amount": 0.5, "unitName": "G"},
                    {"nutrientName": "Total lipid (fat) (grams)", "amount": 0.0, "unitName": "G"},
                    {"nutrientName": "Alcohol, ethyl (grams)", "amount": 3.9, "unitName": "G"},
                ],
            },
            {"fdcId": 2, "description": ""},  # 无描述
            {"fdcId": 3, "description": "Short"},  # 内容过短
        ]
        self._patch_get(monkeypatch, lambda url, h: data)
        adapter = USDAFoodDataAdapter()
        items = adapter.fetch()
        assert len(items) == 1
        assert "43 KCAL" in items[0]["content"]
        assert items[0]["title"].startswith("USDA:")
        assert adapter.validate(items) == []

    def test_dbpedia_fetch(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import DBpediaAdapter

        data = {
            "results": {
                "bindings": [
                    {
                        "label": {"value": "Gin"},
                        "abstract": {"value": "Gin is a distilled alcoholic drink."},
                        "entity": {"value": "http://dbpedia.org/resource/Gin"},
                    },
                    {"label": {"value": ""}, "abstract": {"value": ""}},  # 跳过
                ]
            }
        }
        self._patch_get(monkeypatch, lambda url, h: data)
        adapter = DBpediaAdapter()
        items = adapter.fetch()
        assert len(items) == 1
        assert items[0]["title"] == "Gin"
        assert items[0]["source_url"] == "http://dbpedia.org/resource/Gin"
        assert adapter.validate(items) == []

    def test_bar_assistant_cocktails_fetch(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import BarAssistantCocktailsAdapter

        items = [
            {
                "title": "Gin Fizz",
                "content": "# Gin Fizz\n\n杜松子酒、柠檬汁、苏打水",
                "source_authority": "bar-assistant",
                "source_url": "https://example.com/gin-fizz",
                "refreshed_at": "2026-08-01T00:00:00",
                "license": "MIT",
                "category": "recipe",
                "glassware": "Highball",
                "technique": "Shake",
                "flavor_profile": "citrus",
                "verified": True,
            }
        ]
        monkeypatch.setattr(
            "hermes_kb.bar_assistant_sync.fetch_bar_assistant_cocktails",
            lambda: items,
        )
        adapter = BarAssistantCocktailsAdapter()
        result = adapter.fetch()
        assert result[0]["category"] == "recipe"
        assert result[0]["glassware"] == "Highball"
        assert result[0]["verified"] is True
        assert adapter.validate(result) == []

    def test_bar_assistant_ingredients_fetch(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import BarAssistantIngredientsAdapter

        items = [
            {
                "title": "Gin",
                "content": "# Gin\n\n杜松子酒原料档案",
                "source_authority": "bar-assistant",
                "source_url": "https://example.com/gin",
                "refreshed_at": None,
                "license": "MIT",
                "category": "ingredient_profile",
                "verified": False,
            }
        ]
        monkeypatch.setattr(
            "hermes_kb.bar_assistant_sync.fetch_bar_assistant_ingredients",
            lambda: items,
        )
        adapter = BarAssistantIngredientsAdapter()
        result = adapter.fetch()
        assert result[0]["category"] == "ingredient_profile"
        assert adapter.validate(result) == []


# ---------------------------------------------------------------------------
# API 适配器：validate + TheCocktailDB import
# ---------------------------------------------------------------------------
class TestApiAdapterValidate:
    @pytest.mark.parametrize(
        "adapter",
        [
            "wikidata",
            "crossref",
            "wikidata_cocktails",
            "wikipedia",
            "openfoodfacts",
            "usda_fooddata",
            "dbpedia",
            "bar_assistant_cocktails",
            "bar_assistant_ingredients",
        ],
    )
    def test_validate_detects_missing_fields(self, adapter):
        from hermes_kb.data_sources.registry import get_adapter

        inst = get_adapter(adapter)
        problems = inst.validate([{"title": "x"}])
        assert any("缺 title/content" in p for p in problems)

    def test_thecocktaildb_fetch_validate(self):
        from hermes_kb.data_sources.adapters.api import TheCocktailDBAdapter

        adapter = TheCocktailDBAdapter()
        assert adapter.fetch() == []
        assert adapter.validate([]) == []

    def test_thecocktaildb_import_data(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import TheCocktailDBAdapter
        from hermes_kb.rag import ImportService

        monkeypatch.setattr(
            "hermes_kb.thecocktaildb_sync.sync_thecocktaildb",
            lambda importer=None: {"imported": 3, "skipped": 2, "failed": 1},
        )
        result = TheCocktailDBAdapter().import_data(ImportService())
        assert result["imported"] == 3
        assert result["skipped"] == 2
        assert result["failed"] == 1

    def test_thecocktaildb_import_data_exception(self, monkeypatch):
        from hermes_kb.data_sources.adapters.api import TheCocktailDBAdapter
        from hermes_kb.rag import ImportService

        def boom(importer=None):
            raise RuntimeError("net down")

        monkeypatch.setattr(
            "hermes_kb.thecocktaildb_sync.sync_thecocktaildb", boom
        )
        result = TheCocktailDBAdapter().import_data(ImportService())
        assert result["imported"] == 0
        assert "net down" in result["errors"][0]


# ---------------------------------------------------------------------------
# API 适配器：剩余边界路径（wbgetentities 失败 / 上限 break / bar-assistant import）
# ---------------------------------------------------------------------------
class TestApiAdapterExtraPaths:
    def _patch_get(self, monkeypatch, responder):
        import hermes_kb.data_sources.adapters.api as api_mod

        def fake_get(url, headers=None):
            return responder(url, headers or {})

        monkeypatch.setattr(api_mod._ApiAdapter, "_get", staticmethod(fake_get))

    def test_wikidata_cocktails_wbgetentities_fail(self, monkeypatch):
        """wbgetentities 失败 → continue，仍以 QID 兜底构造条目。"""
        from hermes_kb.data_sources.adapters.api import WikidataCocktailsAdapter

        sparql = {
            "results": {
                "bindings": [
                    {"item": {"value": "http://www.wikidata.org/entity/Q123"}},
                ]
            }
        }

        def responder(url, headers):
            if "sparql" in url:
                return sparql
            raise RuntimeError("wbgetentities down")

        self._patch_get(monkeypatch, responder)
        items = WikidataCocktailsAdapter().fetch()
        assert items[0]["title"] == "Q123"

    def test_wikidata_cocktails_build_items_dict_alias(self):
        """词典翻译与中文标题不同时作为别名补充。"""
        from hermes_kb.data_sources.adapters.api import WikidataCocktailsAdapter

        ent = {
            "labels": {"zh": {"value": "琴費士"}, "en": {"value": "Gin Fizz"}},
            "aliases": {},
            "descriptions": {},
        }
        items = WikidataCocktailsAdapter()._build_items(["Q123"], {"Q123": ent})
        assert items[0]["title"] == "琴費士"
        assert "金菲士" in items[0]["content"]  # 词典别名

    def test_crossref_fetch_reaches_limit(self, monkeypatch):
        """达到 _MAX_ITEMS*2 上限时 break。"""
        from hermes_kb.data_sources.adapters.api import CrossrefAdapter

        data = {
            "message": {
                "items": [
                    {
                        "title": [f"Paper {i}"],
                        "DOI": f"10.1000/{i}",
                        "container-title": ["Journal"],
                        "abstract": "",
                    }
                    for i in range(20)
                ]
            }
        }
        self._patch_get(monkeypatch, lambda url, h: data)
        items = CrossrefAdapter().fetch()
        assert len(items) == 16  # _MAX_ITEMS * 2

    def test_wikipedia_fetch_reaches_limit(self, monkeypatch):
        """达到 _MAX_PER_SOURCE 上限时 break。"""
        from hermes_kb.data_sources.adapters.api import WikipediaAdapter

        long_extract = "这是一段足够长的中文百科正文。" * 30
        pages = {
            str(i): {"title": f"条目{i}", "extract": long_extract} for i in range(50)
        }
        self._patch_get(
            monkeypatch, lambda url, h: {"query": {"pages": pages}}
        )
        items = WikipediaAdapter().fetch()
        assert len(items) == 40  # _MAX_PER_SOURCE

    def test_usda_fooddata_requests_fail(self, monkeypatch):
        """所有请求抛异常 → 返回空列表。"""
        from hermes_kb.data_sources.adapters.api import USDAFoodDataAdapter

        def boom(url, headers):
            raise RuntimeError("net down")

        self._patch_get(monkeypatch, boom)
        assert USDAFoodDataAdapter().fetch() == []

    def test_usda_fooddata_reaches_limit(self, monkeypatch):
        """达到 _MAX_PER_SOURCE 上限时 break。"""
        from hermes_kb.data_sources.adapters.api import USDAFoodDataAdapter

        def food(i):
            return {
                "fdcId": i,
                "description": "Beer, regular, all varieties, with a fairly long "
                "descriptive text that ensures content length exceeds the "
                "minimum required threshold of one hundred characters",
                "foodNutrients": [
                    {"nutrientName": "Energy (kilocalories)", "amount": 43, "unitName": "KCAL"}
                ],
            }

        data = [food(i) for i in range(10)]
        self._patch_get(monkeypatch, lambda url, h: data)
        adapter = USDAFoodDataAdapter()
        adapter._MAX_PER_SOURCE = 2  # type: ignore[assignment]
        items = adapter.fetch()
        assert len(items) == 2

    def test_bar_assistant_cocktails_import_data(self, monkeypatch):
        """BarAssistantCocktailsAdapter 通用导入路径。"""
        from hermes_kb.data_sources.adapters.api import BarAssistantCocktailsAdapter
        from hermes_kb.rag import ImportService

        monkeypatch.setattr(
            "hermes_kb.bar_assistant_sync.fetch_bar_assistant_cocktails",
            lambda: [
                {
                    "title": "Gin Fizz",
                    "content": "# Gin Fizz\n\n杜松子酒、柠檬汁、苏打水",
                    "source_authority": "bar-assistant",
                    "source_url": "https://example.com/gin-fizz",
                    "refreshed_at": None,
                    "license": "MIT",
                    "category": "recipe",
                    "glassware": "",
                    "technique": "",
                    "flavor_profile": "",
                    "verified": True,
                }
            ],
        )
        result = BarAssistantCocktailsAdapter().import_data(ImportService())
        assert result["imported"] == 1

    def test_bar_assistant_ingredients_import_data(self, monkeypatch):
        """BarAssistantIngredientsAdapter 通用导入路径。"""
        from hermes_kb.data_sources.adapters.api import BarAssistantIngredientsAdapter
        from hermes_kb.rag import ImportService

        monkeypatch.setattr(
            "hermes_kb.bar_assistant_sync.fetch_bar_assistant_ingredients",
            lambda: [
                {
                    "title": "Gin",
                    "content": "# Gin\n\n杜松子酒原料档案",
                    "source_authority": "bar-assistant",
                    "source_url": "https://example.com/gin",
                    "refreshed_at": None,
                    "license": "MIT",
                    "category": "ingredient_profile",
                    "verified": False,
                }
            ],
        )
        result = BarAssistantIngredientsAdapter().import_data(ImportService())
        assert result["imported"] == 1





