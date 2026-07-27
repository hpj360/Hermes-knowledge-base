"""配方元数据推断工具。

基于 content/ingredients/title 的关键词匹配，推断 technique/glassware/iba_category。
用于外部数据源（TheCocktailDB / IBA dataset）导入时回填结构化元数据。
"""
from __future__ import annotations

from hermes_kb.ingredients import canonicalize, get_tags


def infer_technique(content: str, ingredients: list[str] | None = None) -> str:
    """推断调酒技法。

    规则（按优先级）：
    - content 含 "摇酒壶"/"摇匀"/"shake" → "shake"
    - content 含 "搅拌"/"stir" → "stir"
    - content 含 "直接倒入"/"build"/"兑和" → "build"
    - content 含 "分层"/"layer" → "layer"
    - content 含 "捣压"/"捣碎"/"muddle" → "muddle"
    - content 含 "搅拌机"/"blend" → "blend"
    - 无法推断返回 ""

    关键词匹配大小写不敏感（content 可能是英文）。
    多个关键词命中时，按上述优先级返回第一个。
    注意：stir 关键词 "搅拌" 是 blend 关键词 "搅拌机" 的子串，
    故 stir 检查排除 "搅拌机" 命中的情况，保证 "搅拌机" → blend。

    Args:
        content: 配方步骤/正文文本。
        ingredients: 材料列表（预留参数，当前不参与技法推断）。

    Returns:
        技法标识符（shake/stir/build/layer/muddle/blend），无法推断返回 ""。
    """
    if not content:
        return ""
    cl = content.lower()
    if "摇酒壶" in content or "摇匀" in content or "shake" in cl:
        return "shake"
    # "搅拌机" 是 blend 关键词，需先排除以避免被 stir 的 "搅拌" 子串误匹配
    if ("搅拌" in content and "搅拌机" not in content) or "stir" in cl:
        return "stir"
    if "直接倒入" in content or "build" in cl or "兑和" in content:
        return "build"
    if "分层" in content or "layer" in cl:
        return "layer"
    if "捣压" in content or "捣碎" in content or "muddle" in cl:
        return "muddle"
    if "搅拌机" in content or "blend" in cl:
        return "blend"
    return ""


def infer_glassware(content: str, title: str = "") -> str:
    """推断载杯类型。

    规则（按优先级，大小写不敏感）：
    - content 含 "马天尼杯"/"martini glass" → "马天尼杯"
    - content 含 "古典杯"/"rocks glass"/"old fashioned" → "古典杯"
    - content 含 "高球杯"/"highball" → "高球杯"
    - content 含 "柯林斯杯"/"collins" → "柯林斯杯"
    - content 含 "香槟杯"/"champagne flute" → "香槟杯"
    - content 含 "飓风杯"/"hurricane" → "飓风杯"
    - content 含 "玛格丽特杯"/"margarita" → "玛格丽特杯"
    - content 含 "白兰地杯"/"snifter" → "白兰地杯"
    - content 含 "Coupe 杯"/"coupe" → "Coupe 杯"
    - 无法推断返回 ""

    Args:
        content: 配方步骤/正文文本。
        title: 配方标题（预留参数，当前不参与载杯推断）。

    Returns:
        载杯中文名，无法推断返回 ""。
    """
    if not content:
        return ""
    cl = content.lower()
    if "马天尼杯" in content or "martini glass" in cl:
        return "马天尼杯"
    if "古典杯" in content or "rocks glass" in cl or "old fashioned" in cl:
        return "古典杯"
    if "高球杯" in content or "highball" in cl:
        return "高球杯"
    if "柯林斯杯" in content or "collins" in cl:
        return "柯林斯杯"
    if "香槟杯" in content or "champagne flute" in cl:
        return "香槟杯"
    if "飓风杯" in content or "hurricane" in cl:
        return "飓风杯"
    if "玛格丽特杯" in content or "margarita" in cl:
        return "玛格丽特杯"
    if "白兰地杯" in content or "snifter" in cl:
        return "白兰地杯"
    if "coupe" in cl:
        return "Coupe 杯"
    return ""


def infer_iba_category(iba_type: str) -> str:
    """将 IBA dataset 的 type 字段映射为标准 iba_category。

    规则：
    - "The Unforgettables" → "unforgettables"
    - "Contemporary Classics" → "contemporary_classics"
    - "New Era Drinks" → "new_era_drinks"
    - 其他/空 → ""

    Args:
        iba_type: IBA dataset 的 type 字段值。

    Returns:
        标准 iba_category 标识符，无法映射返回 ""。
    """
    if not iba_type:
        return ""
    mapping = {
        "The Unforgettables": "unforgettables",
        "Contemporary Classics": "contemporary_classics",
        "New Era Drinks": "new_era_drinks",
    }
    return mapping.get(iba_type, "")


def infer_flavor_profile(ingredients: list[str]) -> str:
    """基于材料列表聚合风味标签。

    流程：
    1. 对每个材料名，用 ingredients.canonicalize 归一化
    2. 查 INGREDIENT_REGISTRY 的 tags
    3. 收集所有 tags，去重，分号拼接
    4. 空列表返回 ""

    Args:
        ingredients: 材料名列表（可为中文标准名或英文别名）。

    Returns:
        分号拼接的去重风味标签字符串，无标签返回 ""。
    """
    if not ingredients:
        return ""
    # dict 保持插入顺序并去重
    seen: dict[str, None] = {}
    for ing in ingredients:
        canonical = canonicalize(ing)
        for tag in get_tags(canonical):
            seen[tag] = None
    return ";".join(seen)
