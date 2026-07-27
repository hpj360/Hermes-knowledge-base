# -*- coding: utf-8 -*-
"""阶段 A.5：seed_recipes 扩展测试。

覆盖：
- 字段完整性（title/base_spirit/difficulty/season/iba_category/technique/glassware/ingredients/history/content）
- 分类覆盖（IBA 三大分类：unforgettables/contemporary_classics/new_era_drinks）
- 技法覆盖（build/stir/shake/blend/layer/muddle）
- 标题唯一性
- 材料归一化（所有 ingredients 均在 INGREDIENT_REGISTRY 注册）
- frontmatter 一致性（content 头部 `<!-- ingredients: a|b|c -->` 与 ingredients 字段一致）
- 历史/字段类型与长度合理性
"""
from __future__ import annotations



def test_seed_recipes_count_meets_iba_minimum():
    """种子配方数应不少于 IBA 全量（57 款：23 Unforgettables + 24 Contemporary + 10 New Era）。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    assert len(SEED_RECIPES) >= 50, f"种子配方仅 {len(SEED_RECIPES)} 款，未达 IBA 全量目标"


def test_seed_recipes_count_is_57_iba_full():
    """IBA 全量基线应不少于 57 款（23+24+10），向后兼容新增非 IBA 配方。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    assert len(SEED_RECIPES) >= 57, f"期望 >= 57 款（IBA 全量基线），实际 {len(SEED_RECIPES)}"


def test_required_fields_present():
    """每款配方必须包含所有必填字段且非空。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    required_fields = [
        "title",
        "base_spirit",
        "difficulty",
        "season",
        "iba_category",
        "technique",
        "glassware",
        "ingredients",
        "history",
        "content",
    ]
    missing: list[tuple[str, str]] = []
    for r in SEED_RECIPES:
        for f in required_fields:
            if f not in r or not r.get(f):
                missing.append((r.get("title", "?"), f))
    assert not missing, f"缺失字段: {missing}"


def test_titles_unique():
    """所有配方标题唯一。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    titles = [r["title"] for r in SEED_RECIPES]
    duplicates = {t for t in titles if titles.count(t) > 1}
    assert not duplicates, f"标题重复: {duplicates}"


def test_iba_category_distribution():
    """IBA 三大分类覆盖且数量符合官方分布（向后兼容新增非 IBA 配方）。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    by_cat: dict[str, int] = {}
    for r in SEED_RECIPES:
        cat = r["iba_category"]
        by_cat[cat] = by_cat.get(cat, 0) + 1

    # IBA 三大分类必须存在且数量符合官方分布
    assert by_cat.get("unforgettables") == 23
    assert by_cat.get("contemporary_classics") == 24
    assert by_cat.get("new_era_drinks") == 10
    # 允许新增非 IBA 配方（iba_category="" 或 "non_iba"）


def test_technique_distribution():
    """技法分布合理（覆盖主要技法）。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    valid_techniques = {"build", "stir", "shake", "blend", "layer", "muddle"}
    by_tech: dict[str, int] = {}
    for r in SEED_RECIPES:
        tech = r["technique"]
        assert tech in valid_techniques, f"未知技法 {tech}（配方 {r['title']}）"
        by_tech[tech] = by_tech.get(tech, 0) + 1

    # shake/build/stir 应为主流
    assert by_tech.get("shake", 0) > 0
    assert by_tech.get("build", 0) > 0
    assert by_tech.get("stir", 0) > 0


def test_base_spirit_distribution():
    """基酒分布合理。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    valid_bases = {"gin", "whiskey", "rum", "tequila", "vodka", "brandy", "wine", "liqueur", "mezcal", "none", "other"}
    by_base: dict[str, int] = {}
    for r in SEED_RECIPES:
        base = r["base_spirit"]
        assert base in valid_bases, f"未知基酒 {base}（配方 {r['title']}）"
        by_base[base] = by_base.get(base, 0) + 1

    # 金酒应是主流基酒（IBA 配方中金酒占比较高）
    assert by_base.get("gin", 0) >= 10, "金酒配方数应不少于 10"


def test_difficulty_values_valid():
    """难度字段取值合法。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    valid_difficulty = {"easy", "medium", "hard"}
    for r in SEED_RECIPES:
        assert r["difficulty"] in valid_difficulty, (
            f"非法难度 {r['difficulty']}（配方 {r['title']}）"
        )


def test_season_values_valid():
    """季节字段取值合法。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    valid_season = {"spring", "summer", "autumn", "winter"}
    for r in SEED_RECIPES:
        assert r["season"] in valid_season, (
            f"非法季节 {r['season']}（配方 {r['title']}）"
        )


def test_ingredients_non_empty():
    """每款配方的材料列表非空。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    for r in SEED_RECIPES:
        assert isinstance(r["ingredients"], list)
        assert len(r["ingredients"]) >= 2, (
            f"配方 {r['title']} 材料数 < 2：{r['ingredients']}"
        )


def test_ingredients_canonicalized():
    """所有材料经 canonicalize 后必须存在于 INGREDIENT_REGISTRY。"""
    from hermes_kb.ingredients import (
        INGREDIENT_REGISTRY,
        canonicalize,
    )
    from hermes_kb.seed_recipes import SEED_RECIPES

    unknown: dict[str, list[str]] = {}
    for r in SEED_RECIPES:
        for ing in r["ingredients"]:
            normalized = canonicalize(ing)
            in_registry = any(
                info["canonical"] == normalized
                for info in INGREDIENT_REGISTRY.values()
            )
            if not in_registry:
                unknown.setdefault(ing, []).append(r["title"])

    assert not unknown, f"{len(unknown)} 个材料未注册: {list(unknown.keys())}"


def test_frontmatter_consistency():
    """content 头部 `<!-- ingredients: a|b|c -->` 与 ingredients 字段一致。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    issues: list[tuple[str, str]] = []
    for r in SEED_RECIPES:
        content = r["content"]
        prefix = "<!-- ingredients:"
        if not content.startswith(prefix):
            issues.append((r["title"], "缺 frontmatter"))
            continue
        end = content.find("-->")
        if end == -1:
            issues.append((r["title"], "frontmatter 未闭合"))
            continue
        # 提取 frontmatter 内的材料串
        fm_str = content[len(prefix) : end].strip()
        fm_ings = [x.strip() for x in fm_str.split("|") if x.strip()]
        if fm_ings != r["ingredients"]:
            issues.append(
                (
                    r["title"],
                    f"frontmatter={fm_ings} vs ingredients={r['ingredients']}",
                )
            )

    assert not issues, f"frontmatter 不一致: {issues}"


def test_history_non_trivial():
    """历史字段应具有实质内容（长度 > 20 字符）。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    short_history: list[tuple[str, int]] = []
    for r in SEED_RECIPES:
        h = r["history"]
        if len(h) < 20:
            short_history.append((r["title"], len(h)))
    assert not short_history, f"history 过短: {short_history}"


def test_content_has_recipe_structure():
    """content 应包含配方与步骤章节。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    missing_section: list[str] = []
    for r in SEED_RECIPES:
        content = r["content"]
        if "## 配方" not in content:
            missing_section.append(f"{r['title']}(缺## 配方)")
        if "## 步骤" not in content:
            missing_section.append(f"{r['title']}(缺## 步骤)")
    assert not missing_section, f"content 缺章节: {missing_section}"


def test_glassware_diversity():
    """杯型字段应覆盖至少 4 种不同杯型。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    glasses: set[str] = {r["glassware"] for r in SEED_RECIPES}
    assert len(glasses) >= 4, f"杯型多样性不足: {glasses}"


def test_known_iba_classics_present():
    """关键 IBA 经典配方必须存在。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    titles = {r["title"] for r in SEED_RECIPES}
    must_have = [
        "马天尼 Martini",
        "尼格罗尼 Negroni",
        "曼哈顿 Manhattan",
        "古典鸡尾酒 Old Fashioned",
        "戴基里 Daiquiri",
        "玛格丽特 Margarita",
    ]
    missing = [t for t in must_have if t not in titles]
    assert not missing, f"缺少 IBA 经典配方: {missing}"


def test_seed_recipes_importable_without_db():
    """seed_recipes 模块应可独立导入（不依赖 DB）。"""
    # 已通过其他测试隐式验证，此处显式断言数据结构
    from hermes_kb.seed_recipes import SEED_RECIPES

    assert isinstance(SEED_RECIPES, list)
    assert all(isinstance(r, dict) for r in SEED_RECIPES)


# ===========================================================================
# Task 3.2 新增：元数据字段完整性补强（语义断言）
# ===========================================================================
def test_all_recipes_have_technique():
    """每款 SEED_RECIPES 都应有非空的 technique 字段。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    missing = [r["title"] for r in SEED_RECIPES if not r.get("technique")]
    assert not missing, f"缺 technique 的配方: {missing}"


def test_all_recipes_have_glassware():
    """每款 SEED_RECIPES 都应有非空的 glassware 字段。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    missing = [r["title"] for r in SEED_RECIPES if not r.get("glassware")]
    assert not missing, f"缺 glassware 的配方: {missing}"


def test_all_recipes_have_iba_category():
    """每款 SEED_RECIPES 都应有非空的 iba_category 字段。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    missing = [r["title"] for r in SEED_RECIPES if not r.get("iba_category")]
    assert not missing, f"缺 iba_category 的配方: {missing}"


def test_technique_values_valid():
    """technique 值必须在合法集合内。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    valid_techniques = {"build", "stir", "shake", "blend", "layer", "muddle"}
    invalid = [
        (r["title"], r["technique"])
        for r in SEED_RECIPES
        if r["technique"] not in valid_techniques
    ]
    assert not invalid, f"非法 technique 值: {invalid}"


def test_iba_category_values_valid():
    """iba_category 值必须在 IBA 三大分类集合内。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    valid_categories = {
        "unforgettables",
        "contemporary_classics",
        "new_era_drinks",
        "non_iba",  # 新增非 IBA 配方
        "",  # 兼容空值
    }
    invalid = [
        (r["title"], r["iba_category"])
        for r in SEED_RECIPES
        if r["iba_category"] not in valid_categories
    ]
    assert not invalid, f"非法 iba_category 值: {invalid}"


def test_glassware_distribution():
    """至少有 3 种不同 glassware 值（如马天尼杯/古典杯/高球杯）。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    glasses = {r["glassware"] for r in SEED_RECIPES}
    assert len(glasses) >= 3, (
        f"杯型多样性不足，仅 {len(glasses)} 种: {glasses}"
    )
    # 抽样验证常见杯型至少命中一个（语义断言）
    common_glasses = {"马天尼杯", "古典杯", "高球杯"}
    assert glasses & common_glasses, (
        f"未覆盖常见杯型（马天尼杯/古典杯/高球杯）任一: {glasses}"
    )


# ===========================================================================
# Task 4.2：新增元数据字段（difficulty/abv_bucket/season）覆盖验证
# ===========================================================================
class TestNewMetadataFields:
    """Task 4: 验证种子配方的 difficulty/abv_bucket/season 字段。"""

    def test_all_seed_recipes_have_difficulty(self):
        """所有种子配方都应有 difficulty 字段（easy/medium/hard）。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        valid_difficulties = {"easy", "medium", "hard"}
        for recipe in SEED_RECIPES:
            assert recipe.get("difficulty", "") in valid_difficulties, \
                f"Recipe '{recipe['title']}' has invalid difficulty: {recipe.get('difficulty')}"

    def test_all_seed_recipes_have_season(self):
        """所有种子配方都应有 season 字段。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        valid_seasons = {"spring", "summer", "autumn", "winter", ""}
        for recipe in SEED_RECIPES:
            assert recipe.get("season", "") in valid_seasons, \
                f"Recipe '{recipe['title']}' has invalid season: {recipe.get('season')}"

    def test_seed_recipes_count_at_least_77(self):
        """种子配方规模 >= 77（57 IBA + 20 非 IBA）。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        assert len(SEED_RECIPES) >= 77, f"Expected >= 77 recipes, got {len(SEED_RECIPES)}"

    def test_layer_technique_recipes_exist(self):
        """layer 技法配方数 >= 2（覆盖原 layer=0 盲区）。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        layer_recipes = [r for r in SEED_RECIPES if r.get("technique") == "layer"]
        assert len(layer_recipes) >= 2, f"Expected >= 2 layer recipes, got {len(layer_recipes)}"

    def test_mocktail_recipes_exist(self):
        """Mocktail 配方（abv_override=0.0）>= 3 款。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        mocktails = [r for r in SEED_RECIPES if r.get("abv_override") == 0.0]
        assert len(mocktails) >= 3, f"Expected >= 3 mocktail recipes, got {len(mocktails)}"

    def test_new_categories_covered(self):
        """新增品类覆盖：Tiki/Hot/Flip/Punch/Mocktail/Layered。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        titles = [r["title"] for r in SEED_RECIPES]
        # Tiki
        assert any("Zombie" in t or "僵尸" in t for t in titles), "Missing Tiki recipe (Zombie)"
        assert any("Painkiller" in t or "止痛药" in t for t in titles), "Missing Tiki recipe (Painkiller)"
        # Hot Drinks
        assert any("Hot Toddy" in t or "热托迪" in t for t in titles), "Missing Hot Drink (Hot Toddy)"
        # Flip
        assert any("Flip" in t for t in titles), "Missing Flip recipe"
        # Punch
        assert any("Punch" in t for t in titles), "Missing Punch recipe"
        # Mocktail
        assert any("Virgin" in t or "Shirley" in t for t in titles), "Missing Mocktail recipe"
        # Layered
        assert any("B-52" in t or "Pousse" in t for t in titles), "Missing Layered recipe"


# ===========================================================================
# Task 6：新增配方的具体内容校验（规模/技法/Mocktail 校验）
# ===========================================================================
class TestNewRecipesVerification:
    """Task 6: 新增配方的具体内容校验。"""

    def test_tiki_recipes_count(self):
        """Tiki 配方数 >= 4。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        tiki_keywords = ["Zombie", "僵尸", "Painkiller", "止痛药", "Missionary", "Scorpion"]
        tiki_count = sum(1 for r in SEED_RECIPES if any(k in r["title"] for k in tiki_keywords))
        assert tiki_count >= 4, f"Expected >= 4 Tiki recipes, got {tiki_count}"

    def test_hot_drinks_recipes_count(self):
        """Hot Drinks 配方数 >= 2。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        hot_keywords = ["Hot Toddy", "热托迪", "Tom and Jerry"]
        hot_count = sum(1 for r in SEED_RECIPES if any(k in r["title"] for k in hot_keywords))
        assert hot_count >= 2, f"Expected >= 2 Hot Drink recipes, got {hot_count}"

    def test_flip_recipes_count(self):
        """Flip 配方数 >= 2。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        flip_count = sum(1 for r in SEED_RECIPES if "Flip" in r["title"] or "Alexander" in r["title"])
        assert flip_count >= 2, f"Expected >= 2 Flip recipes, got {flip_count}"

    def test_punch_recipes_count(self):
        """Punch 配方数 >= 2。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        punch_count = sum(1 for r in SEED_RECIPES if "Punch" in r["title"])
        assert punch_count >= 2, f"Expected >= 2 Punch recipes, got {punch_count}"

    def test_layered_recipes_count(self):
        """Layered 分层配方数 >= 2。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        layer_count = sum(1 for r in SEED_RECIPES if r.get("technique") == "layer")
        assert layer_count >= 2, f"Expected >= 2 layer recipes, got {layer_count}"

    def test_modern_classics_count(self):
        """现代经典配方数 >= 3。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        modern_keywords = ["Paper Plane", "Gold Rush", "Naked and Famous"]
        modern_count = sum(1 for r in SEED_RECIPES if any(k in r["title"] for k in modern_keywords))
        assert modern_count >= 3, f"Expected >= 3 modern classics, got {modern_count}"

    def test_new_recipes_have_non_iba_category(self):
        """新增配方的 iba_category 应为空或 'non_iba'。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        # 跳过前 57 款 IBA 配方
        for recipe in SEED_RECIPES[57:]:
            iba_cat = recipe.get("iba_category", "")
            assert iba_cat in ("", "non_iba"), \
                f"New recipe '{recipe['title']}' has invalid iba_category: {iba_cat}"

    def test_mocktail_ingredients_no_alcohol(self):
        """Mocktail 配方的材料不含酒精（abv=0）。"""
        from hermes_kb.seed_recipes import SEED_RECIPES
        from hermes_kb.ingredients import get_abv
        mocktails = [r for r in SEED_RECIPES if r.get("abv_override") == 0.0]
        assert len(mocktails) >= 3
        for recipe in mocktails:
            for ing in recipe["ingredients"]:
                abv = get_abv(ing)
                assert abv == 0.0, \
                    f"Mocktail '{recipe['title']}' ingredient '{ing}' has abv={abv}"
