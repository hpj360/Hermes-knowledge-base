"""IBA dataset importer 测试（B3）。"""
from __future__ import annotations

import pytest
from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document


def test_parse_iba_recipe_basic():
    """B3: 解析 IBA dataset 单条配方。"""
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "MOJITO",
        "ingredients": [
            {"name": "white rum", "quantity": 4.5},
            {"name": "lime juice", "quantity": 2.0},
            {"name": "sugar syrup", "quantity": 1.5},
            {"name": "soda water", "quantity": None},
            {"name": "mint", "quantity": None},
        ],
        "type": "Contemporary Classics",
    }
    recipe = parse_iba_recipe(raw)
    assert recipe["title"] == "MOJITO"
    assert recipe["source"] == "iba"
    assert recipe["verified"] is True
    assert "白朗姆酒" in recipe["ingredients"]
    assert "青柠汁" in recipe["ingredients"]
    assert recipe["category_official"] == "Contemporary Classics"
    # content 应含 frontmatter
    assert "<!-- ingredients:" in recipe["content"]


def test_parse_iba_recipe_unit_conversion():
    """B3: cl → ml 单位转换。"""
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "TEST",
        "ingredients": [
            {"name": "gin", "quantity": 6.0},
        ],
        "type": "Test",
    }
    recipe = parse_iba_recipe(raw)
    # 6cl → 60ml
    assert "60ml" in recipe["content"]


def test_parse_iba_recipe_unknown_ingredient():
    """B3: 未归一化材料保留英文原名。"""
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "SPECIAL",
        "ingredients": [
            {"name": "gin", "quantity": 4.5},
            {"name": "some rare liqueur", "quantity": 1.0},
        ],
        "type": "Special",
    }
    recipe = parse_iba_recipe(raw)
    assert "金酒" in recipe["ingredients"]
    # 未归一化的应在 unknown_ingredients
    assert "some rare liqueur" in recipe["unknown_ingredients"]


def test_parse_iba_recipe_strength_data_fallback_abv():
    """B3: strength_data 提供兜底 ABV，避免未知材料被当成 0.0 拉低计算。

    场景：'mystery liqueur' 不在本地 ingredients.py 别名索引，
    但 strength_data 给出 0.25，应被采用参与加权 ABV 计算。
    """
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "FALLBACK TEST",
        "ingredients": [
            {"name": "gin", "quantity": 4.5},  # 本地 0.40, 45ml
            {"name": "mystery liqueur", "quantity": 1.5},  # 本地未知, 15ml
        ],
        "type": "Test",
    }

    # 无 strength_data：mystery liqueur ABV=0.0
    recipe_no_fallback = parse_iba_recipe(raw, strength_data=None)
    # 加权: (0.40*45 + 0*15) / 60 = 18/60 = 0.30
    assert recipe_no_fallback["abv"] is not None
    assert recipe_no_fallback["abv"] == pytest.approx(0.30, abs=1e-3)

    # 有 strength_data：mystery liqueur ABV=0.25
    recipe_with_fallback = parse_iba_recipe(
        raw, strength_data={"mystery liqueur": 0.25}
    )
    # 加权: (0.40*45 + 0.25*15) / 60 = (18 + 3.75) / 60 = 0.3625
    assert recipe_with_fallback["abv"] is not None
    assert recipe_with_fallback["abv"] == pytest.approx(0.3625, abs=1e-3)
    # calories 也应更高
    assert recipe_with_fallback["calories"] > recipe_no_fallback["calories"]


def test_parse_iba_recipe_abv_calc_exception_logged(monkeypatch, caplog):
    """B3: ABV 计算抛异常时应记录 warning 而非静默吞并。"""
    from hermes_kb import iba_dataset_importer

    # 让 ingredient_strength.calculate_cocktail_abv 抛异常
    def boom(*args, **kwargs):
        raise RuntimeError("calc boom")

    # 模块内 import 是函数级 lazy import，patch 顶层模块即可
    import hermes_kb.ingredient_strength as is_mod

    monkeypatch.setattr(is_mod, "calculate_cocktail_abv", boom)

    raw = {
        "name": "BOOM TEST",
        "ingredients": [{"name": "gin", "quantity": 4.5}],
        "type": "Test",
    }

    import logging

    with caplog.at_level(logging.WARNING, logger="hermes_kb.iba_dataset_importer"):
        recipe = iba_dataset_importer.parse_iba_recipe(raw)

    # ABV 应为 None（计算失败），content 不应含 abv frontmatter
    assert recipe["abv"] is None
    assert "<!-- abv:" not in recipe["content"]
    # 应有 warning 日志
    assert any("ABV/calories calc failed" in r.message for r in caplog.records)


def test_sync_iba_dataset_with_mock_data():
    """B3: 用 mock 数据导入 IBA 配方。"""
    from hermes_kb.iba_dataset_importer import sync_iba_dataset

    mock_data = [
        {
            "name": "NEGRONI",
            "ingredients": [
                {"name": "gin", "quantity": 3.0},
                {"name": "campari", "quantity": 3.0},
                {"name": "sweet vermouth", "quantity": 3.0},
            ],
            "type": "Contemporary Classics",
        },
        {
            "name": "OLD FASHIONED",
            "ingredients": [
                {"name": "bourbon", "quantity": 6.0},
                {"name": "sugar", "quantity": None},
                {"name": "angostura bitters", "quantity": None},
            ],
            "type": "The Unforgettables",
        },
    ]

    result = sync_iba_dataset(data=mock_data)
    assert result["imported"] == 2
    assert result["skipped"] == 0

    # 验证导入
    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.source == "iba")
        ).all()
        assert len(docs) == 2
        titles = {d.title for d in docs}
        assert "NEGRONI" in titles
        assert "OLD FASHIONED" in titles
        # verified 应为 True（IBA 金标准）
        assert all(d.verified for d in docs)

    # 再次同步应去重
    result2 = sync_iba_dataset(data=mock_data)
    assert result2["imported"] == 0
    assert result2["skipped"] == 2


def test_sync_iba_dataset_dedup_with_seed():
    """B3: 与种子配方去重（按 title 模糊匹配）。"""
    from hermes_kb.database import get_session
    from hermes_kb.iba_dataset_importer import sync_iba_dataset
    from hermes_kb.models import Document
    from hermes_kb.rag import ImportService
    from hermes_kb.seed_recipes import SEED_RECIPES

    # 先播种种子（含 莫吉托 Mojito）。seed_recipes 模块未提供 seed_all，
    # 这里复用 ImportService + SEED_RECIPES 内联播种（与 /api/seed/recipes 同逻辑）。
    importer = ImportService()
    for recipe in SEED_RECIPES:
        result = importer.import_text(
            content=recipe["content"],
            title=recipe["title"],
            source_type="seed",
            file_type="md",
        )
        doc_id = result.get("doc_id") if isinstance(result, dict) else result
        if doc_id:
            with get_session() as session:
                doc = session.get(Document, doc_id)
                if doc:
                    doc.category = "recipe"
                    session.add(doc)
                    session.commit()

    mock_data = [
        {
            "name": "Mojito",  # 与种子 "莫吉托 Mojito" 模糊匹配
            "ingredients": [
                {"name": "white rum", "quantity": 4.5},
                {"name": "lime juice", "quantity": 2.0},
            ],
            "type": "Contemporary Classics",
        },
        {
            # 完全虚构配方名，避免与 57 款 IBA 全量种子去重
            "name": "TEST UNIQUE RECIPE X",
            "ingredients": [
                {"name": "gin", "quantity": 4.5},
                {"name": "lime juice", "quantity": 2.0},
                {"name": "sugar syrup", "quantity": 1.5},
            ],
            "type": "Contemporary Classics",
        },
    ]

    result = sync_iba_dataset(data=mock_data)
    # Mojito 应被去重（与种子模糊匹配）
    # TEST UNIQUE RECIPE X 应导入
    # 注意：种子已扩展至 57 款 IBA 全量，常见 IBA 名均会去重，
    # 故使用虚构名确保 imported >= 1
    assert result["imported"] >= 1
    assert result["skipped"] >= 1


def test_sync_iba_dataset_empty_data():
    """B3: 空数据应返回空结果。"""
    from hermes_kb.iba_dataset_importer import sync_iba_dataset

    result = sync_iba_dataset(data=[])
    assert result["imported"] == 0
    assert result["skipped"] == 0


def test_diff_iba_official_basic():
    """G3: 用 mock local + official data 测试 diff 逻辑。"""
    from hermes_kb.iba_dataset_importer import diff_iba_official

    local_data = [
        {"title": "Negroni"},
        {"title": "Mojito"},
        {"title": "Old Fashioned"},
    ]
    official_data = [
        {"name": "Negroni", "ingredients": [], "type": "The Unforgettables"},
        {"name": "Mojito", "ingredients": [], "type": "Contemporary Classics"},
        {"name": "Daiquiri", "ingredients": [], "type": "Contemporary Classics"},
    ]

    result = diff_iba_official(local_data=local_data, official_data=official_data)

    assert result["local_count"] == 3
    assert result["official_count"] == 3
    # 两边都有的
    assert result["matched"] == ["mojito", "negroni"]
    # 官方有但本地没有
    assert result["missing_locally"] == ["daiquiri"]
    # 本地有但官方没有
    assert result["extra_locally"] == ["old fashioned"]


def test_diff_iba_official_network_fail(monkeypatch):
    """G3: 网络失败时返回结构正确（official_count=0, missing_locally=[]）。"""
    from hermes_kb import iba_dataset_importer

    # 模拟远程拉取失败（返回空列表）
    monkeypatch.setattr(iba_dataset_importer, "_fetch_remote_data", list)

    local_data = [{"title": "Negroni"}, {"title": "Mojito"}]
    result = iba_dataset_importer.diff_iba_official(
        local_data=local_data, official_data=None
    )

    # 结构完整
    assert set(result.keys()) == {
        "local_count",
        "official_count",
        "missing_locally",
        "extra_locally",
        "matched",
    }
    assert result["official_count"] == 0
    assert result["missing_locally"] == []
    assert result["local_count"] == 2
    # 本地全部算作 extra
    assert sorted(result["extra_locally"]) == ["mojito", "negroni"]
    assert result["matched"] == []


def test_normalize_ingredient_empty_string():
    """空字符串返回 ('', True)。"""
    from hermes_kb.iba_dataset_importer import _normalize_ingredient

    assert _normalize_ingredient("") == ("", True)
    assert _normalize_ingredient(None) == ("", True)  # type: ignore[arg-type]


def test_normalize_ingredient_unknown():
    """未知材料返回 (原名, True)。"""
    from hermes_kb.iba_dataset_importer import _normalize_ingredient

    norm, unknown = _normalize_ingredient("some rare liqueur")
    assert norm == "some rare liqueur"
    assert unknown is True


def test_normalize_ingredient_known():
    """已知材料返回 (canonical, False)。"""
    from hermes_kb.iba_dataset_importer import _normalize_ingredient

    norm, unknown = _normalize_ingredient("white rum")
    assert norm == "白朗姆酒"
    assert unknown is False


def test_normalize_ingredient_collapses_whitespace():
    """多空格/非断空格被合并。"""
    from hermes_kb.iba_dataset_importer import _normalize_ingredient

    # 双空格 + 非断空格
    norm, _ = _normalize_ingredient("white\u00a0rum")
    assert norm == "白朗姆酒"


def test_parse_iba_recipe_empty_ingredient_name():
    """空材料名安全跳过。"""
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "TEST EMPTY ING",
        "ingredients": [
            {"name": "", "quantity": 4.5},  # 空名
            {"name": "gin", "quantity": 4.5},
        ],
        "type": "Test",
    }
    recipe = parse_iba_recipe(raw)
    # 空名不会进 unknown_ingredients
    assert "" not in recipe["unknown_ingredients"]
    # gin 仍然被正确归一化
    assert "金酒" in recipe["ingredients"]


def test_parse_iba_recipe_invalid_quantity_skipped():
    """非数字 quantity 被安全跳过（不影响 ABV 计算）。"""
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "BAD QTY",
        "ingredients": [
            {"name": "gin", "quantity": "not-a-number"},  # 非数字
            {"name": "vodka", "quantity": 4.5},  # 45ml, 0.40
        ],
        "type": "Test",
    }
    recipe = parse_iba_recipe(raw)
    # measures 中 gin 显示 'nanml'（float('not-a-number') 会抛 ValueError）
    # 但 vodka 仍参与 ABV 计算
    assert recipe["abv"] is not None
    # vodka 单独参与 → 0.40
    assert recipe["abv"] == pytest.approx(0.40, abs=1e-3)


def test_parse_iba_recipe_no_ingredients():
    """ingredients 为空列表时不抛异常。"""
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {"name": "EMPTY", "ingredients": [], "type": "Test"}
    recipe = parse_iba_recipe(raw)
    assert recipe["title"] == "EMPTY"
    assert recipe["ingredients"] == []
    assert recipe["abv"] is None
    assert recipe["calories"] is None
    # content 不应含 abv/calories frontmatter
    assert "<!-- abv:" not in recipe["content"]
    assert "<!-- calories:" not in recipe["content"]


def test_normalize_title_empty():
    """空标题返回空字符串。"""
    from hermes_kb.iba_dataset_importer import _normalize_title

    assert _normalize_title("") == ""
    assert _normalize_title(None) == ""  # type: ignore[arg-type]


def test_normalize_title_strips_punctuation():
    """标点符号被剥离（& 不在剥离列表中，保留）。"""
    from hermes_kb.iba_dataset_importer import _normalize_title

    assert _normalize_title("Mojito!") == "mojito"
    assert _normalize_title("Old-Fashioned") == "oldfashioned"
    # & 不在正则 [\s\-_/\\,.!?;:'\"()] 里，故保留
    assert _normalize_title("Gin & Tonic") == "gin&tonic"
    # 多种标点
    assert _normalize_title("Test, Drink; (v2)") == "testdrinkv2"


def test_tokenize_title_empty():
    """空标题返回空 frozenset。"""
    from hermes_kb.iba_dataset_importer import _tokenize_title

    assert _tokenize_title("") == frozenset()
    assert _tokenize_title(None) == frozenset()  # type: ignore[arg-type]


def test_tokenize_title_extracts_tokens():
    """标题被分词为 token 集合。"""
    from hermes_kb.iba_dataset_importer import _tokenize_title

    toks = _tokenize_title("Old Fashioned 123")
    assert "old" in toks
    assert "fashioned" in toks
    assert "123" in toks
    # 中文 token
    toks_zh = _tokenize_title("莫吉托 mojito")
    assert "莫吉托" in toks_zh
    assert "mojito" in toks_zh


def test_is_duplicate_fuzzy_empty_candidate():
    """空候选标题返回 False。"""
    from hermes_kb.iba_dataset_importer import _is_duplicate_fuzzy

    assert _is_duplicate_fuzzy("", set(), set(), []) is False
    assert _is_duplicate_fuzzy(None, set(), set(), []) is False  # type: ignore[arg-type]


def test_is_duplicate_fuzzy_short_norm():
    """规范化后长度 <4 不参与模糊匹配。"""
    from hermes_kb.iba_dataset_importer import _is_duplicate_fuzzy

    # 'abc' 长度 3，不参与 token 模糊匹配
    assert _is_duplicate_fuzzy("abc", set(), set(), []) is False


def test_is_duplicate_fuzzy_exact_match():
    """精确匹配返回 True。"""
    from hermes_kb.iba_dataset_importer import _is_duplicate_fuzzy

    # 'mojito' 在 iba_exact 中
    assert _is_duplicate_fuzzy("Mojito", {"mojito"}, set(), []) is True
    # 'negroni' 在 recipe_exact 中
    assert _is_duplicate_fuzzy("Negroni", set(), {"negroni"}, []) is True


def test_is_duplicate_fuzzy_token_subset():
    """token 子集匹配返回 True。"""
    from hermes_kb.iba_dataset_importer import _is_duplicate_fuzzy

    # 现有 token 集合 {old, fashioned}
    existing = [frozenset({"old", "fashioned"})]
    # 候选 'old fashioned' tokens {old, fashioned} ⊆ existing
    assert _is_duplicate_fuzzy("Old Fashioned", set(), set(), existing) is True
    # 候选 'old fashioned v2' tokens 是 existing 的超集
    assert _is_duplicate_fuzzy("Old Fashioned V2", set(), set(), existing) is True
    # 不相关候选
    assert _is_duplicate_fuzzy("Mojito Recipe", set(), set(), existing) is False


def test_is_duplicate_fuzzy_no_existing_tokens():
    """existing_token_list 含空 frozenset 时不抛异常（continue 跳过）。"""
    from hermes_kb.iba_dataset_importer import _is_duplicate_fuzzy

    # existing_tokens 含空集（被 continue 跳过），不相关候选返回 False
    existing = [frozenset(), frozenset({"negroni"})]
    assert _is_duplicate_fuzzy("Mojito Recipe", set(), set(), existing) is False
    # 候选 'negroni' 命中 existing 非空集
    assert _is_duplicate_fuzzy("Negroni", set(), set(), existing) is True


def test_sync_iba_dataset_with_invalid_recipe_records_failed():
    """解析失败的配方计入 failed。"""
    from hermes_kb.iba_dataset_importer import sync_iba_dataset

    # name 字段缺失会让 parse_iba_recipe 返回 title=""，sync 仍会处理
    # 但 import_text 会失败（无标题）→ failed
    mock_data = [
        {"name": "VALID RECIPE X", "ingredients": [], "type": "T"},
        # 故意构造一个会让 parse_iba_recipe 抛异常的对象
        "not-a-dict",  # type: ignore[list-item]
    ]

    result = sync_iba_dataset(data=mock_data)
    # 'not-a-dict' 会让 .get 抛 AttributeError，被 except 捕获，failed += 1
    assert result["failed"] >= 1


def test_fetch_remote_data_direct_success(monkeypatch):
    """_fetch_remote_data 直连 GitHub 成功时返回 dict 列表。"""
    from hermes_kb import iba_dataset_importer


    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"name": "Mojito", "ingredients": [], "type": "Test"}]

    def fake_get(url, timeout):
        assert "raw.githubusercontent.com" in url
        assert "/master/" in url
        return FakeResp()

    monkeypatch.setattr(iba_dataset_importer.httpx, "get", fake_get)
    result = iba_dataset_importer._fetch_remote_data()
    assert result == [{"name": "Mojito", "ingredients": [], "type": "Test"}]


def test_fetch_remote_data_mirror_success(monkeypatch):
    """直连失败但 gh-proxy 镜像成功时返回镜像数据。"""
    import httpx

    from hermes_kb import iba_dataset_importer


    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"name": "Negroni", "ingredients": [], "type": "Test"}]

    call_count = {"n": 0}

    def fake_get(url, timeout):
        call_count["n"] += 1
        # 直连 GitHub 两次（master + main）都失败
        if "gh-proxy.com" not in url:
            raise httpx.HTTPError("direct blocked")
        return FakeResp()

    monkeypatch.setattr(iba_dataset_importer.httpx, "get", fake_get)
    result = iba_dataset_importer._fetch_remote_data()
    assert result == [{"name": "Negroni", "ingredients": [], "type": "Test"}]
    # 至少 3 次（2 次直连 + 1 次镜像）
    assert call_count["n"] >= 3


def test_fetch_remote_data_local_fallback(monkeypatch, tmp_path):
    """所有远程都失败时回退本地 data/iba_recipes.json。"""
    import json

    import httpx

    from hermes_kb import iba_dataset_importer

    def fake_get(url, timeout):
        raise httpx.HTTPError("all network down")

    monkeypatch.setattr(iba_dataset_importer.httpx, "get", fake_get)

    # 写一个临时本地文件并 patch Path.exists / open 让 _fetch_remote_data 读到它
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    local_file = data_dir / "iba_recipes.json"
    local_file.write_text(
        json.dumps([{"name": "LOCAL FALLBACK", "ingredients": [], "type": "T"}]),
        encoding="utf-8",
    )

    import pathlib

    real_exists = pathlib.Path.exists

    def patched_exists(self):
        if str(self).endswith("iba_recipes.json"):
            return True
        return real_exists(self)

    real_open = open

    def patched_open(path, *args, **kwargs):
        if str(path).endswith("iba_recipes.json"):
            return real_open(local_file, *args, **kwargs)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "exists", patched_exists)
    monkeypatch.setattr("builtins.open", patched_open)

    result = iba_dataset_importer._fetch_remote_data()
    assert result == [{"name": "LOCAL FALLBACK", "ingredients": [], "type": "T"}]


def test_fetch_remote_data_all_fail_returns_empty(monkeypatch):
    """所有远程失败 + 无本地文件 → 返回空列表。"""
    import pathlib

    import httpx

    from hermes_kb import iba_dataset_importer

    def fake_get(url, timeout):
        raise httpx.HTTPError("all down")

    monkeypatch.setattr(iba_dataset_importer.httpx, "get", fake_get)
    # 让所有 Path.exists 返回 False（无本地文件）
    monkeypatch.setattr(pathlib.Path, "exists", lambda self: False)

    result = iba_dataset_importer._fetch_remote_data()
    assert result == []


def test_diff_iba_official_with_db_local(tmp_db):
    """local_data=None 时从 DB 查询本地 IBA 配方。"""
    from hermes_kb.database import get_session
    from hermes_kb.iba_dataset_importer import diff_iba_official
    from hermes_kb.models import Document
    from hermes_kb.rag import ImportService

    # 播种一条 IBA 配方到 DB
    importer = ImportService()
    importer.import_text(
        content="# Mojito\n\n## 配方\n- 白朗姆酒 45ml",
        title="Mojito",
        source_type="iba",
        file_type="md",
    )
    with get_session() as session:
        docs = session.exec(
            __import__("sqlmodel").select(Document).where(Document.title == "Mojito")
        ).all()
        for d in docs:
            d.source = "iba"
            d.category = "recipe"
            session.add(d)
        session.commit()

    official = [{"name": "Mojito"}, {"name": "Daiquiri"}]
    result = diff_iba_official(local_data=None, official_data=official)

    assert result["local_count"] == 1
    assert result["official_count"] == 2
    assert "mojito" in result["matched"]
    assert "daiquiri" in result["missing_locally"]


def test_diff_iba_official_handles_non_dict_items():
    """diff 时遇到非 dict 项不抛异常（_title_of 返回空字符串）。"""
    from hermes_kb.iba_dataset_importer import diff_iba_official

    local_data = [{"title": "Mojito"}, "not-a-dict", 123, None]
    official_data = [{"name": "Mojito"}, {"name": "Negroni"}]

    result = diff_iba_official(local_data=local_data, official_data=official_data)
    # 非 dict 项被 _title_of 安全跳过
    assert result["local_count"] == 1
    assert result["official_count"] == 2
    assert "mojito" in result["matched"]
    assert "negroni" in result["missing_locally"]


def test_parse_iba_recipe_maps_iba_category():
    """Task 7.4: IBA dataset 的 type 字段映射为 iba_category。"""
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "TEST UNFORGETTABLES",
        "ingredients": [
            {"name": "gin", "quantity": 4.5},
            {"name": "lemon juice", "quantity": 1.5},
        ],
        "type": "The Unforgettables",
    }
    recipe = parse_iba_recipe(raw)
    assert recipe["iba_category"] == "unforgettables"

    # Contemporary Classics
    raw_contemporary = {
        "name": "TEST CONTEMPORARY",
        "ingredients": [{"name": "gin", "quantity": 4.5}],
        "type": "Contemporary Classics",
    }
    assert parse_iba_recipe(raw_contemporary)["iba_category"] == "contemporary_classics"

    # New Era Drinks
    raw_new_era = {
        "name": "TEST NEW ERA",
        "ingredients": [{"name": "gin", "quantity": 4.5}],
        "type": "New Era Drinks",
    }
    assert parse_iba_recipe(raw_new_era)["iba_category"] == "new_era_drinks"

    # 未知 type 返回默认分类 contemporary_classics（infer_iba_category 的默认值）
    raw_unknown = {
        "name": "TEST UNKNOWN TYPE",
        "ingredients": [{"name": "gin", "quantity": 4.5}],
        "type": "Some Unknown Category",
    }
    assert parse_iba_recipe(raw_unknown)["iba_category"] == "contemporary_classics"


def test_parse_iba_recipe_infers_technique():
    """Task 7.4: 当 content 含 shake 关键词时推断 technique='shake'。

    IBA dataset 原始数据无 instructions，content 主要由材料列表 + 标题 + 分类构成。
    本测试构造 title 含 "shake"（被拼入 content 的 H1 标题），触发 infer_technique。
    """
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "SHAKE TEST RECIPE",  # 标题含 "shake"，content 包含 "# SHAKE TEST RECIPE"
        "ingredients": [
            {"name": "gin", "quantity": 4.5},
            {"name": "lemon juice", "quantity": 1.5},
        ],
        "type": "Contemporary Classics",
    }
    recipe = parse_iba_recipe(raw)
    assert recipe["technique"] == "shake"

    # 普通配方（无技法关键词）technique 应为空
    raw_no_technique = {
        "name": "PLAIN RECIPE XYZ",
        "ingredients": [
            {"name": "gin", "quantity": 4.5},
            {"name": "lemon juice", "quantity": 1.5},
        ],
        "type": "Contemporary Classics",
    }
    assert parse_iba_recipe(raw_no_technique)["technique"] == ""


def test_parse_iba_recipe_infers_glassware():
    """Task 7.4: 当 content 含 "martini glass" 时推断 glassware='马天尼杯'。

    构造 title 含 "Martini Glass"（被拼入 content 的 H1 标题），触发 infer_glassware。
    """
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "MARTINI GLASS TEST",
        "ingredients": [
            {"name": "gin", "quantity": 4.5},
            {"name": "dry vermouth", "quantity": 1.5},
        ],
        "type": "The Unforgettables",
    }
    recipe = parse_iba_recipe(raw)
    assert recipe["glassware"] == "马天尼杯"

    # 普通 mock 配方（无载杯关键词）glassware 应为空
    raw_no_glass = {
        "name": "PLAIN RECIPE XYZ",
        "ingredients": [{"name": "gin", "quantity": 4.5}],
        "type": "Contemporary Classics",
    }
    assert parse_iba_recipe(raw_no_glass)["glassware"] == ""


def test_parse_iba_recipe_returns_metadata():
    """Task 7.4: 完整断言返回 dict 包含 technique/glassware/iba_category/flavor_profile 四字段。"""
    from hermes_kb.iba_dataset_importer import parse_iba_recipe

    raw = {
        "name": "MARTINI GLASS SHAKE TEST",
        "ingredients": [
            {"name": "gin", "quantity": 4.5},
            {"name": "lemon juice", "quantity": 1.5},
            {"name": "sugar syrup", "quantity": 1.0},
        ],
        "type": "The Unforgettables",
    }
    recipe = parse_iba_recipe(raw)
    # 四字段必须存在
    assert "technique" in recipe
    assert "glassware" in recipe
    assert "iba_category" in recipe
    assert "flavor_profile" in recipe
    # 具体值断言
    assert recipe["technique"] == "shake"  # title 含 "shake"
    assert recipe["glassware"] == "马天尼杯"  # title 含 "martini glass"
    assert recipe["iba_category"] == "unforgettables"
    # flavor_profile：gin/lemon juice/sugar syrup 都有 tags（如 citrus/sweet）
    assert recipe["flavor_profile"] != ""
    # 向后兼容：旧字段仍存在
    assert recipe["source"] == "iba"
    assert recipe["verified"] is True
    assert "content" in recipe
    assert "ingredients" in recipe
    assert "category_official" in recipe


def test_sync_iba_dataset_skips_seed_recipes():
    """Task 7.4: 同步时跳过种子已有的配方（基于 _is_duplicate_fuzzy 模糊匹配）。

    场景：先调用 seed_recipes() 导入 57 款 IBA 种子（含 "莫吉托 Mojito"），
    再调用 sync_iba_dataset 同步含 "Mojito" 的 mock 数据，应被识别为 duplicate。
    """
    from hermes_kb.iba_dataset_importer import sync_iba_dataset
    from hermes_kb.seed import seed_recipes

    # 1. 导入种子配方（含 "莫吉托 Mojito"）
    seed_result = seed_recipes()
    assert seed_result["seeded"] >= 1  # 至少导入了一些

    # 2. 构造 mock IBA 数据：包含 "Mojito"（与种子 "莫吉托 Mojito" 模糊匹配）
    #    以及一个虚构配方（确保 imported >= 1）
    mock_data = [
        {
            "name": "Mojito",  # 种子已有 → 应被去重 skip
            "ingredients": [
                {"name": "white rum", "quantity": 4.5},
                {"name": "lime juice", "quantity": 2.0},
                {"name": "sugar syrup", "quantity": 1.5},
            ],
            "type": "Contemporary Classics",
        },
        {
            # 完全虚构配方名，避免与 57 款 IBA 种子模糊匹配
            "name": "TEST UNIQUE RECIPE XYZ",
            "ingredients": [
                {"name": "gin", "quantity": 4.5},
                {"name": "lemon juice", "quantity": 2.0},
                {"name": "sugar syrup", "quantity": 1.5},
            ],
            "type": "Contemporary Classics",
        },
    ]

    result = sync_iba_dataset(data=mock_data)
    # Mojito 应被去重 → skipped >= 1
    assert result["skipped"] >= 1, (
        f"应跳过种子已有的 Mojito，实际 skipped={result['skipped']}"
    )
    # 虚构配方应导入 → imported >= 1
    assert result["imported"] >= 1, (
        f"应导入虚构配方，实际 imported={result['imported']}"
    )
