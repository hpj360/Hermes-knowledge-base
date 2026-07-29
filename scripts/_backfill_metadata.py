"""批量回填 544 条配方的 difficulty/season/abv_bucket/abv + 补全 technique。

回填策略：
- technique: 用 infer_technique(content) 补全空值
- abv: 用 estimate_recipe_stats(ingredients) 计算，写入 meta JSON
- abv_bucket: 用 classify_abv_bucket(abv) 分类
- difficulty: 基于 ingredient 数 + technique 推断
- season: 基于 ingredients/tags 推断
"""
import json
import re
import sys
from collections import Counter

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, "src")

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.ingredient_strength import estimate_recipe_stats
from hermes_kb.ingredients import canonicalize, get_tags
from hermes_kb.models import Document
from hermes_kb.recipe_metadata import infer_technique
from hermes_kb.recipe_stats import classify_abv_bucket

_FRONTMATTER_RE = re.compile(r"<!--\s*ingredients:\s*([^>]+?)\s*-->")


def parse_ingredients(content: str) -> list[str]:
    """从 content frontmatter 解析材料列表。"""
    if not content:
        return []
    match = _FRONTMATTER_RE.search(content[:500])
    if not match:
        return []
    return [x.strip() for x in match.group(1).split("|") if x.strip()]


# 季节关键词映射（材料 tag → 季节）
_SEASON_RULES = {
    "summer": ["mint", "tropical", "citrus", "lime", "soda", "rum", "tequila",
               "薄荷", "青柠", "苏打", "朗姆", "龙舌兰", "热带", "西柚", "百香果"],
    "winter": ["coffee", "cream", "egg", "whiskey", "hot", "spice",
               "咖啡", "奶油", "鸡蛋", "威士忌", "热", "肉桂", "丁香"],
    "spring": ["floral", "herbal", "light", "gin", "elderflower", "lavender",
               "花香", "草药", "金酒", "接骨木花", "薰衣草"],
    "autumn": ["apple", "caramel", "vermouth", "bitter", "whisky", "bourbon",
               "苹果", "焦糖", "味美思", "苦精", "波本"],
}


def infer_season(ingredients: list[str], title: str = "") -> str:
    """基于材料和标题推断季节。"""
    text = title.lower()
    # 标题直接匹配
    if any(k in text for k in ["hot", "toddy", "coffee", "irish coffee"]):
        return "winter"
    if any(k in text for k in ["mojito", "daiquiri", "colada", "summer"]):
        return "summer"
    if any(k in text for k in ["zombie", "scorpion", "punch"]):
        return "summer"

    # 材料匹配计分
    scores = {s: 0 for s in _SEASON_RULES}
    for ing in ingredients:
        canonical = canonicalize(ing)
        tags = get_tags(canonical)
        all_text = f"{ing} {canonical} {' '.join(tags)}".lower()
        for season, keywords in _SEASON_RULES.items():
            for kw in keywords:
                if kw.lower() in all_text:
                    scores[season] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "autumn"  # 默认秋季


def infer_difficulty(ingredients: list[str], technique: str, title: str = "") -> str:
    """基于材料数 + 技法 + 标题推断难度。"""
    n = len(ingredients)
    text = title.lower()

    # 标题直接匹配高难度
    if any(k in text for k in ["zombie", "scorpion", "punch", "b-52", "rainbow",
                                "pousse", "tom and jerry"]):
        return "hard"

    if technique in ("layer", "blend"):
        return "hard"
    if technique in ("muddle",):
        return "medium"
    if n > 6:
        return "hard"
    if n >= 4:
        return "medium"
    return "easy"


def main():
    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.category == "recipe")
        ).all()

        print(f"配方总数: {len(docs)}")
        stats = {
            "technique_filled": 0,
            "abv_filled": 0,
            "abv_bucket_filled": 0,
            "difficulty_filled": 0,
            "season_filled": 0,
            "skipped_no_ingredients": 0,
        }
        season_dist = Counter()
        difficulty_dist = Counter()
        abv_bucket_dist = Counter()

        for doc in docs:
            ingredients = parse_ingredients(doc.content or "")
            if not ingredients:
                stats["skipped_no_ingredients"] += 1
                # 仍填充默认值
                if not doc.difficulty:
                    doc.difficulty = "medium"
                    stats["difficulty_filled"] += 1
                if not doc.season:
                    doc.season = "autumn"
                    stats["season_filled"] += 1
                if not doc.abv_bucket:
                    doc.abv_bucket = "medium"
                    stats["abv_bucket_filled"] += 1
                difficulty_dist[doc.difficulty] += 1
                season_dist[doc.season] += 1
                abv_bucket_dist[doc.abv_bucket] += 1
                session.add(doc)
                continue

            # 1. 补全 technique
            if not doc.technique:
                tech = infer_technique(doc.content or "", ingredients)
                if tech:
                    doc.technique = tech
                    stats["technique_filled"] += 1

            # 2. 计算 ABV + abv_bucket
            meta = json.loads(doc.meta) if doc.meta and doc.meta != "{}" else {}
            if not meta.get("abv"):
                try:
                    est = estimate_recipe_stats(ingredients)
                    abv = est.get("estimated_abv", 0.0)
                    meta["abv"] = round(abv, 4)
                    meta["calories"] = round(est.get("estimated_calories", 0.0), 1)
                    meta["total_volume_ml"] = round(est.get("total_volume_ml", 0.0), 1)
                    doc.meta = json.dumps(meta, ensure_ascii=False)
                    stats["abv_filled"] += 1
                except Exception:  # noqa: BLE001
                    abv = 0.0

            abv = meta.get("abv", 0.0)
            if not doc.abv_bucket:
                bucket = classify_abv_bucket(abv)
                if bucket:
                    doc.abv_bucket = bucket
                    stats["abv_bucket_filled"] += 1

            # 3. 填充 difficulty
            if not doc.difficulty:
                doc.difficulty = infer_difficulty(ingredients, doc.technique, doc.title)
                stats["difficulty_filled"] += 1

            # 4. 填充 season
            if not doc.season:
                doc.season = infer_season(ingredients, doc.title)
                stats["season_filled"] += 1

            difficulty_dist[doc.difficulty] += 1
            season_dist[doc.season] += 1
            abv_bucket_dist[doc.abv_bucket] += 1
            session.add(doc)

        session.commit()

    print("\n=== 回填统计 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("\n=== 分布 ===")
    print(f"  difficulty: {dict(difficulty_dist)}")
    print(f"  season: {dict(season_dist)}")
    print(f"  abv_bucket: {dict(abv_bucket_dist)}")


if __name__ == "__main__":
    main()
