"""配方筛选/审核/隐藏（B5 数据源治理）。"""
from __future__ import annotations

from typing import Any

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document


def filter_recipes(
    source: str | None = None,
    verified: bool | None = None,
    hidden: bool | None = None,
    status: str | None = None,
    limit: int = 100,
    *,
    technique: str | None = None,
    glassware: str | None = None,
    iba_category: str | None = None,
    flavor_profile: str | None = None,
    difficulty: str | None = None,
    abv_bucket: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]]:
    """筛选配方列表。

    新增 keyword-only 参数（向后兼容）：
    - technique/glassware/iba_category: 精确匹配，空串或 None 时不过滤
    - flavor_profile: 模糊匹配（Document.flavor_profile 包含查询字符串），空串或 None 时不过滤
    - difficulty/abv_bucket/season: 精确匹配，空串或 None 时不过滤
    """
    with get_session() as session:
        stmt = select(Document).where(Document.category == "recipe")
        if source is not None:
            stmt = stmt.where(Document.source == source)
        if verified is not None:
            stmt = stmt.where(Document.verified == verified)
        if hidden is not None:
            stmt = stmt.where(Document.hidden == hidden)
        if status is not None:
            stmt = stmt.where(Document.status == status)
        if technique:
            stmt = stmt.where(Document.technique == technique)
        if glassware:
            stmt = stmt.where(Document.glassware == glassware)
        if iba_category:
            stmt = stmt.where(Document.iba_category == iba_category)
        if flavor_profile:
            stmt = stmt.where(Document.flavor_profile.like(f"%{flavor_profile}%"))
        if difficulty:
            stmt = stmt.where(Document.difficulty == difficulty)
        if abv_bucket:
            stmt = stmt.where(Document.abv_bucket == abv_bucket)
        if season:
            stmt = stmt.where(Document.season == season)
        stmt = stmt.limit(limit)
        docs = session.exec(stmt).all()
        return [
            {
                "doc_id": d.doc_id,
                "title": d.title,
                "source": d.source,
                "source_id": d.source_id,
                "verified": d.verified,
                "season": d.season,
                "hidden": d.hidden,
                "status": d.status,
                "image_url": d.image_url,
                "technique": d.technique,
                "glassware": d.glassware,
                "iba_category": d.iba_category,
                "flavor_profile": d.flavor_profile,
                "difficulty": d.difficulty,
                "abv_bucket": d.abv_bucket,
            }
            for d in docs
        ]


def verify_recipe(doc_id: str) -> bool:
    """审核通过配方（verified=True, status=published）。"""
    with get_session() as session:
        doc = session.get(Document, doc_id)
        if not doc:
            return False
        doc.verified = True
        doc.status = "published"
        session.add(doc)
        session.commit()
        return True


def hide_recipe(doc_id: str, hidden: bool = True) -> bool:
    """隐藏/取消隐藏配方。"""
    with get_session() as session:
        doc = session.get(Document, doc_id)
        if not doc:
            return False
        doc.hidden = hidden
        session.add(doc)
        session.commit()
        return True


def find_recipes_by_ingredients(
    user_ingredients: list[str],
    min_match: int = 1,
    limit: int = 20,
) -> dict[str, list[dict[str, Any]]]:
    """按材料交集检索配方。

    流程：
    1. 对用户输入的每个材料，调用 ingredients.canonicalize 归一化
    2. 调用 substitutes.get_substitutes 扩展用户材料集合（含替代关系）
    3. 加载所有 category=recipe 的配方
    4. 对每个配方，计算用户材料集合与配方 ingredients 的交集数
    5. 分组：
       - full_match: 用户材料集合 ⊇ 配方材料集合（含替代命中）
       - partial_match: 命中数 ≥ min_match 但有缺失
    6. 排序：
       - full_match 按配方材料数降序
       - partial_match 按命中数降序，再按缺失数升序
    7. 各组取前 limit 条

    Args:
        user_ingredients: 用户材料名列表（可为中文或英文别名）
        min_match: partial_match 的最小命中数阈值，默认 1
        limit: 每组返回的最大数量，默认 20

    Returns:
        {"full_match": [...], "partial_match": [...]}
    """
    from hermes_kb.ingredients import canonicalize, get_category
    from hermes_kb.substitutes import get_substitutes

    if not user_ingredients:
        return {"full_match": [], "partial_match": []}

    # 1. 归一化 + 扩展用户材料集合
    user_canonical: set[str] = set()
    for ing in user_ingredients:
        canon = canonicalize(ing)
        if canon:
            user_canonical.add(canon)
            # 加入替代材料
            for sub in get_substitutes(canon):
                user_canonical.add(canonicalize(sub) or sub)

    # 2. 加载所有配方
    with get_session() as session:
        stmt = select(Document).where(
            Document.category == "recipe",
            Document.hidden == False,  # SQLAlchemy 需要 == 而非 is
        )
        docs = session.exec(stmt).all()

    # 3. 计算交集
    full_match: list[dict[str, Any]] = []
    partial_match: list[dict[str, Any]] = []

    for doc in docs:
        # 解析配方材料（从 content frontmatter 或 ingredients 字段）
        # 简化实现：用 recipe_match 的解析逻辑或直接从 frontmatter 解析
        from hermes_kb.recipe_match import _FRONTMATTER_PATTERN

        recipe_ings: set[str] = set()
        content = doc.content or ""
        m = _FRONTMATTER_PATTERN.search(content)
        if m:
            for ing_name in m.group(1).split("|"):
                ing_name = ing_name.strip()
                if ing_name:
                    canon = canonicalize(ing_name)
                    if canon:
                        recipe_ings.add(canon)

        if not recipe_ings:
            continue  # 无材料信息跳过

        # 装饰类材料（garnish）视为可选，不参与缺少数判定
        # 简化：将 garnish 类材料从 recipe_ings 中移除后再判断缺失
        required_ings = {ing for ing in recipe_ings if get_category(ing) != "garnish"}

        hit_count = len(required_ings & user_canonical)
        missing_count = len(required_ings) - hit_count

        item = {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "technique": doc.technique,
            "glassware": doc.glassware,
            "difficulty": doc.difficulty,
            "abv_bucket": doc.abv_bucket,
            "season": doc.season,
            "hit_count": hit_count,
            "missing_count": missing_count,
            "missing_ingredients": sorted(required_ings - user_canonical),
        }

        if missing_count == 0:
            full_match.append(item)
        elif hit_count >= min_match:
            partial_match.append(item)

    # 4. 排序
    full_match.sort(key=lambda x: x["hit_count"], reverse=True)
    partial_match.sort(key=lambda x: (-x["hit_count"], x["missing_count"]))

    return {
        "full_match": full_match[:limit],
        "partial_match": partial_match[:limit],
    }
