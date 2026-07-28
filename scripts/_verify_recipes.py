"""验证 seed_recipes 与 ingredients 注册表的一致性。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hermes_kb.recipe_metadata import infer_flavor_profile
from hermes_kb.seed_recipes import SEED_RECIPES
from hermes_kb.ingredients import INGREDIENT_REGISTRY, canonicalize


# 校验失败累计（任一失败时以非零码退出）
_FAILURES: list[str] = []


def _record_failure(message: str) -> None:
    _FAILURES.append(message)


def verify_difficulty_season_abv_bucket() -> list[str]:
    """Task 12: 校验所有种子配方的 difficulty/abv_bucket/season 字段完整性。

    Returns:
        错误消息列表，空列表表示通过。
    """
    from hermes_kb.seed_recipes import SEED_RECIPES
    errors: list[str] = []
    valid_difficulties = {"easy", "medium", "hard"}
    valid_seasons = {"spring", "summer", "autumn", "winter"}

    for recipe in SEED_RECIPES:
        title = recipe.get("title", "<unknown>")

        # difficulty 校验
        difficulty = recipe.get("difficulty", "")
        if difficulty not in valid_difficulties:
            errors.append(
                f"Recipe '{title}' has invalid difficulty: '{difficulty}'. "
                f"Expected one of {sorted(valid_difficulties)}."
            )

        # season 校验（新增配方必须有，旧配方允许空）
        season = recipe.get("season", "")
        if season and season not in valid_seasons:
            errors.append(
                f"Recipe '{title}' has invalid season: '{season}'. "
                f"Expected one of {sorted(valid_seasons)} or empty."
            )

        # abv_override 校验（Mocktail 配方）
        abv_override = recipe.get("abv_override")
        if abv_override is not None:
            if not isinstance(abv_override, (int, float)) or abv_override < 0:
                errors.append(
                    f"Recipe '{title}' has invalid abv_override: {abv_override}. "
                    f"Expected non-negative number."
                )
            # Mocktail 配方 abv_override 应为 0
            if abv_override != 0:
                errors.append(
                    f"Recipe '{title}' has abv_override={abv_override}. "
                    f"Currently only 0.0 (Mocktail) is supported."
                )

    return errors


def verify_mocktail_ingredients_no_alcohol() -> list[str]:
    """Task 12: 校验 Mocktail 配方的材料不含酒精。

    Returns:
        错误消息列表，空列表表示通过。
    """
    from hermes_kb.ingredients import get_abv
    from hermes_kb.seed_recipes import SEED_RECIPES
    errors: list[str] = []

    for recipe in SEED_RECIPES:
        if recipe.get("abv_override") == 0.0:
            title = recipe.get("title", "<unknown>")
            for ing in recipe.get("ingredients", []):
                abv = get_abv(ing)
                if abv > 0:
                    errors.append(
                        f"Mocktail '{title}' contains alcoholic ingredient "
                        f"'{ing}' (abv={abv})."
                    )
    return errors


def verify_encyclopedia_docs() -> bool:
    """Task 5: 校验百科种子文档与新增材料注册条目完整性。

    校验内容：
    1. SEED_DOCS 规模 ≥ 15
    2. 每篇百科 title/content 非空、content 长度 ≥ 500、含 ≥ 3 个 "## " 二级标题
    3. 新增 INGREDIENT_REGISTRY 条目（亚洲酒与辅料）canonical 存在且
       aliases（list）与 category（str）非空

    失败时打印具体 title/canonical 与原因并返回 False；全部通过返回 True。
    """
    from hermes_kb.seed import SEED_DOCS

    errors: list[str] = []

    # 1. SEED_DOCS 规模
    if len(SEED_DOCS) < 15:
        errors.append(
            f"SEED_DOCS 规模不足: len={len(SEED_DOCS)}，期望 ≥ 15"
        )

    # 2. 每篇百科字段完整性
    for doc in SEED_DOCS:
        title = doc.get("title", "")
        if not isinstance(title, str) or not title:
            errors.append(f"百科 title 为空或非字符串: {title!r}")
            continue

        content = doc.get("content", "")
        if not isinstance(content, str) or not content:
            errors.append(f"百科 '{title}' content 为空或非字符串")
            continue

        if len(content) < 500:
            errors.append(
                f"百科 '{title}' content 长度 {len(content)} < 500"
            )

        h2_count = content.count("## ")
        if h2_count < 3:
            errors.append(
                f"百科 '{title}' 二级标题数 {h2_count} < 3"
            )

    # 3. 新增 INGREDIENT_REGISTRY 条目字段完整性（亚洲酒与辅料）
    required_canonicals = [
        "纯米酒", "本酿造", "纯米大吟酿", "大吟酿", "烧酎",
        "力洛酒", "多林味美思", "诺瓦利帕味美思", "奎纳味美思",
        "薰衣草糖浆", "方块冰", "碎冰", "老冰", "球冰", "冰沙",
    ]

    canonical_to_entry: dict[str, dict] = {}
    for entry in INGREDIENT_REGISTRY.values():
        canon = entry.get("canonical", "")
        if canon:
            canonical_to_entry[canon] = entry

    for canon in required_canonicals:
        if canon not in canonical_to_entry:
            errors.append(f"INGREDIENT_REGISTRY 缺少 canonical: {canon}")
            continue
        entry = canonical_to_entry[canon]
        aliases = entry.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            errors.append(f"材料 '{canon}' aliases 为空或非 list")
        category = entry.get("category")
        if not isinstance(category, str) or not category:
            errors.append(f"材料 '{canon}' category 为空或非 str")

    if errors:
        print(f"❌ {len(errors)} 条百科/材料校验问题:")
        for err in errors:
            print(f"  - {err}")
        return False

    print(
        f"✅ 百科 {len(SEED_DOCS)} 篇 + 新增材料 {len(required_canonicals)} 条校验通过"
    )
    return True


def main() -> None:
    print("=== seed_recipes 统计 ===")
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
            _record_failure(f"字段缺失: {title} 缺 {field}")
    else:
        print(f"✅ 所有 {len(SEED_RECIPES)} 款配方字段完整")

    # 标题唯一性
    titles = [r["title"] for r in SEED_RECIPES]
    duplicates = [t for t in titles if titles.count(t) > 1]
    if duplicates:
        print(f"❌ 标题重复: {set(duplicates)}")
        _record_failure(f"标题重复: {sorted(set(duplicates))}")
    else:
        print("✅ 标题唯一")

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
        print("✅ 所有材料均已注册")

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
            _record_failure(f"frontmatter 问题: {title}: {issue}")
    else:
        print("✅ 所有 frontmatter 正确")

    # ============================================================
    # Task 10.1 新增校验
    # ============================================================

    # --- 1. 元数据完整性校验 ---
    print("\n=== 元数据完整性校验（iba_category→technique/glassware 非空 + flavor_profile 非空）===")
    metadata_issues: list[tuple[str, str]] = []
    for r in SEED_RECIPES:
        title = r.get("title", "?")
        iba = r.get("iba_category", "")
        # iba_category 非空时，technique 与 glassware 必须非空
        if iba:
            if not r.get("technique"):
                metadata_issues.append((title, "iba_category 非空但 technique 为空"))
            if not r.get("glassware"):
                metadata_issues.append((title, "iba_category 非空但 glassware 为空"))
        # flavor_profile（基于 ingredients 聚合）必须非空
        flavor = infer_flavor_profile(r.get("ingredients", []))
        if not flavor:
            metadata_issues.append((title, "flavor_profile 为空（ingredients 无法聚合出 tags）"))

    if metadata_issues:
        print(f"❌ {len(metadata_issues)} 条元数据完整性问题:")
        for title, issue in metadata_issues:
            print(f"  - {title}: {issue}")
            _record_failure(f"元数据完整性: {title}: {issue}")
    else:
        print(f"✅ 所有 {len(SEED_RECIPES)} 款配方元数据完整（technique/glassware/flavor_profile 非空）")

    # --- 2. 材料注册表 canonical 唯一性校验 ---
    print("\n=== INGREDIENT_REGISTRY canonical 唯一性校验 ===")
    canonical_list: list[str] = [
        info.get("canonical", "") for info in INGREDIENT_REGISTRY.values()
    ]
    canonical_nonempty = [c for c in canonical_list if c]
    seen: dict[str, int] = {}
    for c in canonical_nonempty:
        seen[c] = seen.get(c, 0) + 1
    dup_canonical = sorted({c for c, n in seen.items() if n > 1})
    # 也检查空 canonical
    empty_canonical_count = len(canonical_list) - len(canonical_nonempty)

    if dup_canonical or empty_canonical_count > 0:
        if dup_canonical:
            print(f"❌ {len(dup_canonical)} 个 canonical 重复:")
            for c in dup_canonical:
                print(f"  - {c}（出现 {seen[c]} 次）")
                _record_failure(f"canonical 重复: {c}（{seen[c]} 次）")
        if empty_canonical_count > 0:
            print(f"❌ {empty_canonical_count} 条 registry 条目 canonical 为空")
            _record_failure(f"canonical 为空条目数: {empty_canonical_count}")
    else:
        print(f"✅ {len(canonical_nonempty)} 个 canonical 全部唯一（len(set)==len(list)）")

    # --- 3. technique 值合法性校验 ---
    print("\n=== technique 值合法性校验 ===")
    valid_techniques = {"build", "stir", "shake", "blend", "layer", "muddle", ""}
    invalid_techniques: list[tuple[str, str]] = [
        (r.get("title", "?"), r.get("technique", ""))
        for r in SEED_RECIPES
        if r.get("technique", "") not in valid_techniques
    ]
    if invalid_techniques:
        print(f"❌ {len(invalid_techniques)} 条非法 technique:")
        for title, tech in invalid_techniques:
            print(f"  - {title}: technique={tech!r}")
            _record_failure(f"非法 technique: {title}: {tech!r}")
    else:
        print(f"✅ 所有 {len(SEED_RECIPES)} 款配方 technique 值合法")

    # --- 4. iba_category 值合法性校验 ---
    print("\n=== iba_category 值合法性校验 ===")
    valid_categories = {"unforgettables", "contemporary_classics", "new_era_drinks", ""}
    invalid_categories: list[tuple[str, str]] = [
        (r.get("title", "?"), r.get("iba_category", ""))
        for r in SEED_RECIPES
        if r.get("iba_category", "") not in valid_categories
    ]
    if invalid_categories:
        print(f"❌ {len(invalid_categories)} 条非法 iba_category:")
        for title, cat in invalid_categories:
            print(f"  - {title}: iba_category={cat!r}")
            _record_failure(f"非法 iba_category: {title}: {cat!r}")
    else:
        print(f"✅ 所有 {len(SEED_RECIPES)} 款配方 iba_category 值合法")

    # ============================================================
    # Task 12 新增校验：difficulty/season/abv_override 字段完整性 + Mocktail 无酒精
    # ============================================================
    print("\n=== Task 12: difficulty/season/abv_override 字段完整性校验 ===")
    task12_field_errors = verify_difficulty_season_abv_bucket()
    if task12_field_errors:
        print(f"❌ {len(task12_field_errors)} 条字段完整性问题:")
        for err in task12_field_errors:
            print(f"  - {err}")
            _record_failure(f"Task 12 字段完整性: {err}")
    else:
        print(f"✅ 所有 {len(SEED_RECIPES)} 款配方 difficulty/season/abv_override 合法")

    print("\n=== Task 12: Mocktail 材料无酒精校验 ===")
    task12_mocktail_errors = verify_mocktail_ingredients_no_alcohol()
    if task12_mocktail_errors:
        print(f"❌ {len(task12_mocktail_errors)} 条 Mocktail 含酒精问题:")
        for err in task12_mocktail_errors:
            print(f"  - {err}")
            _record_failure(f"Task 12 Mocktail 含酒精: {err}")
    else:
        print("✅ 所有 Mocktail 配方材料均无酒精")

    # ============================================================
    # Task 5 新增校验：百科文档与新增材料完整性
    # ============================================================
    print("\n=== Task 5: 百科文档与新增材料校验 ===")
    if not verify_encyclopedia_docs():
        _record_failure("百科文档/新增材料校验失败（详见上方输出）")

    # ============================================================
    # 汇总退出码
    # ============================================================
    print("\n=== 汇总 ===")
    if _FAILURES:
        print(f"❌ 共 {len(_FAILURES)} 条校验失败，详见上方输出。")
        sys.exit(1)
    else:
        print(f"✅ 全部校验通过（共 {len(SEED_RECIPES)} 款种子配方，{len(INGREDIENT_REGISTRY)} 条材料注册）。")


if __name__ == "__main__":
    main()
