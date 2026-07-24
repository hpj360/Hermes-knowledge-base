"""配方标题 LLM 翻译服务（P1）。

将英文配方标题（IBA / TheCocktailDB）批量翻译为中文。
Mock 后端时回退到简单字典匹配，保证无 LLM Key 时也能用。
"""
from __future__ import annotations

import logging
import re
from typing import Any

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document

_logger = logging.getLogger(__name__)

# 常见鸡尾酒英文名 → 中文映射（Mock 后端回退用）
_COMMON_TRANSLATIONS: dict[str, str] = {
    "mojito": "莫吉托",
    "margarita": "玛格丽特",
    "martini": "马天尼",
    "old fashioned": "古典鸡尾酒",
    "negroni": "尼格罗尼",
    "daiquiri": "代基里",
    "manhattan": "曼哈顿",
    "whiskey sour": "威士忌酸",
    "pina colada": "椰林飘香",
    "cosmopolitan": "大都会",
    "espresso martini": "浓缩咖啡马天尼",
    "long island iced tea": "长岛冰茶",
    "moscow mule": "莫斯科骡子",
    "bloody mary": "血腥玛丽",
    "gin and tonic": "金汤力",
    "tequila sunrise": "龙舌兰日出",
    "mai tai": "迈泰",
    "pisco sour": "皮斯科酸",
    "sidecar": "侧车",
    "french 75": "法兰西75",
    "tom collins": "汤姆柯林斯",
    "white russian": "白俄罗斯",
    "black russian": "黑俄罗斯",
    "irish coffee": "爱尔兰咖啡",
    "vodka martini": "伏特加马天尼",
    "dry martini": "干马天尼",
    "screwdriver": "螺丝刀",
    "harvey wallbanger": "哈维撞墙",
    "bramble": "荆棘",
    "corpse reviver": "尸体复活",
    "last word": "遗言",
    "aviation": "飞行",
    "clover club": "三叶草俱乐部",
    "bees knees": "蜂之膝",
    "gimlet": "吉姆雷特",
    "vesper": "维斯帕",
    "sazerac": "赛泽瑞克",
    "penicillin": "盘尼西林",
    "paloma": "帕洛玛",
    "aperol spritz": "阿佩罗喷雾",
    "americano": "美式鸡尾酒",
    "bellini": "贝利尼",
    "mimosa": "含羞草",
    "grasshopper": "蚱蜢",
    "stinger": "螫针",
    "rusty nail": "生锈钉",
    "godfather": "教父",
    "golden dream": "金色梦想",
    "stinger ": "螫针",
    "between the sheets": "床第之间",
    "alice": "爱丽丝",
}


def _mock_translate(title: str) -> str:
    """Mock 翻译：查常用词典，未命中则保留原标题。"""
    lower = title.strip().lower()
    if lower in _COMMON_TRANSLATIONS:
        return _COMMON_TRANSLATIONS[lower]
    # 尝试模糊匹配
    for en, zh in _COMMON_TRANSLATIONS.items():
        if en in lower:
            return zh
    return title


def translate_title(title: str, llm_client: Any = None) -> str:
    """翻译单个配方标题。

    Args:
        title: 英文配方标题
        llm_client: 可选的 LLMClient 实例（None 时新建）

    Returns:
        中文标题（LLM 不可用时回退到 Mock 字典翻译）
    """
    if not title or not title.strip():
        return title

    # 检测是否已是中文（含 CJK 字符则跳过）
    if re.search(r"[\u4e00-\u9fff]", title):
        return title

    try:
        if llm_client is None:
            from hermes_kb.llm import LLMClient
            llm_client = LLMClient()

        # Mock 后端用字典翻译
        if llm_client.backend_name == "MockLLMBackend":
            return _mock_translate(title)

        messages = [
            {
                "role": "system",
                "content": "你是鸡尾酒翻译专家。将英文鸡尾酒名翻译为简洁的中文译名。只输出译名，不加解释、不加引号。",
            },
            {"role": "user", "content": f"翻译: {title}"},
        ]
        resp = llm_client.chat(messages)
        translated = resp.content.strip()
        # 去除可能的多余引号
        translated = translated.strip('"\'""''')
        return translated if translated else title
    except Exception as e:
        _logger.warning("LLM translate failed for '%s': %s, fallback to mock", title, e)
        return _mock_translate(title)


def batch_translate_titles(
    doc_ids: list[str] | None = None,
    source: str | None = None,
    limit: int = 100,
    llm_client: Any = None,
) -> dict[str, Any]:
    """批量翻译配方标题并更新数据库。

    Args:
        doc_ids: 指定 doc_id 列表（None 时按 source 筛选）
        source: 数据源筛选（如 'iba', 'thecocktaildb'）
        limit: 最多翻译条数
        llm_client: 可选的 LLMClient 实例

    Returns:
        {translated, skipped, failed, model_used}
    """
    translated = 0
    skipped = 0
    failed = 0

    if llm_client is None:
        from hermes_kb.llm import LLMClient
        llm_client = LLMClient()

    model_used = llm_client.backend_name

    with get_session() as session:
        stmt = select(Document).where(Document.category == "recipe")
        if doc_ids:
            stmt = stmt.where(Document.doc_id.in_(doc_ids))
        if source:
            stmt = stmt.where(Document.source == source)
        stmt = stmt.limit(limit)
        docs = session.exec(stmt).all()

        for doc in docs:
            try:
                # 已含中文的跳过
                if re.search(r"[\u4e00-\u9fff]", doc.title):
                    skipped += 1
                    continue

                new_title = translate_title(doc.title, llm_client)
                if new_title and new_title != doc.title:
                    doc.title = new_title
                    session.add(doc)
                    translated += 1
                else:
                    skipped += 1
            except Exception as e:
                _logger.warning("Translate failed for doc %s: %s", doc.doc_id, e)
                failed += 1

        session.commit()

    return {
        "translated": translated,
        "skipped": skipped,
        "failed": failed,
        "model_used": model_used,
    }
