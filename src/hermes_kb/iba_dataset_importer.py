"""IBA 官方配方数据集导入器（B3）。

数据源：lmc2179/iba_dataset_json GitHub 仓库
- recipes.json：IBA 全部配方（~100 款），单位 cl
- ingredients_strength.json：每种成分 ABV 映射

IBA 金标准配方 verified=True，直接进实验室匹配。
单位转换：cl → ml（1cl = 10ml）。
"""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document
from hermes_kb.rag import ImportService

_logger = logging.getLogger(__name__)

# IBA dataset 仓库 URL
IBA_REPO = "lmc2179/iba_dataset_json"
IBA_RAW_BASE = f"https://raw.githubusercontent.com/{IBA_REPO}/master"


def _normalize_ingredient(en_name: str) -> tuple[str, bool]:
    """英文材料名 → 中文标准名。

    复用 ingredients 模块的别名索引（与种子配方共享归一化口径）。

    Returns:
        (normalized_name, is_unknown)
    """
    if not en_name:
        return ("", True)
    stripped = en_name.strip()
    key = stripped.lower()
    try:
        from hermes_kb.ingredients import _ALIAS_INDEX

        if key in _ALIAS_INDEX:
            return (_ALIAS_INDEX[key], False)
    except ImportError:
        pass
    # 未命中别名表，保留原名并标记为未知
    return (stripped, True)


def parse_iba_recipe(
    raw: dict[str, Any],
    strength_data: dict[str, float] | None = None,
) -> dict[str, Any]:
    """解析 IBA dataset 单条配方。

    IBA dataset 格式：
    {
        "name": "MOJITO",
        "ingredients": [{"name": "white rum", "quantity": 4.5}, ...],
        "type": "Contemporary Classics"
    }
    quantity 单位为 cl，需转 ml。

    M2: 当 ingredients 含 volume 信息时，计算配方整体 ABV 与卡路里
    并写入 content frontmatter（<!-- abv --> / <!-- calories -->）。
    """
    title = raw.get("name", "").strip()
    category_official = raw.get("type", "")
    raw_ingredients = raw.get("ingredients", [])

    ingredients: list[str] = []
    measures: list[str] = []
    unknown: list[str] = []

    for ing in raw_ingredients:
        en_name = ing.get("name", "").strip()
        quantity = ing.get("quantity")
        normalized, is_unknown = _normalize_ingredient(en_name)
        # _normalize_ingredient 对未知材料返回原名（非空），故 normalized 恒非空
        ingredients.append(normalized if normalized else en_name)
        if is_unknown and en_name:
            unknown.append(en_name)
        # cl → ml 转换
        if quantity is not None:
            measures.append(f"{float(quantity) * 10:.0f}ml")
        else:
            measures.append("适量")

    # M2: ABV/卡路里计算（quantity 非 None 时收集 volume，cl → ml）
    abv: float | None = None
    calories: float | None = None
    volume_pairs: list[tuple[str, float]] = []
    for ing in raw_ingredients:
        en_name = ing.get("name", "").strip()
        quantity = ing.get("quantity")
        if quantity is not None and en_name:
            try:
                volume_ml = float(quantity) * 10  # cl → ml
                volume_pairs.append((en_name, volume_ml))
            except (ValueError, TypeError):
                pass

    if volume_pairs:
        try:
            from hermes_kb.ingredient_strength import (
                calculate_alcohol_calories,
                calculate_cocktail_abv,
                get_ingredient_abv,
            )

            abv = calculate_cocktail_abv(volume_pairs)
            total_calories = sum(
                calculate_alcohol_calories(vol, get_ingredient_abv(name))
                for name, vol in volume_pairs
            )
            calories = round(total_calories, 1)
        except Exception:
            pass

    # 构建 content（含 frontmatter，供 recipe_match 优先解析）
    ing_str = "|".join(ingredients)
    content_lines = [f"<!-- ingredients: {ing_str} -->"]
    if abv is not None and abv > 0:
        content_lines.append(f"<!-- abv: {abv:.3f} -->")
    if calories is not None and calories > 0:
        content_lines.append(f"<!-- calories: {calories:.0f} -->")
    content_lines.append(f"# {title}\n\n## 配方")
    for ing, measure in zip(ingredients, measures):
        content_lines.append(f"- {ing} {measure}")
    content_lines.append(f"\n## 分类\n{category_official}")
    if unknown:
        content_lines.append(f"\n## 未归一化材料\n{', '.join(unknown)}")
    content = "\n".join(content_lines)

    return {
        "title": title,
        "ingredients": ingredients,
        "content": content,
        "source": "iba",
        "verified": True,
        "category_official": category_official,
        "unknown_ingredients": unknown,
        "abv": abv,
        "calories": calories,
    }


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r"[\s\-_/\\,.!?;:'\"()]+", "", title.lower())


def _tokenize_title(title: str) -> frozenset[str]:
    if not title:
        return frozenset()
    tokens = re.findall(r"[a-z0-9\u4e00-\u9fff]+", title.lower())
    return frozenset(t for t in tokens if t)


def _preload_dedup_index() -> tuple[set[str], set[str], list[frozenset[str]]]:
    iba_exact: set[str] = set()
    recipe_exact: set[str] = set()
    recipe_tokens: list[frozenset[str]] = []
    with get_session() as session:
        rows = session.exec(
            select(Document.title, Document.source).where(
                Document.category == "recipe"
            )
        ).all()
    for title, source in rows:
        if not title:
            continue
        norm = _normalize_title(title)
        if source == "iba" and norm:
            iba_exact.add(norm)
        if norm:
            recipe_exact.add(norm)
        toks = _tokenize_title(title)
        if toks:
            recipe_tokens.append(toks)
    return iba_exact, recipe_exact, recipe_tokens


def _is_duplicate_fuzzy(
    candidate_title: str,
    iba_exact: set[str],
    recipe_exact: set[str],
    recipe_token_list: list[frozenset[str]],
) -> bool:
    if not candidate_title:
        return False
    norm = _normalize_title(candidate_title)
    if not norm:
        return False
    if norm in iba_exact or norm in recipe_exact:
        return True
    if len(norm) < 4:
        return False
    cand_tokens = _tokenize_title(candidate_title)
    if not cand_tokens:
        return False
    for existing_tokens in recipe_token_list:
        if not existing_tokens:
            continue
        if cand_tokens <= existing_tokens or existing_tokens <= cand_tokens:
            return True
    return False


def sync_iba_dataset(
    data: list[dict[str, Any]] | None = None,
    importer: ImportService | None = None,
) -> dict[str, Any]:
    """从 IBA dataset 导入配方。

    Args:
        data: IBA 配方列表。若为 None，尝试从 GitHub 拉取。
        importer: 可选的 ImportService 实例（由 router 通过 app.state 注入）。

    Returns:
        {imported, skipped, failed, unknown_ingredients}
    """
    if data is None:
        data = _fetch_remote_data()
        strength_data: dict[str, float] | None = None
        try:
            from hermes_kb.ingredient_strength import fetch_iba_strength_data

            strength_data = fetch_iba_strength_data()
        except Exception as e:
            _logger.warning("IBA strength data fetch failed: %s", e)
    else:
        strength_data = None

    if not data:
        return {"imported": 0, "skipped": 0, "failed": 0, "unknown_ingredients": []}

    imported = 0
    skipped = 0
    failed = 0
    all_unknown: list[str] = []
    importer = importer or ImportService()
    iba_exact, recipe_exact, recipe_tokens = _preload_dedup_index()

    for raw in data:
        try:
            recipe = parse_iba_recipe(raw, strength_data=strength_data)
            all_unknown.extend(recipe.pop("unknown_ingredients", []))

            # 去重
            if _is_duplicate_fuzzy(recipe["title"], iba_exact, recipe_exact, recipe_tokens):
                skipped += 1
                continue

            # P2-3: 治理字段（IBA 金标准 verified=True/status=published）原子落库，
            # 消除两阶段非原子。
            result = importer.import_text(
                content=recipe["content"],
                title=recipe["title"],
                category="recipe",
                source="iba",
                verified=True,  # IBA 金标准
                status="published",
            )
            doc_id = result.get("doc_id") if isinstance(result, dict) else result
            if doc_id:
                imported += 1
                # 同批次去重更新
                norm = _normalize_title(recipe["title"])
                if norm:
                    iba_exact.add(norm)
                    recipe_exact.add(norm)
                toks = _tokenize_title(recipe["title"])
                if toks:
                    recipe_tokens.append(toks)
            else:
                failed += 1
        except Exception as e:
            _logger.warning("IBA recipe import failed for item: %s", e)
            failed += 1

    return {
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
        "unknown_ingredients": list(set(all_unknown)),
    }


def _fetch_remote_data() -> list[dict[str, Any]]:
    """从 GitHub 拉取 IBA dataset。

    尝试顺序：
    1. raw.githubusercontent.com (master → main)
    2. gh-proxy.com 镜像 (master → main)
    3. 本地 data/iba_recipes.json 文件
    """
    from pathlib import Path

    # 直连 GitHub
    for branch in ("master", "main"):
        try:
            url = f"https://raw.githubusercontent.com/lmc2179/iba_dataset_json/{branch}/recipes.json"
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError, OSError) as e:
            if branch == "master":
                _logger.info("IBA dataset master branch failed, trying main: %s", e)
                continue
            _logger.warning("IBA dataset direct fetch failed: %s", e)

    # gh-proxy 镜像
    for branch in ("master", "main"):
        try:
            url = f"https://gh-proxy.com/https://raw.githubusercontent.com/lmc2179/iba_dataset_json/{branch}/recipes.json"
            resp = httpx.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError, OSError) as e:
            if branch == "master":
                _logger.info("IBA dataset mirror master failed, trying main: %s", e)
                continue
            _logger.warning("IBA dataset mirror fetch failed: %s", e)

    # 本地文件回退
    local_file = Path(__file__).parent.parent.parent / "data" / "iba_recipes.json"
    if local_file.exists():
        _logger.info("IBA dataset: using local file %s", local_file)
        import json
        with open(local_file, encoding="utf-8") as f:
            return json.load(f)

    return []


def diff_iba_official(
    local_data: list[dict] | None = None,
    official_data: list[dict] | None = None,
) -> dict[str, Any]:
    """对比本地 IBA 配方与官方数据集，报告差异。

    Args:
        local_data: 本地 DB 中 source='iba' 的配方列表（None 时从 DB 查询）。
            每项可为 {"title": ...} 或 IBA 风格 {"name": ...}。
        official_data: IBA 官方数据集（None 时从 GitHub 拉取）。

    Returns:
        {
            "local_count": int,
            "official_count": int,
            "missing_locally": list[str],   # 官方有但本地没有的配方名（小写）
            "extra_locally": list[str],     # 本地有但官方没有的（小写）
            "matched": list[str],           # 两边都有的（小写）
        }
    """
    # 1. 收集本地配方名
    if local_data is None:
        local_rows: list[str] = []
        with get_session() as session:
            rows = session.exec(
                select(Document.title).where(Document.source == "iba")
            ).all()
            local_rows = [t for t in rows if t]
        local_items: list[dict] = [{"title": t} for t in local_rows]
    else:
        local_items = list(local_data)

    # 2. 收集官方数据集
    if official_data is None:
        official_items = _fetch_remote_data()
    else:
        official_items = list(official_data)

    def _title_of(item: dict) -> str:
        if not isinstance(item, dict):
            return ""
        # 官方数据集用 "name"，本地用 "title"；兼容两种
        return str(item.get("name") or item.get("title") or "").strip()

    local_set = {_title_of(it).lower() for it in local_items if _title_of(it)}
    official_set = {_title_of(it).lower() for it in official_items if _title_of(it)}

    return {
        "local_count": len(local_set),
        "official_count": len(official_set),
        "missing_locally": sorted(official_set - local_set),
        "extra_locally": sorted(local_set - official_set),
        "matched": sorted(local_set & official_set),
    }
