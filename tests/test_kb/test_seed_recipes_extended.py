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

import pytest


def test_seed_recipes_count_meets_iba_minimum():
    """种子配方数应不少于 IBA 全量（57 款：23 Unforgettables + 24 Contemporary + 10 New Era）。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    assert len(SEED_RECIPES) >= 50, f"种子配方仅 {len(SEED_RECIPES)} 款，未达 IBA 全量目标"


def test_seed_recipes_count_is_57_iba_full():
    """当前 IBA 全量应为 57 款（23+24+10）。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    assert len(SEED_RECIPES) == 57, f"期望 57 款 IBA 全量，实际 {len(SEED_RECIPES)}"


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
    """IBA 三大分类覆盖且数量符合官方分布。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    by_cat: dict[str, int] = {}
    for r in SEED_RECIPES:
        cat = r["iba_category"]
        by_cat[cat] = by_cat.get(cat, 0) + 1

    assert set(by_cat.keys()) == {
        "unforgettables",
        "contemporary_classics",
        "new_era_drinks",
    }, f"出现非官方分类: {set(by_cat.keys())}"
    # IBA 官方数量（2026 版本）
    assert by_cat["unforgettables"] == 23
    assert by_cat["contemporary_classics"] == 24
    assert by_cat["new_era_drinks"] == 10


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

    valid_bases = {"gin", "whiskey", "rum", "tequila", "vodka", "brandy", "other"}
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
