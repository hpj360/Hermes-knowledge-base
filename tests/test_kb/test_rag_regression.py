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

import json
from pathlib import Path

from hermes_kb.recipe_match import match_recipes
from hermes_kb.seed import seed_recipes
from tests.eval import load_eval_set

# Task 5：RAG 评估基线文件路径（tests/eval/baseline.json）
BASELINE_PATH = Path(__file__).resolve().parent.parent / "eval" / "baseline.json"


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


# Task 7：新增百科评估查询（q101-q140）覆盖的 10 篇百科标题
_NEW_ENCYCLOPEDIA_TITLES = [
    "伏特加 Vodka 百科",
    "白兰地 Brandy 百科",
    "利口酒 Liqueur 百科",
    "苦精 Bitters 百科",
    "味美思 Vermouth 百科",
    "糖浆与辅料百科",
    "调酒器具百科",
    "调酒术语词典",
    "日本清酒 Sake 百科",
    "韩国烧酒 Soju 百科",
]

# 每篇新百科在 q101-q140 中对应的 category（每篇 4 条查询）
_NEW_ENCYCLOPEDIA_CATEGORY_MAP = {
    "伏特加 Vodka 百科": "伏特加",
    "白兰地 Brandy 百科": "白兰地",
    "利口酒 Liqueur 百科": "利口酒",
    "苦精 Bitters 百科": "苦精",
    "味美思 Vermouth 百科": "味美思",
    "糖浆与辅料百科": "糖浆辅料",
    "调酒器具百科": "器具",
    "调酒术语词典": "术语",
    "日本清酒 Sake 百科": "清酒",
    "韩国烧酒 Soju 百科": "烧酒",
}


def test_eval_set_new_encyclopedia_sampling():
    """抽样校验新百科评估查询的数据结构（仅校验 JSONL，不依赖真实 RAG 检索）。"""
    by_id = {item.id: item for item in load_eval_set()}

    # 1. 伏特加查询 q101
    q101 = by_id["q101"]
    assert "伏特加 Vodka 百科" in q101.expected_doc_titles
    assert "谷物" in q101.expected_keywords
    assert "马铃薯" in q101.expected_keywords

    # 2. 日本清酒查询 q133
    q133 = by_id["q133"]
    assert "日本清酒 Sake 百科" in q133.expected_doc_titles
    assert "米" in q133.expected_keywords

    # 3. 调酒术语查询
    #    eval_set.jsonl 中：
    #      - q129 = build 兑和技法（keywords=["兑和","直接倒入"]）
    #      - q131 = muddle 捣压技法（keywords=["捣压","薄荷叶"]）
    #    分别校验两者的 doc_title 与对应关键词。
    q129 = by_id["q129"]
    assert "调酒术语词典" in q129.expected_doc_titles
    assert "兑和" in q129.expected_keywords
    q131 = by_id["q131"]
    assert "调酒术语词典" in q131.expected_doc_titles
    assert "捣压" in q131.expected_keywords


def test_eval_set_covers_new_encyclopedia():
    """eval_set.jsonl 规模 >= 140，且 q101-q140 覆盖全部 10 篇新百科，
    category 字段非空且与对应百科一致（如 q101-q104 category == "伏特加"）。"""
    items = load_eval_set()
    # 评估集规模：原 100 条 + 新增 40 条
    assert len(items) >= 140, f"期望 eval_set >= 140 条，实际 {len(items)}"

    by_id = {item.id: item for item in items}
    new_ids = [f"q{i:03d}" for i in range(101, 141)]

    # q101-q140 必须全部存在
    missing_ids = [qid for qid in new_ids if qid not in by_id]
    assert not missing_ids, f"缺少 q101-q140 中的条目: {missing_ids}"

    # expected_doc_title 覆盖全部 10 篇新百科
    new_titles = {by_id[qid].expected_doc_titles[0] for qid in new_ids}
    missing_titles = [t for t in _NEW_ENCYCLOPEDIA_TITLES if t not in new_titles]
    assert not missing_titles, f"q101-q140 未覆盖的新百科标题: {missing_titles}"

    # category 非空且与对应百科一致
    for qid in new_ids:
        item = by_id[qid]
        assert item.category, f"{qid} 的 category 为空"
        expected_title = item.expected_doc_titles[0]
        expected_category = _NEW_ENCYCLOPEDIA_CATEGORY_MAP[expected_title]
        assert item.category == expected_category, (
            f"{qid}: category 期望 {expected_category!r}, 实际 {item.category!r}"
        )


def test_baseline_json_exists():
    """Task 5：断言 tests/eval/baseline.json 文件存在（RAG 评估基线产物）。"""
    assert BASELINE_PATH.exists(), (
        f"baseline.json 不存在: {BASELINE_PATH}。请运行 run_eval_baseline() 生成基线。"
    )
    assert BASELINE_PATH.is_file(), f"baseline.json 不是文件: {BASELINE_PATH}"


def test_baseline_recall_rate_above_threshold():
    """Task 5：读取 baseline.json，断言 recall_rate >= 0。

    基线仅作对比基准，不设高阈值；但确保不为负数（合法范围 [0, 1]）。
    同时校验关键字段齐全：total / recall_hit / keyword_hit / recall_rate /
    keyword_rate / harvested_at。
    """
    assert BASELINE_PATH.exists(), (
        f"baseline.json 不存在: {BASELINE_PATH}。请先运行 run_eval_baseline()。"
    )
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    # 校验字段齐全
    required_keys = {
        "total",
        "recall_hit",
        "keyword_hit",
        "recall_rate",
        "keyword_rate",
        "harvested_at",
    }
    missing = required_keys - set(data)
    assert not missing, f"baseline.json 缺少字段: {sorted(missing)}"

    # recall_rate 非负（基线仅作对比基准，不设高阈值）
    recall_rate = data["recall_rate"]
    assert isinstance(recall_rate, (int, float)), (
        f"recall_rate 应为数值，实际 {type(recall_rate).__name__}: {recall_rate!r}"
    )
    assert recall_rate >= 0, (
        f"recall_rate 不应为负数，实际 {recall_rate}"
    )
