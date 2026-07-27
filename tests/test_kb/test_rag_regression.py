# -*- coding: utf-8 -*-
"""Task 10.3：RAG 准确率回归测试（结构性回归）。

不依赖真实 LLM / Embedding 网络，改为对 RecipeMatch 模块做结构性回归：

- test_seed_recipes_retrievable:
    调用 seed_recipes() 导入 57 款 IBA 配方后，对每款配方用其自身 ingredients
    集合查询 RecipeMatch.match_recipes，断言至少 50 款能被正确匹配
    （自身 doc_id 出现在 full_match 中）。

- test_recipe_match_unchanged:
    抽样 5 款配方（覆盖不同基酒 / 技法 / 分类），用其 ingredients 列表
    查询 RecipeMatch，断言匹配到的 doc_id 对应正确配方（标题一致）。

- test_recipe_match_ingredients_full_match:
    对所有 57 款配方，用其自身 ingredients 集合查询，断言每款至少能进入
    full_match 或 partial_match（结构不变性）。
"""
from __future__ import annotations

from hermes_kb.recipe_match import match_recipes
from hermes_kb.seed import seed_recipes


# 抽样 5 款覆盖不同基酒 / 技法 / 分类的经典 IBA 配方（标题需与 seed_recipes 一致）
_SAMPLED_TITLES = [
    "马天尼 Martini",       # gin / stir / unforgettables
    "玛格丽特 Margarita",   # tequila / shake / contemporary_classics
    "古典鸡尾酒 Old Fashioned",  # whiskey / build / unforgettables
    "尼格罗尼 Negroni",     # gin / build / unforgettables
    "新加坡司令 Singapore Sling",  # gin / shake / contemporary_classics
]


def _import_all_recipes():
    """通过 seed_recipes() 导入全量 57 款 IBA 配方，返回 items 列表。"""
    result = seed_recipes()
    assert result["seeded"] >= 57, (  # 57 IBA + 新增非 IBA 配方
        f"seed_recipes() 应导入 57 款，实际 seeded={result['seeded']}, "
        f"failed={result['failed']}, skipped={result['skipped']}"
    )
    return result["items"]


def test_seed_recipes_retrievable(tmp_db):
    """57 款种子配方中至少 50 款能被 RecipeMatch 基于自身 ingredients 正确匹配。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    items = _import_all_recipes()
    # 构建 title -> doc_id 映射（仅成功导入的）
    title_to_doc_id = {
        item["title"]: item["doc_id"]
        for item in items
        if item.get("status") == "imported" and "doc_id" in item
    }
    assert len(title_to_doc_id) >= 57  # 57 IBA + 新增非 IBA 配方

    matched_count = 0
    unmatched_titles: list[str] = []
    for recipe in SEED_RECIPES:
        title = recipe["title"]
        ings = set(recipe["ingredients"])
        result = match_recipes(ings, limit=20)
        full_match_titles = {m["title"] for m in result["full_match"]}
        if title in full_match_titles:
            matched_count += 1
        else:
            unmatched_titles.append(title)

    assert matched_count >= 50, (
        f"仅 {matched_count}/57 款配方能被 RecipeMatch 正确匹配，"
        f"未匹配: {unmatched_titles}"
    )


def test_recipe_match_unchanged(tmp_db):
    """抽样 5 款配方，用其 ingredients 查询 RecipeMatch，断言匹配到正确 doc_id。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    items = _import_all_recipes()
    title_to_doc_id = {
        item["title"]: item["doc_id"]
        for item in items
        if item.get("status") == "imported" and "doc_id" in item
    }
    recipe_by_title = {r["title"]: r for r in SEED_RECIPES}

    # 抽样标题必须全部存在于种子中
    missing = [t for t in _SAMPLED_TITLES if t not in recipe_by_title]
    assert not missing, f"抽样标题不在 SEED_RECIPES 中: {missing}"

    for title in _SAMPLED_TITLES:
        recipe = recipe_by_title[title]
        expected_doc_id = title_to_doc_id[title]
        ings = set(recipe["ingredients"])
        result = match_recipes(ings, limit=20)
        # 自身 ingredients 必然缺 0 种，应在 full_match 中
        full_match_doc_ids = {m["doc_id"] for m in result["full_match"]}
        full_match_titles = {m["title"] for m in result["full_match"]}
        assert expected_doc_id in full_match_doc_ids, (
            f"{title}: 期望 doc_id={expected_doc_id} 不在 full_match 中。"
            f" 实际 titles={sorted(full_match_titles)}"
        )
        # 标题应一致（doc_id <-> title 对应关系不变）
        for m in result["full_match"]:
            if m["doc_id"] == expected_doc_id:
                assert m["title"] == title, (
                    f"doc_id={expected_doc_id} 标题不一致: "
                    f"期望 {title!r}, 实际 {m['title']!r}"
                )


def test_recipe_match_ingredients_full_match(tmp_db):
    """所有 57 款配方用自身 ingredients 查询，至少出现在 full_match 或 partial_match 中。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    _import_all_recipes()

    missing_recipes: list[str] = []
    for recipe in SEED_RECIPES:
        title = recipe["title"]
        ings = set(recipe["ingredients"])
        result = match_recipes(ings, limit=20)
        full_titles = {m["title"] for m in result["full_match"]}
        partial_titles = {m["title"] for m in result["partial_match"]}
        if title not in (full_titles | partial_titles):
            missing_recipes.append(title)

    assert not missing_recipes, (
        f"{len(missing_recipes)} 款配方未出现在 full/partial_match: {missing_recipes}"
    )


def test_seed_recipes_count_and_no_failures(tmp_db):
    """seed_recipes() 导入结果应为 57 成功 / 0 失败 / 0 跳过。"""
    result = seed_recipes()
    assert result["seeded"] >= 57, f"期望 seeded=57, 实际 {result['seeded']}"  # 57 IBA + 新增非 IBA 配方
    assert result["failed"] == 0, (
        f"期望 failed=0, 实际 {result['failed']}: "
        f"{[i for i in result['items'] if i.get('status') == 'failed']}"
    )
    assert result["skipped"] == 0, f"期望 skipped=0, 实际 {result['skipped']}"


def test_recipe_match_idempotent_after_reimport(tmp_db):
    """seed_recipes() 二次调用应幂等跳过，且 RecipeMatch 仍能匹配全部配方。"""
    from hermes_kb.seed_recipes import SEED_RECIPES

    first = seed_recipes()
    assert first["seeded"] >= 57  # 57 IBA + 新增非 IBA 配方
    second = seed_recipes()
    assert second["seeded"] == 0
    assert second["skipped"] >= 57  # 57 IBA + 新增非 IBA 配方

    # 重新匹配 5 款抽样，确保 RecipeMatch 仍能正确匹配
    recipe_by_title = {r["title"]: r for r in SEED_RECIPES}
    for title in _SAMPLED_TITLES:
        recipe = recipe_by_title[title]
        ings = set(recipe["ingredients"])
        result = match_recipes(ings, limit=20)
        full_titles = {m["title"] for m in result["full_match"]}
        assert title in full_titles, (
            f"幂等导入后 {title} 未在 full_match 中: {sorted(full_titles)}"
        )
