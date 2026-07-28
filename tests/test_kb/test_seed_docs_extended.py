# -*- coding: utf-8 -*-
"""Task 6：百科种子文档扩展测试。

覆盖：
- SEED_DOCS 规模与结构（>= 15 篇，含 title/content）
- 百科内容质量（长度、H2 标题、标题唯一）
- 新增 10 篇百科覆盖（伏特加/白兰地/利口酒/苦精/味美思/糖浆辅料/器具/术语/清酒/烧酒）
- seed_encyclopedia() 函数幂等性与字段写入（需 DB）
- INGREDIENT_REGISTRY 新增 15 条目（归一化/注册/字段完整性）

DB 测试依赖 tests/test_kb/conftest.py 的 autouse ``tmp_db`` fixture，
每个测试自动获得独立临时 SQLite 数据库（通过 KB_DB_PATH 环境变量注入）。
"""
from __future__ import annotations


# ===========================================================================
# 1. SEED_DOCS 规模与结构测试
# ===========================================================================
def test_seed_docs_count_meets_minimum():
    """SEED_DOCS 应不少于 15 篇（5 原有 + 10 新增百科）。"""
    from hermes_kb.seed import SEED_DOCS

    assert len(SEED_DOCS) >= 15, f"SEED_DOCS 仅 {len(SEED_DOCS)} 篇，未达 15 篇基线"


def test_seed_docs_structure():
    """每篇百科应是 dict，含非空 title 与 content（均为 str）。"""
    from hermes_kb.seed import SEED_DOCS

    issues: list[tuple[int, str]] = []
    for idx, doc in enumerate(SEED_DOCS):
        if not isinstance(doc, dict):
            issues.append((idx, "非 dict"))
            continue
        title = doc.get("title")
        if not isinstance(title, str) or not title:
            issues.append((idx, "title 缺失或非 str"))
        content = doc.get("content")
        if not isinstance(content, str) or not content:
            issues.append((idx, "content 缺失或非 str"))
    assert not issues, f"结构问题: {issues}"


# ===========================================================================
# 2. 百科内容质量测试
# ===========================================================================
def test_seed_docs_content_length():
    """每篇 content 长度应 >= 500 字符。"""
    from hermes_kb.seed import SEED_DOCS

    short = [(d["title"], len(d["content"])) for d in SEED_DOCS if len(d["content"]) < 500]
    assert not short, f"content 过短: {short}"


def test_seed_docs_content_has_h2_headings():
    """每篇 content 应含 >= 3 个 `## ` 二级标题（不含 `### ` 三级标题）。"""
    from hermes_kb.seed import SEED_DOCS

    insufficient: list[tuple[str, int]] = []
    for d in SEED_DOCS:
        # `## ` 前缀已排除 `### `（第 3 字符为 `#` 而非空格）
        h2_count = sum(
            1 for line in d["content"].splitlines() if line.startswith("## ")
        )
        if h2_count < 3:
            insufficient.append((d["title"], h2_count))
    assert not insufficient, f"H2 标题不足 3 个: {insufficient}"


def test_seed_docs_titles_unique():
    """所有百科标题应唯一。"""
    from hermes_kb.seed import SEED_DOCS

    titles = [d["title"] for d in SEED_DOCS]
    duplicates = {t for t in titles if titles.count(t) > 1}
    assert not duplicates, f"标题重复: {duplicates}"


# ===========================================================================
# 3. 新增百科覆盖测试
# ===========================================================================
def test_new_encyclopedia_titles_present():
    """10 篇新增百科标题必须存在于 SEED_DOCS。"""
    from hermes_kb.seed import SEED_DOCS

    titles = {d["title"] for d in SEED_DOCS}
    must_have = [
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
    missing = [t for t in must_have if t not in titles]
    assert not missing, f"缺少新增百科: {missing}"


# ===========================================================================
# 4. seed_encyclopedia() 函数测试（需 DB）
#
# 依赖 conftest.py 的 autouse tmp_db fixture（提供独立临时 SQLite）。
# 显式调用 seed_encyclopedia()，不依赖全局播种 fixture，以验证函数本身幂等性。
# ===========================================================================
def test_seed_encyclopedia_first_run():
    """空 DB 首次调用 seed_encyclopedia() 应全部导入，无跳过无失败。"""
    from hermes_kb.seed import SEED_DOCS, seed_encyclopedia

    result = seed_encyclopedia()
    expected = len(SEED_DOCS)
    assert result["seeded"] == expected, (
        f"首次导入 expected seeded={expected}, got {result['seeded']}"
    )
    assert result["skipped"] == 0, f"首次导入不应跳过，got skipped={result['skipped']}"
    assert result["failed"] == 0, f"首次导入不应失败，got failed={result['failed']}"


def test_seed_encyclopedia_idempotent():
    """二次调用 seed_encyclopedia() 应全部跳过，无新增无失败。"""
    from hermes_kb.seed import SEED_DOCS, seed_encyclopedia

    first = seed_encyclopedia()
    assert first["seeded"] == len(SEED_DOCS)

    second = seed_encyclopedia()
    assert second["seeded"] == 0, f"二次导入不应再导入，got seeded={second['seeded']}"
    assert second["skipped"] == len(SEED_DOCS), (
        f"二次导入 expected skipped={len(SEED_DOCS)}, got {second['skipped']}"
    )
    assert second["failed"] == 0, f"二次导入不应失败，got failed={second['failed']}"


def test_seed_encyclopedia_category_written():
    """导入后所有新百科的 category/source/source_type 字段应正确写入。"""
    from sqlmodel import select

    from hermes_kb.database import get_session
    from hermes_kb.models import Document
    from hermes_kb.seed import SEED_DOCS, seed_encyclopedia

    seed_encyclopedia()

    expected_titles = {d["title"] for d in SEED_DOCS}
    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.source == "seed")
        ).all()
        encyc = [d for d in docs if d.title in expected_titles]
        assert len(encyc) == len(SEED_DOCS), (
            f"导入数 {len(encyc)} != SEED_DOCS 数 {len(SEED_DOCS)}"
        )
        bad: list[tuple[str, str, str, str]] = []
        for d in encyc:
            if d.category != "encyclopedia":
                bad.append((d.title, "category", d.category, "encyclopedia"))
            if d.source != "seed":
                bad.append((d.title, "source", d.source, "seed"))
            if d.source_type != "seed":
                bad.append((d.title, "source_type", d.source_type, "seed"))
        assert not bad, f"字段写入错误: {bad}"


def test_seed_encyclopedia_returns_items():
    """返回的 items 列表长度应为 SEED_DOCS 数，每项含 title 与 status。"""
    from hermes_kb.seed import SEED_DOCS, seed_encyclopedia

    result = seed_encyclopedia()
    items = result["items"]
    assert len(items) == len(SEED_DOCS), (
        f"items 长度 {len(items)} != {len(SEED_DOCS)}"
    )
    bad: list[tuple[int, str]] = []
    for idx, item in enumerate(items):
        if "title" not in item:
            bad.append((idx, "缺 title"))
        if "status" not in item:
            bad.append((idx, "缺 status"))
    assert not bad, f"items 字段缺失: {bad}"


# ===========================================================================
# 5. INGREDIENT_REGISTRY 新增条目测试
# ===========================================================================
def test_new_ingredients_canonicalize():
    """新增材料的别名归一化应正确。

    注意：新增 shochu_jp 条目（canonical="烧酎"）的 alias "shochu" 会覆盖
    旧 shochu 条目（canonical="日本烧酎"），因此 canonicalize("shochu") 返回 "烧酎"。
    """
    from hermes_kb.ingredients import canonicalize

    # sake / 清酒 都应归一化为 "清酒"
    assert canonicalize("sake") == "清酒", (
        f'canonicalize("sake")={canonicalize("sake")!r}, expected "清酒"'
    )
    assert canonicalize("清酒") == "清酒"
    assert canonicalize("sake") == canonicalize("清酒")

    # soju / 烧酒 都应归一化为 "烧酒"
    assert canonicalize("soju") == "烧酒", (
        f'canonicalize("soju")={canonicalize("soju")!r}, expected "烧酒"'
    )
    assert canonicalize("烧酒") == "烧酒"
    assert canonicalize("soju") == canonicalize("烧酒")

    # shochu 归一化为 "烧酎"（新增 shochu_jp 条目覆盖旧 shochu 条目）
    assert canonicalize("shochu") == "烧酎", (
        f'canonicalize("shochu")={canonicalize("shochu")!r}, expected "烧酎"'
    )

    # Lillet 归一化为 "力洛酒"
    assert canonicalize("Lillet") == "力洛酒", (
        f'canonicalize("Lillet")={canonicalize("Lillet")!r}, expected "力洛酒"'
    )

    # 蜂蜜糖浆 归一化为自身（已在 registry 注册）
    assert canonicalize("蜂蜜糖浆") == "蜂蜜糖浆"


def test_new_ingredients_in_registry():
    """15 个新增 canonical 名应存在于 INGREDIENT_REGISTRY。"""
    from hermes_kb.ingredients import INGREDIENT_REGISTRY

    canonicals = {info["canonical"] for info in INGREDIENT_REGISTRY.values()}
    must_have = [
        "纯米酒",
        "本酿造",
        "纯米大吟酿",
        "大吟酿",
        "烧酎",
        "力洛酒",
        "多林味美思",
        "诺瓦利帕味美思",
        "奎纳味美思",
        "薰衣草糖浆",
        "方块冰",
        "碎冰",
        "老冰",
        "球冰",
        "冰沙",
    ]
    missing = [c for c in must_have if c not in canonicals]
    assert not missing, f"未注册的新增材料: {missing}"


def test_new_ingredients_fields_complete():
    """新增条目的 aliases（list 非空）与 category（str 非空）字段应完整。"""
    from hermes_kb.ingredients import INGREDIENT_REGISTRY

    must_have = [
        "纯米酒",
        "本酿造",
        "纯米大吟酿",
        "大吟酿",
        "烧酎",
        "力洛酒",
        "多林味美思",
        "诺瓦利帕味美思",
        "奎纳味美思",
        "薰衣草糖浆",
        "方块冰",
        "碎冰",
        "老冰",
        "球冰",
        "冰沙",
    ]
    issues: list[tuple[str, str]] = []
    for canonical_name in must_have:
        info = None
        for v in INGREDIENT_REGISTRY.values():
            if v["canonical"] == canonical_name:
                info = v
                break
        if info is None:
            issues.append((canonical_name, "未找到"))
            continue
        aliases = info.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            issues.append((canonical_name, f"aliases 不完整: {aliases!r}"))
        category = info.get("category")
        if not isinstance(category, str) or not category:
            issues.append((canonical_name, f"category 不完整: {category!r}"))
    assert not issues, f"新增条目字段问题: {issues}"
