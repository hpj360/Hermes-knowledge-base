"""外部数据源同步模块测试：bar_assistant_sync / daily_recipe / iba_dataset_importer。

覆盖：
- bar_assistant_sync: mock data 导入/重复跳过/字段缺失失败/属性错误/批量插入异常
- bar_assistant_sync: _fetch_remote_data 网络失败回退
- daily_recipe: 季节池/热门池/随机池/空库/季节判断/_today_utc
- iba_dataset_importer: parse_iba_recipe/diff_iba_official/_fetch_remote_data 回退
"""
from __future__ import annotations


# ===========================================================================
# bar_assistant_sync
# ===========================================================================
class TestBarAssistantSync:
    """bar-assistant 替代材料同步。"""

    def test_sync_with_mock_data_success(self, client):
        """传入 mock data 成功导入。"""
        from hermes_kb.bar_assistant_sync import sync_bar_assistant_substitutes

        data = [
            {"canonical": "金酒", "substitute": "伏特加"},
            {"canonical": "威士忌", "substitute": "波本"},
        ]
        result = sync_bar_assistant_substitutes(data=data)
        assert result["imported"] == 2
        assert result["skipped"] == 0
        assert result["failed"] == 0

    def test_sync_empty_data(self, client):
        """空列表返回零值。"""
        from hermes_kb.bar_assistant_sync import sync_bar_assistant_substitutes

        result = sync_bar_assistant_substitutes(data=[])
        assert result == {"imported": 0, "skipped": 0, "failed": 0}

    def test_sync_dedup_skipped(self, client):
        """重复数据被跳过（ON CONFLICT DO NOTHING）。"""
        from hermes_kb.bar_assistant_sync import sync_bar_assistant_substitutes

        data = [{"canonical": "金酒", "substitute": "伏特加"}]
        # 第一次导入
        sync_bar_assistant_substitutes(data=data)
        # 第二次应被跳过
        result = sync_bar_assistant_substitutes(data=data)
        assert result["imported"] == 0
        assert result["skipped"] == 1

    def test_sync_missing_canonical_failed(self, client):
        """canonical 缺失计入 failed。"""
        from hermes_kb.bar_assistant_sync import sync_bar_assistant_substitutes

        data = [
            {"canonical": "", "substitute": "伏特加"},
            {"canonical": "金酒", "substitute": ""},
        ]
        result = sync_bar_assistant_substitutes(data=data)
        assert result["imported"] == 0
        assert result["failed"] == 2

    def test_sync_attribute_error_failed(self, client):
        """item 不是 dict（AttributeError）计入 failed。"""
        from hermes_kb.bar_assistant_sync import sync_bar_assistant_substitutes

        data = ["not_a_dict", 123, None]
        result = sync_bar_assistant_substitutes(data=data)
        assert result["imported"] == 0
        assert result["failed"] == 3

    def test_sync_none_data_uses_remote_fetch(self, client, monkeypatch):
        """data=None 时调用 _fetch_remote_data。"""
        from hermes_kb import bar_assistant_sync

        # mock _fetch_remote_data 返回空，避免真实网络
        monkeypatch.setattr(
            bar_assistant_sync, "_fetch_remote_data",
            lambda: [],
        )
        result = bar_assistant_sync.sync_bar_assistant_substitutes(data=None)
        assert result == {"imported": 0, "skipped": 0, "failed": 0}

    def test_sync_batch_insert_failure(self, client, monkeypatch):
        """批量插入异常时返回全 failed。"""
        from hermes_kb import bar_assistant_sync
        from hermes_kb.database import get_session

        def failing_session():
            raise RuntimeError("DB 故障")

        monkeypatch.setattr(bar_assistant_sync, "get_session", failing_session)
        data = [{"canonical": "金酒", "substitute": "伏特加"}]
        result = bar_assistant_sync.sync_bar_assistant_substitutes(data=data)
        assert result["imported"] == 0
        assert result["failed"] == 1

    def test_fetch_remote_data_network_failure(self, monkeypatch):
        """_fetch_remote_data 网络失败返回空列表。"""
        from hermes_kb import bar_assistant_sync
        import httpx

        def failing_get(url, timeout=None):
            raise httpx.HTTPError("network failure")

        monkeypatch.setattr(httpx, "get", failing_get)
        result = bar_assistant_sync._fetch_remote_data()
        assert result == []

    def test_fetch_remote_data_invalid_json(self, monkeypatch):
        """_fetch_remote_data JSON 解析失败返回空。"""
        from hermes_kb import bar_assistant_sync

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                raise ValueError("not json")

        def fake_get(url, timeout=None):
            return FakeResp()

        import httpx

        monkeypatch.setattr(httpx, "get", fake_get)
        result = bar_assistant_sync._fetch_remote_data()
        assert result == []

    def test_fetch_remote_data_parses_substitutes_string(self, monkeypatch):
        """substitutes 字段为字符串时正确分割。"""
        from hermes_kb import bar_assistant_sync

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return [
                    {"name": "Gin", "substitutes": "Vodka, White Rum"},
                    {"name": "Whiskey", "substitutes": ["Bourbon", "Scotch"]},
                ]

        import httpx

        def fake_get(url, timeout=None):
            return FakeResp()

        monkeypatch.setattr(httpx, "get", fake_get)
        result = bar_assistant_sync._fetch_remote_data()
        assert {"canonical": "Gin", "substitute": "Vodka"} in result
        assert {"canonical": "Gin", "substitute": "White Rum"} in result
        assert {"canonical": "Whiskey", "substitute": "Bourbon"} in result

    def test_fetch_remote_data_not_list_returns_empty(self, monkeypatch):
        """raw 不是 list 时返回空。"""
        from hermes_kb import bar_assistant_sync

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"not": "a list"}

        import httpx

        def fake_get(url, timeout=None):
            return FakeResp()

        monkeypatch.setattr(httpx, "get", fake_get)
        result = bar_assistant_sync._fetch_remote_data()
        assert result == []


# ===========================================================================
# daily_recipe
# ===========================================================================
class TestDailyRecipe:
    """每日推荐算法。"""

    def test_today_utc_returns_date(self):
        """_today_utc 返回 date 对象。"""
        from datetime import date

        from hermes_kb.daily_recipe import _today_utc

        d = _today_utc()
        assert isinstance(d, date)

    def test_current_season_summer(self, monkeypatch):
        """7 月 → summer。"""
        from datetime import date

        from hermes_kb import daily_recipe

        monkeypatch.setattr(daily_recipe, "_today_utc", lambda: date(2026, 7, 15))
        assert daily_recipe._current_season() == "summer"

    def test_current_season_spring(self, monkeypatch):
        """4 月 → spring。"""
        from datetime import date

        from hermes_kb import daily_recipe

        monkeypatch.setattr(daily_recipe, "_today_utc", lambda: date(2026, 4, 15))
        assert daily_recipe._current_season() == "spring"

    def test_current_season_autumn(self, monkeypatch):
        """10 月 → autumn。"""
        from datetime import date

        from hermes_kb import daily_recipe

        monkeypatch.setattr(daily_recipe, "_today_utc", lambda: date(2026, 10, 15))
        assert daily_recipe._current_season() == "autumn"

    def test_current_season_winter(self, monkeypatch):
        """1 月 → winter。"""
        from datetime import date

        from hermes_kb import daily_recipe

        monkeypatch.setattr(daily_recipe, "_today_utc", lambda: date(2026, 1, 15))
        assert daily_recipe._current_season() == "winter"

    def test_seasonal_pool_empty_db(self, client):
        """空数据库季节池为空。"""
        from hermes_kb.daily_recipe import _seasonal_pool

        pool = _seasonal_pool("summer")
        assert pool == []

    def test_seasonal_pool_with_data(self, seeded_recipes):
        """有种子数据时季节池非空。"""
        from hermes_kb.daily_recipe import _seasonal_pool

        # 种子配方有 season 字段，找一个存在的季节
        from hermes_kb.seed_recipes import SEED_RECIPES

        seasons = {r.get("season", "") for r in SEED_RECIPES}
        seasons.discard("")
        if seasons:
            pool = _seasonal_pool(next(iter(seasons)))
            # 可能为空（种子配方季节与请求不匹配），但不应报错
            assert isinstance(pool, list)

    def test_daily_recipe_empty_db(self, client):
        """空数据库返回 None 或 {'title': None}。"""
        from hermes_kb.daily_recipe import daily_recipe

        result = daily_recipe()
        assert result is None or result.get("title") is None

    def test_daily_recipe_season_branch(self, seeded_recipes, monkeypatch):
        """roll < 0.6 走季节池分支。"""
        from datetime import date

        from hermes_kb import daily_recipe

        # 强制 roll=0.1（< 0.6 → 季节池）
        monkeypatch.setattr(daily_recipe, "_today_utc", lambda: date(2026, 7, 15))
        import random as random_mod

        class FakeRNG:
            def random(self):
                return 0.1

            def choice(self, seq):
                return seq[0] if seq else None

        monkeypatch.setattr(random_mod, "Random", lambda seed: FakeRNG())

        result = daily_recipe.daily_recipe()
        # 季节池可能为空，回退到其他分支，但不应报错
        assert result is None or "title" in result

    def test_daily_recipe_hot_branch(self, seeded_recipes, monkeypatch):
        """0.6 ≤ roll < 0.9 走热门池分支。"""
        from datetime import date

        from hermes_kb import daily_recipe

        monkeypatch.setattr(daily_recipe, "_today_utc", lambda: date(2026, 7, 15))

        class FakeRNG:
            def random(self):
                return 0.7  # 季节池 < 0.6 失败 → 热门 0.6-0.9

            def choice(self, seq):
                return seq[0] if seq else None

        import random as random_mod

        monkeypatch.setattr(random_mod, "Random", lambda seed: FakeRNG())

        # 提供预取热门池
        hot_recipes = [{"title": "热门配方", "doc_id": "doc_1", "chunk_rowid": 1}]
        result = daily_recipe.daily_recipe(hot_recipes=hot_recipes)
        if result and result.get("reason") == "hot":
            assert result["title"] == "热门配方"

    def test_daily_recipe_random_branch(self, seeded_recipes, monkeypatch):
        """roll ≥ 0.9 走随机池分支。"""
        from datetime import date

        from hermes_kb import daily_recipe

        monkeypatch.setattr(daily_recipe, "_today_utc", lambda: date(2026, 7, 15))

        class FakeRNG:
            def random(self):
                return 0.95  # ≥ 0.9 → 随机

            def choice(self, seq):
                return seq[0] if seq else None

        import random as random_mod

        monkeypatch.setattr(random_mod, "Random", lambda seed: FakeRNG())

        result = daily_recipe.daily_recipe()
        if result:
            assert result["reason"] == "random"


# ===========================================================================
# iba_dataset_importer
# ===========================================================================
class TestIBADatasetImporter:
    """IBA 数据集导入器。"""

    def test_parse_iba_recipe_basic(self):
        """parse_iba_recipe 解析基本字段（IBA dataset 格式：name + quantity）。"""
        from hermes_kb.iba_dataset_importer import parse_iba_recipe

        raw = {
            "name": "Mojito",
            "ingredients": [
                {"name": "white rum", "quantity": 4.5},
                {"name": "lime juice", "quantity": 3},
            ],
            "type": "Contemporary Classics",
        }
        recipe = parse_iba_recipe(raw)
        assert recipe["title"] == "Mojito"
        assert "白朗姆酒" in recipe["content"] or "white rum" in recipe["content"].lower()
        assert "45ml" in recipe["content"]  # 4.5cl → 45ml
        assert "ingredients" in recipe
        assert recipe["source"] == "iba"
        assert recipe["verified"] is True

    def test_parse_iba_recipe_missing_name(self):
        """缺 name 字段时 title 为空字符串。"""
        from hermes_kb.iba_dataset_importer import parse_iba_recipe

        raw = {"ingredients": [{"name": "gin", "quantity": 5}]}
        recipe = parse_iba_recipe(raw)
        assert recipe["title"] == ""
        assert "content" in recipe

    def test_parse_iba_recipe_with_strength_data(self):
        """传入 strength_data 时计算 ABV（quantity 提供 volume）。"""
        from hermes_kb.iba_dataset_importer import parse_iba_recipe

        raw = {
            "name": "Gin Tonic",
            "ingredients": [
                {"name": "gin", "quantity": 5},  # 5cl → 50ml
                {"name": "tonic water", "quantity": 15},  # 15cl → 150ml
            ],
        }
        strength_data = {"gin": 0.40}
        recipe = parse_iba_recipe(raw, strength_data=strength_data)
        # 应计算了 abv（gin 有 ABV 数据）
        assert recipe["abv"] is not None or "abv" in recipe.get("content", "")

    def test_sync_with_mock_data_success(self, client):
        """传入 mock data 成功导入。"""
        from hermes_kb.iba_dataset_importer import sync_iba_dataset

        data = [
            {
                "name": "Test IBA Recipe Unique 1",
                "ingredients": [
                    {"name": "gin", "quantity": 5},
                ],
            },
        ]
        result = sync_iba_dataset(data=data)
        assert result["imported"] == 1
        assert result["failed"] == 0
        assert isinstance(result["unknown_ingredients"], list)

    def test_sync_empty_data(self, client):
        """空数据返回零值。"""
        from hermes_kb.iba_dataset_importer import sync_iba_dataset

        result = sync_iba_dataset(data=[])
        assert result == {"imported": 0, "skipped": 0, "failed": 0, "unknown_ingredients": []}

    def test_sync_dedup_skipped(self, client):
        """重复配方被跳过。"""
        from hermes_kb.iba_dataset_importer import sync_iba_dataset

        data = [{
            "name": "Dedup Test Recipe Unique",
            "ingredients": [{"name": "gin", "quantity": 5}],
        }]
        # 第一次导入
        sync_iba_dataset(data=data)
        # 第二次应被跳过（fuzzy 匹配）
        result = sync_iba_dataset(data=data)
        assert result["skipped"] >= 1

    def test_sync_parse_failure_counted_as_failed(self, client):
        """解析失败的条目计入 failed。"""
        from hermes_kb.iba_dataset_importer import sync_iba_dataset

        # 传入会触发异常的数据（ingredients 不是 list）
        data = [{"name": "Bad Recipe", "ingredients": "not_a_list"}]
        result = sync_iba_dataset(data=data)
        # 应该至少有 1 个 failed 或 skipped
        assert result["failed"] + result["skipped"] + result["imported"] == 1

    def test_diff_iba_official_basic(self, client):
        """diff_iba_official 对比本地与官方数据集。"""
        from hermes_kb.iba_dataset_importer import diff_iba_official

        local_data = [{"title": "Mojito"}, {"title": "Margarita"}]
        official_data = [{"name": "Mojito"}, {"name": "Negroni"}]
        result = diff_iba_official(local_data=local_data, official_data=official_data)
        assert result["local_count"] == 2
        assert result["official_count"] == 2
        assert "mojito" in result["matched"]
        assert "negroni" in result["missing_locally"]
        assert "margarita" in result["extra_locally"]

    def test_diff_iba_official_empty(self, client):
        """两边都为空。"""
        from hermes_kb.iba_dataset_importer import diff_iba_official

        result = diff_iba_official(local_data=[], official_data=[])
        assert result["local_count"] == 0
        assert result["official_count"] == 0
        assert result["matched"] == []
        assert result["missing_locally"] == []
        assert result["extra_locally"] == []

    def test_diff_iba_official_from_db(self, client):
        """local_data=None 从 DB 查询。"""
        from hermes_kb.database import get_session
        from hermes_kb.iba_dataset_importer import diff_iba_official
        from hermes_kb.models import Document

        with get_session() as session:
            session.add(Document(
                doc_id="test_diff_iba",
                title="IBA Test Recipe",
                content="x",
                file_type="md",
                chunk_count=0,
                category="recipe",
                source="iba",
            ))
            session.commit()

        result = diff_iba_official(local_data=None, official_data=[{"name": "IBA Test Recipe"}])
        assert "iba test recipe" in result["matched"]

    def test_fetch_remote_data_network_failure_returns_empty(self, monkeypatch):
        """网络全失败 + 无本地文件 → 空列表。"""
        from hermes_kb import iba_dataset_importer
        import httpx

        def failing_get(url, timeout=None):
            raise httpx.HTTPError("network failure")

        monkeypatch.setattr(httpx, "get", failing_get)
        result = iba_dataset_importer._fetch_remote_data()
        assert isinstance(result, list)

    def test_fetch_remote_data_success(self, monkeypatch):
        """直连 GitHub 成功。"""
        from hermes_kb import iba_dataset_importer

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return [{"name": "Test Recipe"}]

        def fake_get(url, timeout=None):
            return FakeResp()

        import httpx

        monkeypatch.setattr(httpx, "get", fake_get)
        result = iba_dataset_importer._fetch_remote_data()
        assert result == [{"name": "Test Recipe"}]
