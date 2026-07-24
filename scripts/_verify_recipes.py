"""验证 seed_recipes 与 ingredients 注册表的一致性。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hermes_kb.seed_recipes import SEED_RECIPES
from hermes_kb.ingredients import INGREDIENT_REGISTRY, canonicalize


def main() -> None:
    print(f"=== seed_recipes 统计 ===")
    print(f"总配方数: {len(SEED_RECIPES)}")

    # 分类统计
    by_category: dict[str, int] = {}
    by_technique: dict[str, int] = {}
    by_base: dict[str, int] = {}
    for r in SEED_RECIPES:
        by_category[r.get("iba_category", "?")] = by_category.get(r.get("iba_category", "?"), 0) + 1
        by_technique[r.get("technique", "?")] = by_technique.get(r.get("technique", "?"), 0) + 1
        by_base[r.get("base_spirit", "?")] = by_base.get(r.get("base_spirit", "?"), 0) + 1

    print("\n按 IBA 分类:")
    for k, v in by_category.items():
        print(f"  {k}: {v}")
    print("\n按技法:")
    for k, v in by_technique.items():
        print(f"  {k}: {v}")
    print("\n按基酒:")
    for k, v in by_base.items():
        print(f"  {k}: {v}")

    # 字段完整性检查
    print("\n=== 字段完整性检查 ===")
    required_fields = ["title", "base_spirit", "difficulty", "season",
                       "iba_category", "technique", "glassware",
                       "ingredients", "history", "content"]
    missing_field_recipes = []
    for r in SEED_RECIPES:
        for f in required_fields:
            if f not in r or not r.get(f):
                missing_field_recipes.append((r.get("title", "?"), f))
    if missing_field_recipes:
        print(f"❌ {len(missing_field_recipes)} 条字段缺失:")
        for title, field in missing_field_recipes:
            print(f"  - {title} 缺 {field}")
    else:
        print(f"✅ 所有 {len(SEED_RECIPES)} 款配方字段完整")

    # 标题唯一性
    titles = [r["title"] for r in SEED_RECIPES]
    duplicates = [t for t in titles if titles.count(t) > 1]
    if duplicates:
        print(f"❌ 标题重复: {set(duplicates)}")
    else:
        print(f"✅ 标题唯一")

    # 材料归一化检查
    print("\n=== 材料归一化检查 ===")
    unknown_ingredients: dict[str, list[str]] = {}
    for r in SEED_RECIPES:
        for ing in r["ingredients"]:
            normalized = canonicalize(ing)
            # 检查 normalized 是否在注册表中
            in_registry = any(
                info["canonical"] == normalized
                for info in INGREDIENT_REGISTRY.values()
            )
            if not in_registry:
                unknown_ingredients.setdefault(ing, []).append(r["title"])

    if unknown_ingredients:
        print(f"⚠️  {len(unknown_ingredients)} 个材料未注册:")
        for ing, recipes in sorted(unknown_ingredients.items()):
            print(f"  - {ing} (用于 {len(recipes)} 款配方)")
    else:
        print(f"✅ 所有材料均已注册")

    # content frontmatter 检查
    print("\n=== frontmatter 检查 ===")
    frontmatter_issues = []
    for r in SEED_RECIPES:
        content = r["content"]
        if not content.startswith("<!-- ingredients:"):
            frontmatter_issues.append((r["title"], "缺 frontmatter"))
            continue
        # 提取 frontmatter
        end = content.find("-->")
        if end == -1:
            frontmatter_issues.append((r["title"], "frontmatter 未闭合"))
            continue
        fm = content[18:end].strip()
        fm_ings = [x.strip() for x in fm.split("|") if x.strip()]
        if fm_ings != r["ingredients"]:
            frontmatter_issues.append((r["title"],
                                       f"frontmatter 与 ingredients 不一致: {fm_ings} vs {r['ingredients']}"))

    if frontmatter_issues:
        print(f"❌ {len(frontmatter_issues)} 条 frontmatter 问题:")
        for title, issue in frontmatter_issues:
            print(f"  - {title}: {issue}")
    else:
        print(f"✅ 所有 frontmatter 正确")


if __name__ == "__main__":
    main()
