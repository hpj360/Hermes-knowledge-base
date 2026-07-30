"""批量回填配方的 difficulty/season/abv_bucket/technique/glassware 到 Document.meta JSON。

根因修复：
- 原脚本将 5 字段写入 Document 列属性（doc.difficulty 等），但验证与下游
  读取 Document.meta JSON，导致 meta JSON 中这 5 字段覆盖率始终为 0%。
- 原脚本未推断 glassware，载杯覆盖率无法提升。
- 原脚本仅在 abv 缺失时才回写 doc.meta，已存在 abv 的配方永远不会被写入新字段。
- 原脚本 bare except 吞掉 estimate_recipe_stats 异常，无任何日志。

修复策略：
- 将 5 字段写入 meta JSON（同时保持列同步），每条配方处理完毕后统一回写 doc.meta。
- 新增 glassware 推断（infer_glassware + 扩展英文关键词 + 技法兜底）。
- 显式 session.commit() 持久化。
- 详细日志输出每个字段的回填数量与最终覆盖率。
"""
import json
import logging
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
from hermes_kb.recipe_metadata import infer_glassware, infer_technique
from hermes_kb.recipe_stats import classify_abv_bucket

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("backfill_metadata")

_FRONTMATTER_RE = re.compile(r"<!--\s*ingredients:\s*([^>]+?)\s*-->")

# 技法 → 默认载杯（当 content 无显式载杯关键词时的兜底）
_TECHNIQUE_GLASSWARE_FALLBACK = {
    "stir": "马天尼杯",
    "shake": "高球杯",
    "build": "高球杯",
    "layer": "古典杯",
    "muddle": "古典杯",
    "blend": "飓风杯",
}

# 扩展载杯关键词（补充 infer_glassware 未覆盖的英文别名，大小写不敏感）
_GLASSWARE_EXTRA_RULES: list[tuple[str, str]] = [
    ("cocktail glass", "马天尼杯"),
    ("coupe glass", "Coupe 杯"),
    ("martini", "马天尼杯"),
    ("highball glass", "高球杯"),
    ("collins glass", "柯林斯杯"),
    ("rocks", "古典杯"),
    ("old fashioned glass", "古典杯"),
    ("shot glass", "古典杯"),
    ("wine glass", "高球杯"),
    ("margarita glass", "玛格丽特杯"),
    ("hurricane glass", "飓风杯"),
    ("champagne", "香槟杯"),
    ("snifter", "白兰地杯"),
    ("coupe", "Coupe 杯"),
    ("highball", "高球杯"),
    ("collins", "柯林斯杯"),
]


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


def infer_glassware_ex(content: str, title: str, technique: str) -> str:
    """推断载杯：infer_glassware + 扩展英文关键词 + 技法兜底。"""
    glass = infer_glassware(content, title)
    if glass:
        return glass
    # 扩展关键词匹配（大小写不敏感）
    if content:
        cl = content.lower()
        for kw, label in _GLASSWARE_EXTRA_RULES:
            if kw in cl:
                return label
    # 技法兜底；无技法时默认高球杯
    return _TECHNIQUE_GLASSWARE_FALLBACK.get(technique, "高球杯")


def _load_meta(doc: Document) -> dict:
    """安全解析 doc.meta JSON，失败返回空 dict。"""
    if not doc.meta or doc.meta == "{}":
        return {}
    try:
        result = json.loads(doc.meta)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def main() -> None:
    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.category == "recipe")
        ).all()

        total = len(docs)
        log.info("配方总数: %d", total)

        stats = {
            "technique_filled": 0,
            "glassware_filled": 0,
            "abv_filled": 0,
            "abv_bucket_filled": 0,
            "difficulty_filled": 0,
            "season_filled": 0,
            "skipped_no_ingredients": 0,
        }
        season_dist = Counter()
        difficulty_dist = Counter()
        abv_bucket_dist = Counter()
        glassware_dist = Counter()
        technique_dist = Counter()

        for doc in docs:
            content = doc.content or ""
            ingredients = parse_ingredients(content)
            if not ingredients:
                stats["skipped_no_ingredients"] += 1

            meta = _load_meta(doc)

            # 1. technique：meta → 列 → 推断 → 默认 build
            tech = meta.get("technique") or doc.technique or ""
            if not tech:
                tech = infer_technique(content, ingredients) or "build"
                stats["technique_filled"] += 1
            if not doc.technique:
                doc.technique = tech
            meta["technique"] = tech

            # 2. glassware：meta → 列 → infer_glassware_ex（含兜底）
            glass = meta.get("glassware") or doc.glassware or ""
            if not glass:
                glass = infer_glassware_ex(content, doc.title, tech)
                stats["glassware_filled"] += 1
            if not doc.glassware:
                doc.glassware = glass
            meta["glassware"] = glass

            # 3. abv / calories / total_volume_ml
            if not meta.get("abv"):
                if ingredients:
                    try:
                        est = estimate_recipe_stats(ingredients)
                        meta["abv"] = round(est.get("estimated_abv", 0.0), 4)
                        meta["calories"] = round(
                            est.get("estimated_calories", 0.0), 1
                        )
                        meta["total_volume_ml"] = round(
                            est.get("total_volume_ml", 0.0), 1
                        )
                        stats["abv_filled"] += 1
                    except Exception as exc:  # noqa: BLE001
                        log.warning(
                            "abv 估算失败 doc=%s title=%s: %s",
                            doc.doc_id, doc.title, exc,
                        )
                        meta["abv"] = 0.0
                else:
                    meta["abv"] = 0.0

            # 4. abv_bucket：meta → 列 → classify_abv_bucket → 默认 medium
            bucket = meta.get("abv_bucket") or doc.abv_bucket or ""
            if not bucket:
                bucket = classify_abv_bucket(meta.get("abv", 0.0)) or "medium"
                stats["abv_bucket_filled"] += 1
            if not doc.abv_bucket:
                doc.abv_bucket = bucket
            meta["abv_bucket"] = bucket

            # 5. difficulty：meta → 列 → infer_difficulty → 默认 medium
            diff = meta.get("difficulty") or doc.difficulty or ""
            if not diff:
                diff = infer_difficulty(ingredients, tech, doc.title) or "medium"
                stats["difficulty_filled"] += 1
            if not doc.difficulty:
                doc.difficulty = diff
            meta["difficulty"] = diff

            # 6. season：meta → 列 → infer_season → 默认 autumn
            season = meta.get("season") or doc.season or ""
            if not season:
                season = infer_season(ingredients, doc.title) or "autumn"
                stats["season_filled"] += 1
            if not doc.season:
                doc.season = season
            meta["season"] = season

            # 统一回写 meta JSON（修复原脚本仅在 abv 缺失时回写的 bug）
            doc.meta = json.dumps(meta, ensure_ascii=False)
            session.add(doc)

            difficulty_dist[diff] += 1
            season_dist[season] += 1
            abv_bucket_dist[bucket] += 1
            glassware_dist[glass] += 1
            technique_dist[tech] += 1

        session.commit()
        log.info("已 commit %d 条配方元数据", total)

    # ------------------------------------------------------------------
    # 报告
    # ------------------------------------------------------------------
    print("\n=== 回填统计 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n=== 分布 ===")
    print(f"  difficulty: {dict(difficulty_dist)}")
    print(f"  season: {dict(season_dist)}")
    print(f"  abv_bucket: {dict(abv_bucket_dist)}")
    print(f"  glassware: {dict(glassware_dist)}")
    print(f"  technique: {dict(technique_dist)}")

    # 覆盖率（meta JSON 视角，与验证查询一致）
    print("\n=== meta JSON 覆盖率 ===")
    fields = ["difficulty", "season", "abv_bucket", "technique", "glassware"]
    with get_session() as s:
        recipes = s.exec(
            select(Document).where(Document.category == "recipe")
        ).all()
        counts = {f: 0 for f in fields}
        for r in recipes:
            m = _load_meta(r)
            for f in fields:
                if m.get(f):
                    counts[f] += 1
        n = len(recipes)
        for f in fields:
            pct = (counts[f] / n * 100) if n else 0.0
            print(f"  {f}: {counts[f]}/{n} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
