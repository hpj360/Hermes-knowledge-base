# -*- coding: utf-8 -*-
"""TheCocktailDB 同步器测试（B2）。"""
from __future__ import annotations


from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document


def test_normalize_ingredient():
    """B2: 英文材料名 → 中文标准名。"""
    from hermes_kb.thecocktaildb_sync import normalize_ingredient

    assert normalize_ingredient("Light rum") == "朗姆酒"
    assert normalize_ingredient("Gin") == "金酒"
    assert normalize_ingredient("Lime juice") == "青柠汁"
    assert normalize_ingredient("Campari") == "金巴利"
    assert normalize_ingredient("Unknown ingredient") is None


def test_normalize_ingredient_case_insensitive():
    """B2: 归一化应大小写不敏感。"""
    from hermes_kb.thecocktaildb_sync import normalize_ingredient

    assert normalize_ingredient("GIN") == "金酒"
    assert normalize_ingredient("light RUM") == "朗姆酒"


def test_parse_recipe_basic():
    """B2: 解析单条 API 响应为配方 dict。"""
    from hermes_kb.thecocktaildb_sync import parse_recipe

    api_data = {
        "idDrink": "11000",
        "strDrink": "Mojito",
        "strInstructions": "Muddle mint leaves with sugar and lime juice.",
        "strDrinkThumb": "https://www.thecocktaildb.com/images/media/drink/metwpp1504642957.jpg",
        "strIngredient1": "Light rum",
        "strMeasure1": "2-3 oz",
        "strIngredient2": "Lime",
        "strMeasure2": "Juice of 1",
        "strIngredient3": "Sugar",
        "strMeasure3": "2 tsp",
        "strIngredient4": "Mint",
        "strMeasure4": "2-4",
        "strIngredient5": "Soda water",
        "strMeasure5": "",
        "strIngredient6": None,
    }
    recipe = parse_recipe(api_data)
    assert recipe["source_id"] == "11000"
    assert recipe["title"] == "Mojito"
    assert recipe["source"] == "thecocktaildb"
    assert recipe["verified"] is False
    assert recipe["image_url"] == "https://www.thecocktaildb.com/images/media/drink/metwpp1504642957.jpg"
    assert "朗姆酒" in recipe["ingredients"]
    assert "青柠汁" in recipe["ingredients"]
    assert "糖浆" in recipe["ingredients"]


def test_parse_recipe_preserves_unknown_ingredients():
    """B2: 未归一化的材料应保留英文原名。"""
    from hermes_kb.thecocktaildb_sync import parse_recipe

    api_data = {
        "idDrink": "11001",
        "strDrink": "Special Drink",
        "strInstructions": "Mix.",
        "strDrinkThumb": "",
        "strIngredient1": "Gin",
        "strMeasure1": "1 oz",
        "strIngredient2": "Midori Melon Liqueur",
        "strMeasure2": "0.5 oz",
        "strIngredient3": None,
    }
    recipe = parse_recipe(api_data)
    assert "金酒" in recipe["ingredients"]
    # 未归一化的应保留在 unknown_ingredients
    assert "Midori Melon Liqueur" in recipe["unknown_ingredients"]
    # content 中也应保留英文原名
    assert "Midori Melon Liqueur" in recipe["content"]


def test_parse_recipe_no_image():
    """B2: 无图片时 image_url 为 None。"""
    from hermes_kb.thecocktaildb_sync import parse_recipe

    api_data = {
        "idDrink": "11002",
        "strDrink": "No Image Drink",
        "strInstructions": "Mix.",
        "strIngredient1": "Vodka",
        "strMeasure1": "1 oz",
        "strIngredient2": None,
    }
    recipe = parse_recipe(api_data)
    assert recipe["image_url"] is None


def test_sync_thecocktaildb_mock(monkeypatch):
    """B2: 同步流程 mock 测试。"""
    from hermes_kb.thecocktaildb_sync import sync_thecocktaildb

    mock_drinks = [
        {
            "idDrink": "11000", "strDrink": "Mojito",
            "strInstructions": "Muddle mint with sugar and lime.",
            "strDrinkThumb": "https://example.com/mojito.jpg",
            "strIngredient1": "Light rum", "strMeasure1": "2 oz",
            "strIngredient2": "Lime", "strMeasure2": "1",
            "strIngredient3": "Soda water", "strMeasure3": "Top",
            "strIngredient4": None,
        },
        {
            "idDrink": "11001", "strDrink": "Negroni",
            "strInstructions": "Stir all ingredients with ice.",
            "strDrinkThumb": "https://example.com/negroni.jpg",
            "strIngredient1": "Gin", "strMeasure1": "1 oz",
            "strIngredient2": "Campari", "strMeasure2": "1 oz",
            "strIngredient3": "Sweet Vermouth", "strMeasure3": "1 oz",
            "strIngredient4": None,
        },
    ]

    def mock_httpx_get(url, **kwargs):
        class MockResp:
            status_code = 200
            def json(self):
                return {"drinks": mock_drinks}
            def raise_for_status(self):
                pass
        return MockResp()

    import httpx
    monkeypatch.setattr(httpx, "get", mock_httpx_get)

    result = sync_thecocktaildb(limit=10, letters="a")
    assert result["imported"] == 2
    assert result["failed"] == 0

    # 验证导入
    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.source == "thecocktaildb")
        ).all()
        assert len(docs) == 2
        titles = {d.title for d in docs}
        assert "Mojito" in titles
        assert "Negroni" in titles
        # image_url 应保存
        mojito = next(d for d in docs if d.title == "Mojito")
        assert mojito.image_url == "https://example.com/mojito.jpg"
        # verified 应为 False
        assert all(not d.verified for d in docs)

    # 再次同步应去重
    result2 = sync_thecocktaildb(limit=10, letters="a")
    assert result2["imported"] == 0
    assert result2["skipped"] == 2


def test_sync_thecocktaildb_multiple_letters(monkeypatch):
    """B2: 应支持多字母遍历（全量拉取）。"""
    from hermes_kb.thecocktaildb_sync import sync_thecocktaildb

    fetch_log = []

    def mock_httpx_get(url, **kwargs):
        fetch_log.append(url)
        class MockResp:
            status_code = 200
            def json(self):
                # 不同字母返回不同配方
                if "f=a" in url:
                    return {"drinks": [{"idDrink": "1", "strDrink": "A Drink", "strIngredient1": "Gin", "strMeasure1": "1oz"}]}
                elif "f=b" in url:
                    return {"drinks": [{"idDrink": "2", "strDrink": "B Drink", "strIngredient1": "Vodka", "strMeasure1": "1oz"}]}
                return {"drinks": None}
            def raise_for_status(self):
                pass
        return MockResp()

    import httpx
    monkeypatch.setattr(httpx, "get", mock_httpx_get)

    result = sync_thecocktaildb(limit=100, letters="ab")
    assert result["imported"] == 2
    # 应拉取了两个字母
    assert any("f=a" in u for u in fetch_log)
    assert any("f=b" in u for u in fetch_log)


def test_sync_thecocktaildb_network_failure(monkeypatch):
    """B2: 网络失败应返回 failed=1 不崩溃。"""
    from hermes_kb.thecocktaildb_sync import sync_thecocktaildb

    def mock_httpx_get(url, **kwargs):
        raise ConnectionError("network down")

    import httpx
    monkeypatch.setattr(httpx, "get", mock_httpx_get)

    result = sync_thecocktaildb(limit=10, letters="a")
    assert result["imported"] == 0
    assert result["failed"] >= 1


# ===========================================================================
# Task 5.2 新增：验证 midori/galliano/drambuie 已能归一化
# ===========================================================================
def test_parse_recipe_known_ingredients_normalized():
    """Task 5.2: midori/galliano/drambuie 已注册到 INGREDIENT_REGISTRY，
    parse_recipe 应能归一化这些材料，unknown_ingredients 列表大幅减少（应为空）。
    """
    from hermes_kb.thecocktaildb_sync import parse_recipe

    api_data = {
        "idDrink": "99001",
        "strDrink": "Known Ingredients Test",
        "strInstructions": "Stir all ingredients with ice.",
        "strDrinkThumb": "",
        "strIngredient1": "Gin",
        "strMeasure1": "1 oz",
        "strIngredient2": "midori",
        "strMeasure2": "0.5 oz",
        "strIngredient3": "galliano",
        "strMeasure3": "0.25 oz",
        "strIngredient4": "drambuie",
        "strMeasure4": "0.5 oz",
        "strIngredient5": None,
    }
    recipe = parse_recipe(api_data)

    # midori/galliano/drambuie 已能归一化（在 _INGREDIENT_OVERRIDES 或
    # INGREDIENT_REGISTRY 中），故 unknown_ingredients 应为空列表
    assert recipe["unknown_ingredients"] == [], (
        f"未归一化材料列表非空: {recipe['unknown_ingredients']}"
    )

    # ingredients 应全部为中文标准名（不含原英文 midori/galliano/drambuie）
    ingredients_str = "|".join(recipe["ingredients"])
    assert "midori" not in ingredients_str.lower()
    assert "galliano" not in ingredients_str.lower()
    assert "drambuie" not in ingredients_str.lower()

    # 抽样验证归一化结果命中（金酒 + midori→哈密瓜利口酒 / galliano→加利亚诺）
    assert "金酒" in recipe["ingredients"]
    # midori 的 override 值为 "哈密瓜利口酒"
    assert "哈密瓜利口酒" in recipe["ingredients"]
    # galliano 的 override 值为 "加利亚诺"
    assert "加利亚诺" in recipe["ingredients"]
    # drambuie 的 override 值为 "威士忌利口酒"
    assert "威士忌利口酒" in recipe["ingredients"]


# ---------- Task 6: 元数据推断（technique/glassware/flavor_profile） ----------

MOCK_MOJITO = {
    "idDrink": "11000",
    "strDrink": "Mojito",
    "strInstructions": (
        "Build in a highball glass with ice. Add rum, lime juice, sugar, "
        "and mint leaves. Top with soda water."
    ),
    "strDrinkThumb": "https://example.com/mojito.jpg",
    "strIngredient1": "Light Rum",
    "strMeasure1": "2-3 oz",
    "strIngredient2": "Lime",
    "strMeasure2": "Juice of 1",
    "strIngredient3": "Sugar",
    "strMeasure3": "2 tsp",
    "strIngredient4": "Mint",
    "strMeasure4": "2-4",
    "strIngredient5": "Soda Water",
    "strMeasure5": "Top",
}


def test_parse_recipe_infers_technique():
    """Task 6: instructions 含 'shake well' 应推断 technique='shake'。"""
    from hermes_kb.thecocktaildb_sync import parse_recipe

    api_data = {
        "idDrink": "11010",
        "strDrink": "Shaken Drink",
        "strInstructions": "Shake well with ice and strain into a glass.",
        "strDrinkThumb": "https://example.com/shaken.jpg",
        "strIngredient1": "Gin",
        "strMeasure1": "2 oz",
        "strIngredient2": "Lime Juice",
        "strMeasure2": "0.5 oz",
        "strIngredient3": None,
    }
    recipe = parse_recipe(api_data)
    assert recipe["technique"] == "shake"


def test_parse_recipe_infers_glassware():
    """Task 6: instructions 含 'highball glass' 应推断 glassware='高球杯'。"""
    from hermes_kb.thecocktaildb_sync import parse_recipe

    api_data = {
        "idDrink": "11011",
        "strDrink": "Highball Drink",
        "strInstructions": "Pour into a highball glass filled with ice.",
        "strDrinkThumb": "",
        "strIngredient1": "Whiskey",
        "strMeasure1": "2 oz",
        "strIngredient2": "Soda Water",
        "strMeasure2": "4 oz",
        "strIngredient3": None,
    }
    recipe = parse_recipe(api_data)
    assert recipe["glassware"] == "高球杯"


def test_parse_recipe_infers_mojito():
    """Task 6: Mojito mock（build + highball）应推断 technique='build'、glassware='高球杯'。"""
    from hermes_kb.thecocktaildb_sync import parse_recipe

    recipe = parse_recipe(MOCK_MOJITO)
    assert recipe["technique"] == "build"
    assert recipe["glassware"] == "高球杯"
    # 同时验证基本字段未被破坏
    assert recipe["title"] == "Mojito"
    assert recipe["source_id"] == "11000"
    assert recipe["source"] == "thecocktaildb"


def test_parse_recipe_flavor_profile():
    """Task 6: 含 rum/mint/lime juice 的配方 flavor_profile 应非空。"""
    from hermes_kb.thecocktaildb_sync import parse_recipe

    recipe = parse_recipe(MOCK_MOJITO)
    # 朗姆酒/薄荷叶/青柠汁均带 tags，flavor_profile 应非空
    assert recipe["flavor_profile"]
    # 至少应包含朗姆酒带来的某个风味标签（如 sweet/tropical/molasses/caramel）
    assert any(
        tag in recipe["flavor_profile"]
        for tag in ("sweet", "tropical", "molasses", "caramel", "light", "clean")
    )


def test_parse_recipe_no_inference():
    """Task 6: 无关键词的 mock 应返回空 technique/glassware（不报错）。"""
    from hermes_kb.thecocktaildb_sync import parse_recipe

    api_data = {
        "idDrink": "11012",
        "strDrink": "Plain Drink",
        "strInstructions": "Mix everything together.",  # 不含任何技法/载杯关键词
        "strDrinkThumb": "",
        "strIngredient1": "Water",  # 不在 registry，无 tags
        "strMeasure1": "1 oz",
        "strIngredient2": None,
    }
    recipe = parse_recipe(api_data)
    assert recipe["technique"] == ""
    assert recipe["glassware"] == ""
    # 不应抛异常，且新字段存在
    assert "flavor_profile" in recipe
