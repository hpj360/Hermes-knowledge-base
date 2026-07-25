"""材料强度与营养计算模块（G2）。

数据源：
- ingredients.py 的 ABV 注册表（本地权威）
- IBA ingredients_strength.json（远程校验补充）
- 卡路里公式：Volume(ml) × ABV × 0.789(酒精密度) × 7(kcal/g) = 纯酒精卡路里

参考公式来源：basicfreetools.com Alcohol Calorie Calculator
"""
from __future__ import annotations

import logging

import httpx

from hermes_kb import ingredients

_logger = logging.getLogger(__name__)

# IBA dataset 仓库基础 URL（分支在 fetch 时拼接，避免硬编码 master 导致 main 分支永远不被尝试）
IBA_REPO = "lmc2179/iba_dataset_json"
IBA_RAW_BASE = f"https://raw.githubusercontent.com/{IBA_REPO}"

# 无体积时的估算假设（ml）：按材料分类给默认体积
# 烈酒 45ml，利口酒 15ml，果汁 30ml，糖浆 10ml，装饰 0ml
_VOLUME_BY_CATEGORY = {
    "base_spirit": 45.0,
    "juice": 30.0,
    "garnish": 0.0,
    "wine": 90.0,
}


def get_ingredient_abv(name: str) -> float:
    """通过 ingredients.canonicalize 归一化后查 ABV，未知返回 0.0。"""
    canonical = ingredients.canonicalize(name)
    return ingredients.get_abv(canonical)


def get_ingredient_abv_with_fallback(
    name: str,
    strength_data: dict[str, float] | None = None,
) -> float:
    """先查本地注册表，未命中或返回 0.0 时回退到 IBA strength_data。

    本地 ingredients.py 是权威源，但 IBA dataset 中部分英文材料名
    （如 "1 sugar cube" / "half lime cut into 4 wedges" 等带数量短语）
    未在别名索引中，此时 strength_data 提供兜底 ABV，避免 ABV 计算偏少。

    Args:
        name: 材料英文名（IBA dataset 原文）
        strength_data: IBA ingredients_strength.json 解析后的 dict

    Returns:
        0.0-1.0 的小数；两边都未命中返回 0.0。
    """
    local_abv = get_ingredient_abv(name)
    if local_abv > 0:
        return local_abv
    if not strength_data or not name:
        return 0.0
    try:
        return float(strength_data.get(name.strip().lower(), 0.0))
    except (TypeError, ValueError):
        return 0.0


def calculate_cocktail_abv(
    ingredients_list: list[tuple[str, float]],
    strength_data: dict[str, float] | None = None,
) -> float:
    """加权平均 ABV。

    Args:
        ingredients_list: [(材料名, 体积ml), ...]
        strength_data: 可选的 IBA strength 兜底映射

    Returns:
        0.0-1.0 的小数；总体积为 0 时返回 0.0。
    """
    total_volume = sum(vol for _, vol in ingredients_list)
    if total_volume <= 0:
        return 0.0
    weighted = sum(
        get_ingredient_abv_with_fallback(name, strength_data) * vol
        for name, vol in ingredients_list
    )
    return weighted / total_volume


def calculate_alcohol_calories(volume_ml: float, abv: float) -> float:
    """纯酒精卡路里：volume_ml × abv × 0.789 × 7。"""
    return volume_ml * abv * 0.789 * 7


def _estimate_volume(canonical: str) -> float:
    """根据材料分类估算单次用量（ml）。"""
    category = ingredients.get_category(canonical)
    if category == "modifier":
        # 利口酒（含酒精）15ml，糖浆/无酒精辅料 10ml
        return 15.0 if ingredients.get_abv(canonical) > 0 else 10.0
    return _VOLUME_BY_CATEGORY.get(category, 15.0)


def estimate_recipe_stats(ingredient_names: list[str]) -> dict:
    """无体积时的配方强度估算。

    假设：烈酒 45ml，利口酒 15ml，果汁 30ml，糖浆 10ml，装饰 0ml。

    Returns:
        {"estimated_abv": float, "estimated_calories": float, "total_volume_ml": float}
    """
    total_volume = 0.0
    weighted_abv = 0.0
    total_calories = 0.0

    for name in ingredient_names:
        canonical = ingredients.canonicalize(name)
        abv = ingredients.get_abv(canonical)
        vol = _estimate_volume(canonical)
        total_volume += vol
        weighted_abv += abv * vol
        total_calories += calculate_alcohol_calories(vol, abv)

    estimated_abv = weighted_abv / total_volume if total_volume > 0 else 0.0
    return {
        "estimated_abv": estimated_abv,
        "estimated_calories": total_calories,
        "total_volume_ml": total_volume,
    }


def fetch_iba_strength_data() -> dict[str, float]:
    """从 IBA GitHub 拉取 ingredients_strength.json。

    尝试顺序：直连 GitHub (master → main) → gh-proxy 镜像 (master → main) → 本地文件。

    Returns:
        {材料英文名: ABV小数}；全部失败返回空 dict。
    """
    from pathlib import Path

    data: dict | None = None

    # 直连 GitHub
    for branch in ("master", "main"):
        try:
            url = f"{IBA_RAW_BASE}/{branch}/ingredients_strength.json"
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            break
        except (httpx.HTTPError, ValueError, OSError) as e:
            _logger.info("IBA strength direct fetch (%s) failed: %s", branch, e)
            continue

    # gh-proxy 镜像
    if data is None:
        for branch in ("master", "main"):
            try:
                url = (
                    f"https://gh-proxy.com/{IBA_RAW_BASE}/{branch}/"
                    f"ingredients_strength.json"
                )
                resp = httpx.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                break
            except (httpx.HTTPError, ValueError, OSError) as e:
                _logger.info("IBA strength mirror fetch (%s) failed: %s", branch, e)
                continue

    # 本地文件回退
    if data is None:
        local_file = Path(__file__).parent.parent.parent / "data" / "iba_strength.json"
        if local_file.exists():
            import json
            with open(local_file, encoding="utf-8") as f:
                data = json.load(f)
            _logger.info("IBA strength: using local file %s", local_file)
        else:
            return {}

    result: dict[str, float] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            try:
                result[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
    return result
