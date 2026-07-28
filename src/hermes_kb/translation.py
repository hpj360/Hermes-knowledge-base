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
# 覆盖 IBA 经典、TheCocktailDB 高频配方及种子配方英文标题，共 230+ 条。
# 注意：所有中文值必须唯一（避免一词多译），见 test_no_duplicate_values。
_COMMON_TRANSLATIONS: dict[str, str] = {
    # ============================================================
    # 原有高频经典（50 条）
    # ============================================================
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
    "between the sheets": "床第之间",
    "alice": "爱丽丝",
    # ============================================================
    # 种子配方提取（42 条，源自 seed_recipes.py 中英对照）
    # ============================================================
    "white lady": "白色佳人",
    "alexander": "亚历山大",
    "boulevardier": "林荫道",
    "gin fizz": "金菲士",
    "hanky panky": "汉基帕基",
    "john collins": "约翰柯林斯",
    "martinez": "马天尼内兹",
    "mary pickford": "玛丽碧克馥",
    "planter's punch": "种植者宾治",
    "ramos gin fizz": "拉莫斯菲士",
    "caipirinha": "卡布琳娜",
    "corpse reviver #2": "复尸者2号",
    "cuba libre": "自由古巴",
    "kir": "主教",
    "mint julep": "薄荷茱莉普",
    "singapore sling": "新加坡司令",
    "zombie": "僵尸",
    "barracuda": "梭鱼",
    "dark 'n' stormy": "黑风暴",
    "dirty martini": "脏马天尼",
    "french martini": "法式马天尼",
    "illegal": "非法",
    "tommy's margarita": "汤米的玛格丽特",
    "yellow bird": "黄鸟",
    "missionary's downfall": "传教士的堕落",
    "painkiller": "止痛药",
    "scorpion bowl": "蝎子碗",
    "hot toddy": "热托迪",
    "tom and jerry": "汤姆与杰瑞",
    "port flip": "波特菲利普",
    "brandy alexander": "白兰地亚历山大",
    "fish house punch": "渔会潘趣",
    "rum punch": "朗姆潘趣",
    "virgin mojito": "无酒精莫吉托",
    "shirley temple": "雪莉邓波儿",
    "no-tequila sunrise": "无龙舌兰日出",
    "pousse-café": "彩虹酒",
    "new york sour": "纽约酸",
    "hemingway daiquiri": "海明威代基里",
    "paper plane": "纸飞机",
    "gold rush": "淘金热",
    "naked and famous": "裸体与成名",
    # ============================================================
    # Sour 酸酒与 Daisy 雏菊家族（15 条）
    # ============================================================
    "amaretto sour": "杏仁酸",
    "brandy sour": "白兰地酸",
    "apricot sour": "杏子酸",
    "peach sour": "蜜桃酸",
    "midori sour": "蜜多力酸",
    "brandy crusta": "白兰地壳饰",
    "brandy daisy": "白兰地雏菊",
    "gin daisy": "金雏菊",
    "whiskey daisy": "威士忌雏菊",
    "brandy smash": "白兰地碎冰",
    "whiskey smash": "威士忌碎冰",
    "bourbon smash": "波本碎冰",
    "improved whiskey cocktail": "改良威士忌鸡尾酒",
    "fancy whiskey": "花式威士忌",
    "old pal": "老朋友",
    # ============================================================
    # Highball 高球与 Cooler 酷乐（12 条）
    # ============================================================
    "greyhound": "灰狗",
    "salty dog": "咸狗",
    "sea breeze": "海风",
    "bay breeze": "湾风",
    "cape codder": "鳕鱼角",
    "madras": "马德拉斯",
    "gin rickey": "金瑞奇",
    "vodka rickey": "伏特加瑞奇",
    "whiskey rickey": "威士忌瑞奇",
    "gin and it": "金酒味美思",
    "shandy": "仙迪",
    "radler": "拉德勒",
    # ============================================================
    # Martini 马天尼变体（10 条）
    # ============================================================
    "apple martini": "苹果马天尼",
    "chocolate martini": "巧克力马天尼",
    "pomegranate martini": "石榴马天尼",
    "peach martini": "蜜桃马天尼",
    "pear martini": "梨子马天尼",
    "lemon drop martini": "柠檬滴马天尼",
    "porn star martini": "明星马天尼",
    "saketini": "清酒马天尼",
    "tequini": "龙舌兰马天尼",
    "gin gimlet": "金吉姆雷特",
    # ============================================================
    # Tiki 热带鸡尾酒（12 条）
    # ============================================================
    "bahama mama": "巴哈马妈妈",
    "banana daiquiri": "香蕉代基里",
    "strawberry daiquiri": "草莓代基里",
    "banana split": "香蕉船",
    "mango tango": "芒果探戈",
    "coco loco": "椰子狂热",
    "rum runner": "朗姆逃犯",
    "hurricane": "飓风",
    "fog cutter": "雾刃",
    "navy grog": "海军烈酒",
    "tahitian breeze": "塔希提微风",
    "scorpion": "蝎子",
    # ============================================================
    # Creamy 奶油甜品鸡尾酒（8 条）
    # ============================================================
    "mudslide": "泥石流",
    "colorado bulldog": "科罗拉多斗牛犬",
    "pink squirrel": "粉红松鼠",
    "golden cadillac": "金色凯迪拉克",
    "snow white": "白雪公主",
    "frozen mudslide": "冰泥石流",
    "creamy screwdriver": "奶油螺丝刀",
    "banana cow": "香蕉牛",
    # ============================================================
    # 现代经典与派对饮品（12 条）
    # ============================================================
    "blue lagoon": "蓝色珊瑚礁",
    "blue hawaiian": "蓝色夏威夷",
    "blue margarita": "蓝色玛格丽特",
    "blue monday": "蓝色星期一",
    "electric lemonade": "电柠檬水",
    "purple rain": "紫雨",
    "purple haze": "紫雾",
    "woo woo": "呜呜",
    "sex on the beach": "性感海滩",
    "fuzzy navel": "绒毛肚脐",
    "hairy navel": "毛茸肚脐",
    "kamikaze": "神风特攻",
    # ============================================================
    # 禁酒令前经典（15 条）
    # ============================================================
    "rob roy": "罗伯罗伊",
    "dry rob roy": "干罗伯罗伊",
    "perfect rob roy": "完美罗伯罗伊",
    "godmother": "教母",
    "silver bullet": "银弹",
    "millionaire": "百万富翁",
    "casino": "赌场",
    "saratoga": "萨拉托加",
    "polo": "马球",
    "jazz": "爵士",
    "bijou": "珠宝",
    "alaska": "阿拉斯加",
    "monkey gland": "猴腺",
    "satan's whiskers": "撒旦胡须",
    "fallen angel": "堕落天使",
    # ============================================================
    # 国际与地区经典（12 条）
    # ============================================================
    "caipiroska": "卡皮罗斯卡",
    "caipirissima": "卡皮里斯玛",
    "batida": "巴蒂达",
    "batida de coco": "椰子巴蒂达",
    "pisco punch": "皮斯科潘趣",
    "el presidente": "总统",
    "cuban special": "古巴特别",
    "english rose": "英伦玫瑰",
    "harvard": "哈佛",
    "oxford": "牛津",
    "cambridge": "剑桥",
    "metropolitan": "都市",
    # ============================================================
    # Shooter 子弹与派对烈饮（10 条）
    # ============================================================
    "baby guinness": "小健力士",
    "slippery nipple": "滑乳头",
    "irish car bomb": "爱尔兰汽车炸弹",
    "jagerbomb": "野格炸弹",
    "lemon drop": "柠檬滴",
    "melon ball": "瓜球",
    "mind eraser": "记忆消除者",
    "boilermaker": "锅炉工",
    "depth charge": "深水炸弹",
    "saké bomb": "清酒炸弹",
    # ============================================================
    # Hot Drink 热饮（5 条）
    # ============================================================
    "mulled wine": "热红酒",
    "glogg": "格洛格",
    "bishop": "主教香料酒",
    "hot buttered rum": "热黄油朗姆",
    "michelada": "米切拉达",
    # ============================================================
    # Punch 潘趣与蛋酒（4 条）
    # ============================================================
    "boston punch": "波士顿潘趣",
    "champagne punch": "香槟潘趣",
    "fruit punch": "水果潘趣",
    "egg nog": "蛋酒",
    # ============================================================
    # 其他经典与变体（20 条）
    # ============================================================
    "angel's kiss": "天使之吻",
    "bloody maria": "血腥玛丽亚",
    "bloody caesar": "血腥凯撒",
    "matador": "斗牛士",
    "tequila slammer": "龙舌兰炮弹",
    "vodka sunrise": "伏特加日出",
    "sangria": "桑格利亚",
    "shrub": "果醋",
    "red eye": "红眼",
    "prairie oyster": "草原牡蛎",
    "death in the afternoon": "午后之死",
    "hemingway special": "海明威特调",
    "red lion": "红狮",
    "red snapper": "红鲷鱼",
    "pink lady": "粉红佳人",
    "pink rose": "粉红玫瑰",
    "old cuban": "老古巴",
    "tipperary": "蒂珀雷里",
    "remember the maine": "记住缅因号",
    "hoffman house": "霍夫曼屋",
    # ============================================================
    # Negroni / Sazerac 变体与现代禁酒令风格（10 条）
    # ============================================================
    "white negroni": "白尼格罗尼",
    "negroni sbagliato": "错版尼格罗尼",
    "mezcal negroni": "梅斯卡尔尼格罗尼",
    "mezcal old fashioned": "梅斯卡尔古典",
    "rye sazerac": "黑麦赛泽瑞克",
    "brown derby": "棕色德比",
    "derby": "德比",
    "queens park": "皇后公园",
    "queen charlotte": "夏洛特皇后",
    "ace": "王牌",
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
    except (KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
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
            except (KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
                _logger.warning("Translate failed for doc %s: %s", doc.doc_id, e)
                failed += 1

        session.commit()

    return {
        "translated": translated,
        "skipped": skipped,
        "failed": failed,
        "model_used": model_used,
    }
