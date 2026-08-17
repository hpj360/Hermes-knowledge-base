"""配方结构化字段工具（V6-Phase 2）。

从配方 content 的 ``## 配方`` 段落解析结构化用料表，并推断
``base_spirit`` / ``abv`` / ``ingredients_json`` 三个结构化字段：

- ``parse_recipe_section``：解析用料表为 ``[{name, measure, amount_ml}]``
- ``infer_base_spirit``：从材料列表推断基酒（gin/vodka/rum/whiskey/tequila/brandy/other）
- ``compute_abv``：按实际体积加权平均计算酒精度（0.0-1.0）
- ``build_ingredients_json``：序列化为 ``[{"name": "...", "measure": "..."}]``
- ``structured_from_content``：一键入口（content → 三字段）

兼容数据源格式：
- iba_official / iba / seed：``- 金酒 60ml``、``- 干邑白兰地 30ml``
- thecocktaildb：``- 金酒 1 3/4 shot``（shot 单位，1 shot ≈ 45ml）
- bar_assistant：``- 60 ml 金酒``（数量在前）

设计说明：
- 解析失败不抛异常，返回可用的最佳结果（空用料表/空基酒/abv=0），
  保证回填脚本对全部配方幂等可重跑、不因单条脏数据中断。
"""
from __future__ import annotations

import json
import re
from typing import Any

from hermes_kb.ingredients import canonicalize, get_category

# 标准基酒标识（models.base_spirit 枚举）
_BASE_SPIRIT_IDS = (
    "gin",
    "vodka",
    "rum",
    "whiskey",
    "tequila",
    "brandy",
    "other",
)

# 中文标准名 → 基酒标识（显式映射，优先于注册表类目判断）
_BASE_SPIRIT_NAME_MAP: dict[str, str] = {
    "金酒": "gin",
    "荷兰金酒": "gin",
    "老汤姆金酒": "gin",
    "gin": "gin",
    "london dry gin": "gin",
    "dry gin": "gin",
    "old tom gin": "gin",
    "伏特加": "vodka",
    "小麦伏特加": "vodka",
    "柠檬伏特加": "vodka",
    "风味伏特加": "vodka",
    "vodka": "vodka",
    "朗姆酒": "rum",
    "白朗姆酒": "rum",
    "黑朗姆酒": "rum",
    "陈年朗姆酒": "rum",
    "香料朗姆酒": "rum",
    "金朗姆酒": "rum",
    "高度朗姆酒": "rum",
    "151朗姆酒": "rum",
    "卡沙萨": "rum",
    "rum": "rum",
    "white rum": "rum",
    "dark rum": "rum",
    "light rum": "rum",
    "gold rum": "rum",
    "spiced rum": "rum",
    "overproof rum": "rum",
    "white cuban ron": "rum",
    "jamaican rum": "rum",
    "bacardi": "rum",
    "cachaca": "rum",
    "威士忌": "whiskey",
    "波本威士忌": "whiskey",
    "黑麦威士忌": "whiskey",
    "苏格兰威士忌": "whiskey",
    "爱尔兰威士忌": "whiskey",
    "田纳西威士忌": "whiskey",
    "加拿大威士忌": "whiskey",
    "日本威士忌": "whiskey",
    "小麦威士忌": "whiskey",
    "玉米威士忌": "whiskey",
    "whiskey": "whiskey",
    "whisky": "whiskey",
    "bourbon": "whiskey",
    "scotch": "whiskey",
    "irish whiskey": "whiskey",
    "rye whiskey": "whiskey",
    "tennessee whiskey": "whiskey",
    "龙舌兰": "tequila",
    "白龙舌兰": "tequila",
    "微陈龙舌兰": "tequila",
    "陈酿龙舌兰": "tequila",
    "梅斯卡尔": "tequila",
    "手工艺梅斯卡尔": "tequila",
    "tequila": "tequila",
    "mezcal": "tequila",
    "白兰地": "brandy",
    "干邑白兰地": "brandy",
    "雅文邑": "brandy",
    "苹果白兰地": "brandy",
    "格拉帕": "brandy",
    "樱桃白兰地": "brandy",
    "XO干邑": "brandy",
    "VSOP干邑": "brandy",
    "皮斯科": "brandy",
    "brandy": "brandy",
    "cognac": "brandy",
    "armagnac": "brandy",
    "applejack": "brandy",
    "pisco": "brandy",
    "calvados": "brandy",
    "grappa": "brandy",
}

# 体积换算：oz / shot → ml（近似，1 oz = 1 shot ≈ 30/45ml 常用约定）
_ML_PER_OZ = 30.0
_ML_PER_SHOT = 45.0

# 配方段落行解析
_RECIPE_LINE_RE = re.compile(r"^-\s*(.+)$")

# 体积/数量单位（含复数；part 按相对比例参与加权，见 _to_ml）
_UNIT_ALTS = (
    "ml|cl|oz|shot|shots|dash|dashes|splash|splashes|drop|drops|pinch|pinches|"
    "part|parts|bar\\s*spoon|bar\\s*spoons|cup|cups|tsp|tsps|tblsp|tblsps|"
    "tbsp|tbsps|pint|pints|qt|qts|fifth|fifths|l|can|cans|bottle|bottles"
)
_UNIT_PATTERN = f"(?:{_UNIT_ALTS})"

# 数量写法："1" / "1.5" / "1 1/2" / "1 3/4" / "3/4" / "1-2"（范围取中点）
_AMOUNT_PATTERN = (
    r"\d+(?:\.\d+)?(?:\s+\d+/\d+)?|\d+/\d+|\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?"
)
# 单位前的形容词（"1 small bottle" / "2 fresh limes"）
_UNIT_ADJ = r"(?:small|large|big|whole|fresh|extra|standard)"

# 数量在前："60 ml 金酒" / "1.5 oz Gin" / "2 cups 水"（必须有单位，避免误吞名称首字）
_MEASURE_FIRST_RE = re.compile(
    rf"^(?:约\s*)?({_AMOUNT_PATTERN})\s*(?:{_UNIT_ADJ})?\s*({_UNIT_PATTERN})\s+(.+)$",
    re.IGNORECASE,
)
# 名称在前："金酒 60ml" / "干味美思 10 ml" / "金酒 1 3/4 shot" / "伏特加 3 parts"
# 数量支持 "1 3/4"（整+分）/"3/4"（分）/"1.5"（小数）/"1-2"（范围）三种写法；
# 单位可带复数，单位后允许跟品牌/质地描述（如 "Everclear 1 fifth Smirnoff red label"，
# 描述不参与结构化，仅保留纯材料名）。
_NAME_FIRST_RE = re.compile(
    rf"^(.+?)\s+({_AMOUNT_PATTERN})\s*(?:{_UNIT_ADJ})?\s*({_UNIT_PATTERN})?(?:\s+.*)?$",
    re.IGNORECASE,
)


_UNIT_ML = {
    "ml": 1.0,
    "cl": 10.0,
    "oz": 30.0,
    "shot": 45.0,
    "cup": 240.0,
    "tsp": 5.0,
    "tblsp": 15.0,
    "tbsp": 15.0,
    "pint": 473.0,
    "qt": 946.0,
    "fifth": 757.0,
    "l": 1000.0,
    "can": 355.0,
    "bottle": 750.0,
    "barspoon": 5.0,
    "bar spoon": 5.0,
    "drop": 0.05,
    "dash": 0.6,
    "pinch": 0.3,
    "splash": 5.0,
}


def _to_ml(amount: float, unit: str) -> float:
    """单位换算为 ml。未知单位返回 0.0（不会影响加权平均）。

    ``part`` 为相对比例单位，映射为固定 30ml（1 part 假设）——
    对加权平均 ABV 结果等价（权重只看相对比例），同时保证有体积。
    """
    if not unit:
        return amount  # 无单位时视为 ml
    u = unit.strip().lower().replace(" ", "")
    factor = _UNIT_ML.get(u)
    # 复数单位（cups/shots/pints...）归一为单数再查表
    if factor is None and u.endswith("s"):
        factor = _UNIT_ML.get(u[:-1])
    if factor is not None:
        return amount * factor
    # "part" 按相对比例参与加权（1 part ≈ 30ml，不影响 ABV 比例）
    if u in ("part", "parts"):
        return amount * 30.0
    # 整体/片状等无体积材料（薄荷枝、方糖等）不参与加权
    if u in ("whole", "slice", "slices", "piece", "pieces", "package"):
        return 0.0
    return 0.0


def _split_fraction(text: str) -> float:
    """解析 "1 3/4" / "1.5" / "3/4" / "1-2"（范围取中点）等数量写法。失败返回 0.0。"""
    text = text.strip()
    try:
        if "-" in text and "/" not in text:
            # 范围 "1-2" / "2-3"：取中点（单位不变，ABV 比例不变）
            lo, hi = text.split("-", 1)
            return (float(lo) + float(hi)) / 2.0
        if " " in text and "/" in text:
            whole, frac = text.split(" ", 1)
            num, den = frac.split("/")
            return float(whole) + float(num) / float(den)
        if "/" in text:
            num, den = text.split("/")
            return float(num) / float(den)
        return float(text)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0.0


def parse_recipe_section(content: str) -> list[dict[str, Any]]:
    """解析 ``## 配方`` 段落为结构化用料表。

    Returns:
        ``[{"name": str, "measure": str, "amount_ml": float}, ...]``
        - ``measure``：原始用量文本（如 "60ml"、"1 3/4 shot"、"适量"）
        - ``amount_ml``：换算后的毫升数（换算失败为 0.0）
        - 无法解析为带用量的行时，仅保留 ``name``（measure=""）
    """
    if not content:
        return []
    lines = content.splitlines()
    # 定位 "## 配方" 段落
    start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("## 配方"):
            start = i
            break
    if start < 0:
        return []
    items: list[dict[str, Any]] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("## ", "# ")):
            break  # 下一段落
        m = _RECIPE_LINE_RE.match(stripped)
        if not m:
            continue
        raw = m.group(1).strip()
        if not raw or raw.startswith("!"):
            continue
        # 去除尾部装饰说明（括号/顿号后）
        name, amount_ml, measure = _parse_one(raw)
        if name:
            items.append(
                {"name": name, "measure": measure or "", "amount_ml": amount_ml}
            )
    return items


def _parse_one(raw: str) -> tuple[str, float, str]:
    """解析单行用料，返回 (材料名, 换算ml, 原始用量文本)。"""
    # 尝试数量在前（bar_assistant："60 ml 金酒" / "2 cups 水"）——必须有单位
    m = _MEASURE_FIRST_RE.match(raw)
    if m:
        amount = _split_fraction(m.group(1))
        unit = m.group(2) or ""
        name = m.group(3).strip()
        ml = _to_ml(amount, unit)
        if ml > 0:
            return _clean_name(name), ml, f"{m.group(1)}{unit}"
    # 尝试名称在前（iba/thecocktaildb："金酒 60ml" / "伏特加 3 parts" / "咖啡 1/2 cup instant"）
    m = _NAME_FIRST_RE.match(raw)
    if m:
        name = m.group(1).strip()
        amount = _split_fraction(m.group(2))
        unit = m.group(3) or ""
        ml = _to_ml(amount, unit)
        if ml > 0:
            return _clean_name(name), ml, f"{m.group(2)}{unit}"
    # 无法解析用量 → 仅名称
    return _clean_name(raw), 0.0, ""


def _clean_name(name: str) -> str:
    """清理材料名：去括号注释、尾部标点与数量量词（如"橄榄 1 颗"→"橄榄"）。"""
    cleaned = re.sub(r"[（(].*?[)）]", "", name).strip()
    cleaned = cleaned.strip("·。、;；,， ")
    # 剥离尾部"数字 量词"（装饰数量，如 "1 颗"、"2 片"），保留纯材料名
    cleaned = re.sub(r"\s*\d+\s*[颗个片滴只杯把撮]s?$", "", cleaned).strip()
    return cleaned


def infer_base_spirit(ingredients: list[str]) -> str:
    """从材料列表推断基酒标识。

    规则：
    1. 显式映射命中（_BASE_SPIRIT_NAME_MAP）
    2. 注册表类目为 base_spirit 的材料（映射标准名到基酒标识）
    3. 无法判断返回 ""（由调用方决定是否标 "other"）

    Args:
        ingredients: 材料名列表（中文标准名或英文别名均可）。

    Returns:
        gin/vodka/rum/whiskey/tequila/brandy 之一，无法判断返回 ""。
    """
    if not ingredients:
        return ""
    for ing in ingredients:
        canonical = canonicalize(ing)
        mapped = _BASE_SPIRIT_NAME_MAP.get(canonical)
        if mapped:
            return mapped
    # 注册表类目兜底：任一 base_spirit 材料，映射标准名到基酒标识
    for ing in ingredients:
        canonical = canonicalize(ing)
        if get_category(canonical) == "base_spirit":
            mapped = _BASE_SPIRIT_NAME_MAP.get(canonical)
            if mapped:
                return mapped
            # 未显式映射的 base_spirit（如白酒）→ other
            return "other"
    return ""


def compute_abv(ingredients: list[dict[str, Any]]) -> float:
    """按实际体积加权平均计算酒精度（0.0-1.0）。

    全部无有效体积时，回退到 ``estimate_recipe_stats`` 的分类体积估算，
    保证 dash/pinch/splash 类无 ml 配方也能得到合理 ABV。
    """
    total_vol = 0.0
    weighted = 0.0
    for item in ingredients:
        vol = float(item.get("amount_ml") or 0.0)
        if vol <= 0:
            continue
        name = item.get("name", "")
        abv = _ingredient_abv(name)
        total_vol += vol
        weighted += abv * vol
    if total_vol > 0:
        return round(weighted / total_vol, 4)
    # 无体积兜底：分类体积估算
    names = [item.get("name", "") for item in ingredients if item.get("name")]
    if not names:
        return 0.0
    try:
        from hermes_kb.ingredient_strength import estimate_recipe_stats

        return round(estimate_recipe_stats(names).get("estimated_abv", 0.0), 4)
    except Exception:  # noqa: BLE001 — 估算失败返回 0，不阻塞
        return 0.0


def _ingredient_abv(name: str) -> float:
    """材料 ABV：查注册表（canonicalize 后 get_abv）。

    注册表未命中的常见材料兜底（TheCocktailDB / IBA 官方等外部源未归一化材料）。
    支持品牌名前缀剥离（如 "Smirnoff Vodka" → "vodka"），覆盖 IBA 官方英文名。
    """
    from hermes_kb.ingredients import get_abv

    canonical = canonicalize(name)
    abv = get_abv(canonical)
    if abv > 0:
        return abv
    # 兜底映射：常见未注册材料名（大小写不敏感）
    _ABV_FALLBACK: dict[str, float] = {
        # === 基酒类 ===
        "applejack": 0.35,
        "everclear": 0.95,
        "grain alcohol": 0.95,
        "firewater": 0.95,
        "cuban aguardiente": 0.40,
        "white cuban ron": 0.40,
        "jamaican rum": 0.40,
        "white cuban ron barcardi": 0.40,
        "bacardi limon": 0.35,
        "london dry gin": 0.40,
        "smirnoff vodka": 0.40,
        "absolut peppar": 0.40,
        "peach vodka": 0.40,
        "vodka vanilla": 0.35,
        "tequila 100% agave": 0.40,
        "100% agave tequila": 0.40,
        "blended scotch whisky": 0.40,
        "jack daniels": 0.40,
        "johnnie walker": 0.40,
        "jim beam": 0.40,
        "lagavulin 16y": 0.40,
        "wild turkey": 0.40,
        # === 利口酒/葡萄酒类 ===
        "pisang ambon": 0.20,
        "strawberry schnapps": 0.20,
        "chambord raspberry liqueur": 0.165,
        "bitter campari": 0.21,
        "crème de cassis": 0.15,
        "creme de cassis": 0.15,
        "elderflower cordial": 0.15,
        "chamomile cordial": 0.0,
        "dry white wine": 0.12,
        "amontillado sherry": 0.175,
        "palo cortado": 0.175,
        "white smooth grappa": 0.40,
        "sweet vermouth": 0.16,
        "dry vermouth": 0.16,
        # === 软饮/果汁/辅料 ===
        "mountain dew": 0.0,
        "surge": 0.0,
        "sweet and sour": 0.0,
        "sweet & sour": 0.0,
        "sweet & sour mix": 0.0,
        "corona": 0.045,
        "coca-cola": 0.0,
        "coke": 0.0,
        "dr pepper": 0.0,
        "lime cordial": 0.0,
        "lime juice cordial": 0.0,
        "lemonade": 0.0,
        "soda water": 0.0,
        "club soda": 0.0,
        "tonic water": 0.0,
        "ginger beer": 0.0,
        "ginger ale": 0.0,
        "pink grapefruit soda": 0.0,
        "caramel coloring": 0.0,
        "vanilla extract": 0.35,
        "vanilla": 0.0,
        "monin honey syrup": 0.0,
        "honey syrup": 0.0,
        "honey mix*": 0.0,
        "superfine sugar": 0.0,
        "ice": 0.0,
        "salt": 0.0,
        "sugar": 0.0,
        "honey": 0.0,
        "mint": 0.0,
        "mint leaves": 0.0,
        "orange": 0.0,
        "lemon": 0.0,
        "lime": 0.0,
        "orange peel": 0.0,
        "lemon peel": 0.0,
        "lime peel": 0.0,
        "lime wedge": 0.0,
        "lemon wedge": 0.0,
        "orange slice": 0.0,
        "cherry": 0.0,
        "maraschino cherry": 0.0,
        "olive": 0.0,
        "cocktail onion": 0.0,
        "pineapple": 0.0,
        "cucumber": 0.0,
        "cinnamon": 0.0,
        "cinnamon stick": 0.0,
        "nutmeg": 0.0,
        "egg white": 0.0,
        "egg": 0.0,
        "whole egg": 0.0,
        "milk": 0.0,
        "cream": 0.0,
        "heavy cream": 0.0,
        "half-and-half": 0.0,
        "coffee": 0.0,
        "espresso": 0.0,
        "hot coffee": 0.0,
        "chocolate": 0.0,
        "chocolate syrup": 0.0,
        "cocoa powder": 0.0,
        "pepper": 0.0,
        "black pepper": 0.0,
        "tabasco": 0.0,
        "worcestershire sauce": 0.0,
        "tomato juice": 0.0,
        "cranberry juice": 0.0,
        "grapefruit juice": 0.0,
        "pineapple juice": 0.0,
        "apple juice": 0.0,
        "orange juice": 0.0,
        "freshly squeezed orange juice": 0.0,
        "lemon juice": 0.0,
        "fresh lemon juice": 0.0,
        "lime juice": 0.0,
        "fresh lime juice": 0.0,
        "pomegranate juice": 0.0,
        "cranberry": 0.0,
        "grapefruit": 0.0,
        "apple": 0.0,
        "raw honey": 0.0,
        # === 品牌/利口酒特例 ===
        "cherry heering": 0.20,
        "hot damn": 0.40,
        "anis": 0.35,
        "rose": 0.12,
        "apfelkorn": 0.15,
        "absolut kurant": 0.40,
        "blackberry brandy": 0.30,
        "rhum agricole": 0.40,
        "st-germain": 0.20,
        "pelinkovac": 0.35,
        "plum brandy": 0.40,
        "fruit punch": 0.0,
        "zima": 0.0,
        "schweppes russchian": 0.0,
        "kiwi liqueur": 0.20,
        "midori melon liqueur": 0.20,
        "godiva liqueur": 0.20,
        "peachtree schnapps": 0.20,
        "black sambuca": 0.38,
    }
    key = name.strip().lower()
    if key in _ABV_FALLBACK:
        return _ABV_FALLBACK[key]
    # 品牌名前缀剥离兜底："Smirnoff Vodka" → "vodka" → canon+get_abv
    _BRAND_PREFIXES = (
        "smirnoff|bacardi|monin|lagavulin|jack\\s+daniels|jim\\s+beam|"
        "johnnie\\s+walker|absolut|fresh|dry|blended|white\\s+smooth|"
        "pink|amontillado|palo\\s+cortado"
    )
    stripped = re.sub(rf"^(?:{_BRAND_PREFIXES})\s+", "", key, flags=re.IGNORECASE)
    if stripped != key and stripped:
        canonical = canonicalize(stripped)
        abv = get_abv(canonical)
        if abv > 0:
            return abv
        if stripped in _ABV_FALLBACK:
            return _ABV_FALLBACK[stripped]
    # 尾部/首部基酒词兜底："Goslings Rum" → "rum"(0.40)、"Rhum agricole" → "rhum"(0.40)
    _SPIRIT_WORD_ABV = {
        "rum": 0.40, "ron": 0.40, "rhum": 0.40, "whiskey": 0.40, "whisky": 0.40,
        "scotch": 0.40, "gin": 0.40, "vodka": 0.40, "tequila": 0.40,
        "brandy": 0.40, "grappa": 0.40, "cognac": 0.40, "pisco": 0.40,
        "schnapps": 0.20, "liqueur": 0.20, "cordial": 0.15, "sambuca": 0.38,
        "amaretto": 0.24, "frangelico": 0.20, "maraschino": 0.30,
        "sherry": 0.175, "wine": 0.12, "vermouth": 0.16, "beer": 0.05,
        "absinthe": 0.60, "bitters": 0.40, "alcohol": 0.95,
    }
    words = key.split()
    if words:
        last = words[-1].rstrip("s")
        if last in _SPIRIT_WORD_ABV:
            return _SPIRIT_WORD_ABV[last]
        first = words[0].rstrip("s")
        if first in _SPIRIT_WORD_ABV:
            return _SPIRIT_WORD_ABV[first]
    return 0.0


def build_ingredients_json(ingredients: list[dict[str, Any]]) -> str:
    """序列化结构化用料表为 JSON 字符串。

    每项 ``{"name": "...", "measure": "..."}``，measure 为空则省略。
    """
    items = [
        {"name": item.get("name", "")}
        | ({"measure": item["measure"]} if item.get("measure") else {})
        for item in ingredients
        if item.get("name")
    ]
    return json.dumps(items, ensure_ascii=False)


def _parse_abv_section(content: str) -> float | None:
    """从 ``## 酒精度`` 段落解析明确 ABV（0.0-1.0）。

    bar-assistant 快照含显式酒精度（如 ``## 酒精度`` / ``21.33%``），
    权威度高于体积加权估算。解析失败返回 None。
    """
    if not content:
        return None
    for line in content.splitlines():
        s = line.strip()
        if not s.startswith("## 酒精度") and "酒精度" not in s:
            continue
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
        if m:
            try:
                val = float(m.group(1)) / 100.0
            except ValueError:
                return None
            return min(val, 1.0) if 0.0 <= val <= 1.0 else None
    return None


def structured_from_content(content: str) -> dict[str, Any]:
    """一键入口：从配方 content 提取结构化字段。

    Returns:
        ``{"base_spirit": str, "abv": float, "ingredients_json": str}``
        - base_spirit：无法判断时优先基酒类目，仍无则 "other"
        - abv：优先 ``## 酒精度`` 段落（显式），否则体积加权平均，无体积时 0.0
        - ingredients_json：结构化用料表 JSON（可为 "[]"）
    """
    items = parse_recipe_section(content)
    names = [item["name"] for item in items]
    base_spirit = infer_base_spirit(names) or "other"
    explicit = _parse_abv_section(content)
    abv = explicit if explicit is not None else compute_abv(items)
    return {
        "base_spirit": base_spirit,
        "abv": abv,
        "ingredients_json": build_ingredients_json(items),
    }
