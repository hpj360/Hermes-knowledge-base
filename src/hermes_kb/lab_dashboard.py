"""运营看板指标聚合（M4.1）。

一次性返回实验室运营所需的全部指标。
"""
from __future__ import annotations

from typing import Any

from sqlmodel import func, select

from hermes_kb.database import get_session
from hermes_kb.daily_recipe import daily_recipe
from hermes_kb.ingredients import all_canonical
from hermes_kb.missing_stats import get_top_missing
from hermes_kb.models import Document, IngredientSubstitute, RecipeStats
from hermes_kb.recipe_stats import get_hot_recipes
from hermes_kb.seed_recipes import SEED_RECIPES
from hermes_kb.substitutes import SUBSTITUTES_PRESET


def get_lab_dashboard() -> dict[str, Any]:
    """聚合实验室运营指标。"""
    # Top 配方（取 10 条，供 daily_recipe 复用，避免重复查询）
    hot_recipes = get_hot_recipes(limit=10, days=30)
    top_recipe = hot_recipes[0]["title"] if hot_recipes else None

    # 高频缺失
    top_missing_list = get_top_missing(limit=1)
    top_missing = top_missing_list[0] if top_missing_list else None

    # 替代表覆盖率
    all_ings = set(all_canonical())
    covered = set(SUBSTITUTES_PRESET.keys())

    # 单 session 聚合所有 DB 指标（合并原 2 个 session，减少连接开销）
    with get_session() as session:
        recipe_count = session.exec(
            select(func.count(Document.doc_id)).where(
                Document.category == "recipe"
            )
        ).one()

        # 本周匹配数（近 7 天新增的匹配数，A4-1 修正后语义）
        weekly_match = session.exec(
            select(func.sum(RecipeStats.weekly_match_count))
        ).one() or 0

        # 累计匹配数（保留原 sum 语义）
        total_match = session.exec(
            select(func.sum(RecipeStats.match_count)).where(
                RecipeStats.match_count > 0
            )
        ).one() or 0

        # 用户自定义替代数
        user_sub_count = session.exec(
            select(func.count(IngredientSubstitute.id)).where(
                IngredientSubstitute.source == "user"
            )
        ).one()

        rows = session.exec(
            select(IngredientSubstitute.canonical).distinct()
        ).all()
        covered.update(rows)

    substitute_coverage = len(covered & all_ings) / len(all_ings) if all_ings else 0

    # 今日推荐（复用已取的热门池，避免 daily_recipe 内部重复查询）
    daily = daily_recipe(hot_recipes=hot_recipes)

    # 季节标签覆盖
    seasonal_recipes = sum(1 for r in SEED_RECIPES if r.get("season"))
    season_coverage = seasonal_recipes / len(SEED_RECIPES) if SEED_RECIPES else 0

    return {
        "recipe_count": recipe_count,
        "weekly_match_count": weekly_match,
        "total_match_count": total_match,
        "top_recipe": top_recipe,
        "top_missing": top_missing,
        "substitute_coverage": round(substitute_coverage, 2),
        "user_substitute_count": user_sub_count,
        "daily_recipe": daily["title"] if daily else None,
        "season_coverage": round(season_coverage, 2),
    }
