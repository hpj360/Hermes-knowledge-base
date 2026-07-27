"""三层替代关系表（L1 预置 + L2 用户自定义 + L3 预留）。

- L1: 预置 IBA 替代关系（本文件常量）
- L2: 用户自定义（持久化到 SQLite ingredient_substitutes 表）
- L3: 外部同步（M4 远期，接口预留）
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import IngredientSubstitute

# L1: 预置替代关系（扩充版，B4：基于 bar-assistant 开源数据集）
SUBSTITUTES_PRESET: dict[str, list[str]] = {
    # === 基酒互替 ===
    "金酒": ["伏特加", "杜松子酒"],
    "伏特加": ["金酒"],
    "威士忌": ["波本", "黑麦威士忌", "苏格兰威士忌"],
    "朗姆酒": ["黑朗姆酒", "白朗姆酒", "陈年朗姆酒"],
    "龙舌兰": ["梅斯卡尔"],
    # === 辅料 ===
    "味美思": ["干味美思", "甜味美思"],
    "君度": ["干库拉索", "橙味力娇酒", "Triple Sec"],
    "金巴利": ["Aperol", "Campari"],
    "苦精": ["橙味苦精", "安高天娜苦精"],
    "糖浆": ["蜂蜜糖浆", "白糖水", "龙舌兰糖浆"],
    "蜂蜜糖浆": ["糖浆", "蜂蜜"],
    "汤力水": ["苏打水", "气泡水", "奎宁水"],
    "苏打水": ["汤力水", "气泡水"],
    "干库拉索": ["君度", "橙味力娇酒"],
    "橙味力娇酒": ["君度", "干库拉索"],
    "咖啡利口酒": ["甘露咖啡利口酒", "Kahlua"],
    "甘露咖啡利口酒": ["咖啡力娇酒", "Kahlua"],
    "椰子利口酒": ["马利宝"],
    "杏仁糖浆": ["Orgeat", "杏仁糖浆"],
    "黑莓利口酒": ["Creme de Mure"],
    "薄荷利口酒": ["绿薄荷利口酒", "Creme de Menthe"],
    # === 果汁 ===
    "青柠汁": ["柠檬汁"],
    "柠檬汁": ["青柠汁"],
    "橙汁": ["血橙汁", "橘子汁"],
    "蔓越莓汁": ["红莓汁"],
    "菠萝汁": ["芒果汁"],
    "番茄汁": ["蔬菜汁"],
    # === 装饰 ===
    "樱桃": ["酒渍樱桃", "蜜饯樱桃"],
    "橄榄": ["珍珠洋葱"],
    "薄荷叶": ["薄荷枝"],
    "柠檬片": ["青柠片", "橙片"],
    "青柠片": ["柠檬片"],
    "橙皮": ["柠檬皮", "西柚皮"],
    "柠檬皮": ["橙皮"],
    # === 其他 ===
    "蛋白": ["鹰嘴豆水"],
    "姜汁啤酒": ["姜汁汽水", "姜茶"],
    "姜汁汽水": ["姜汁啤酒"],
    "红葡萄酒": ["白葡萄酒"],
    "白葡萄酒": ["红葡萄酒"],
    "香槟": ["起泡酒", "Prosecco"],
    "起泡酒": ["香槟", "Prosecco"],
    "咖啡": ["浓缩咖啡"],
    "牛奶": ["燕麦奶", "杏仁奶"],
    # === 1. 朗姆酒细分互替 ===
    "白朗姆酒": ["金朗姆酒", "黑朗姆酒", "陈年朗姆酒", "朗姆酒"],
    "金朗姆酒": ["白朗姆酒", "黑朗姆酒", "陈年朗姆酒"],
    "黑朗姆酒": ["金朗姆酒", "白朗姆酒", "陈年朗姆酒"],
    "陈年朗姆酒": ["金朗姆酒", "黑朗姆酒", "白朗姆酒"],
    "151朗姆酒": ["金朗姆酒", "黑朗姆酒"],
    "黑朗姆": ["黑朗姆酒", "金朗姆酒"],
    # === 2. 威士忌细分互替 ===
    "波本威士忌": ["黑麦威士忌", "田纳西威士忌", "威士忌"],
    "黑麦威士忌": ["波本威士忌", "威士忌"],
    "苏格兰威士忌": ["日本威士忌", "威士忌"],
    "日本威士忌": ["苏格兰威士忌", "威士忌"],
    "田纳西威士忌": ["波本威士忌", "威士忌"],
    "爱尔兰威士忌": ["威士忌", "苏格兰威士忌"],
    # === 3. 龙舌兰细分互替 ===
    "银龙舌兰": ["金龙舌兰", "龙舌兰"],
    "金龙舌兰": ["银龙舌兰", "陈年龙舌兰", "龙舌兰"],
    "陈年龙舌兰": ["金龙舌兰", "龙舌兰"],
    "梅斯卡尔": ["龙舌兰"],
    # === 4. 味美思细分互替 ===
    "干味美思": ["甜味美思", "白味美思", "味美思"],
    "甜味美思": ["干味美思", "红味美思", "味美思"],
    "白味美思": ["干味美思", "甜味美思"],
    "红味美思": ["甜味美思", "干味美思"],
    # === 5. 苦精细分互替 ===
    "安高天娜苦精": ["佩肖德苦精", "橙味苦精", "苦精"],
    "佩肖德苦精": ["安高天娜苦精", "苦精"],
    "橙味苦精": ["安高天娜苦精", "苦精"],
    # === 6. 利口酒细分互替 ===
    "覆盆子利口酒": ["黑加仑利口酒", "Chambord"],
    "黑加仑利口酒": ["覆盆子利口酒", "Creme de Cassis"],
    "黑樱桃力娇酒": ["黑樱桃利口酒", "Maraschino"],
    "查特酒": ["黄查特酒", "绿查特酒"],
    "黄查特酒": ["绿查特酒", "查特酒"],
    "绿查特酒": ["黄查特酒", "查特酒"],
    # === 7. 白兰地与葡萄酒细分 ===
    "干邑": ["雅文邑", "白兰地"],
    "雅文邑": ["干邑", "白兰地"],
    "白兰地": ["干邑", "雅文邑"],
    "波特酒": ["红葡萄酒", "马德拉酒"],
    "雪莉酒": ["白葡萄酒", "味美思"],
    # === 8. 果汁细分互替 ===
    "西柚汁": ["葡萄柚汁", "血橙汁"],
    "葡萄柚汁": ["西柚汁"],
    "血橙汁": ["橙汁", "西柚汁"],
    "芒果汁": ["菠萝汁", "百香果汁"],
    "百香果汁": ["芒果汁", "菠萝汁"],
    # === 9. 糖浆细分互替 ===
    "红石榴糖浆": ["覆盆子糖浆", "蔓越莓汁"],
    "覆盆子糖浆": ["红石榴糖浆"],
    "肉桂糖浆": ["糖浆", "蜂蜜糖浆"],
    "姜糖浆": ["糖浆", "蜂蜜糖浆"],
    "龙舌兰糖浆": ["蜂蜜糖浆", "糖浆"],
    # === 10. 装饰细分互替 ===
    "肉豆蔻": ["肉桂粉", "豆蔻粉"],
    "肉桂粉": ["肉豆蔻"],
    "肉桂棒": ["肉桂粉"],
    "迷迭香": ["百里香"],
    "百里香": ["迷迭香"],
    # === 11. 无酒精替代 ===
    "无酒精金酒": ["Seedlip", "苏打水"],
    "Seedlip": ["无酒精金酒"],
    "无酒精朗姆": ["朗姆酒", "风味糖浆"],
    "无酒精伏特加": ["伏特加", "苏打水"],
    "无酒精威士忌": ["威士忌", "红茶"],
    "无酒精龙舌兰": ["龙舌兰", "苏打水"],
    # === 12. 其他常见替代补全 ===
    "蛋清": ["鹰嘴豆水", "蛋清粉"],
    "蛋黄": ["全蛋"],
    "全蛋": ["蛋黄", "蛋清"],
    "奶油": ["椰奶", "淡奶", "炼乳"],
    "炼乳": ["奶油", "淡奶"],
    "淡奶": ["奶油", "炼乳"],
    "椰奶": ["奶油", "椰浆"],
    "椰浆": ["椰奶", "奶油"],
    "黑刺李金酒": ["金酒", "黑刺李利口酒"],
    "黑刺李利口酒": ["黑刺李金酒"],
    # === 13. 水果与装饰细分 ===
    "酒渍樱桃": ["蜜饯樱桃", "樱桃"],
    "蜜饯樱桃": ["酒渍樱桃", "樱桃"],
    "珍珠洋葱": ["橄榄", "鸡尾酒洋葱"],
    "鸡尾酒洋葱": ["珍珠洋葱"],
    "橙片": ["柠檬片", "西柚片"],
    "西柚片": ["橙片", "柠檬片"],
    "薄荷枝": ["薄荷叶"],
    # === 14. 汽水与碳酸饮料细分 ===
    "奎宁水": ["汤力水"],
    "气泡水": ["苏打水", "汤力水"],
    "姜茶": ["姜汁啤酒", "蜂蜜"],
    # === 15. 咖啡与茶饮 ===
    "浓缩咖啡": ["冷萃咖啡", "速溶咖啡"],
    "冷萃咖啡": ["浓缩咖啡"],
    "速溶咖啡": ["浓缩咖啡"],
    "红茶": ["绿茶", "乌龙茶"],
    "绿茶": ["红茶"],
    # === 16. 烈酒细分补全 ===
    "加拿大威士忌": ["黑麦威士忌", "威士忌"],
    "调和威士忌": ["苏格兰威士忌", "波本威士忌"],
    "单麦威士忌": ["苏格兰威士忌", "日本威士忌"],
    "杜松子酒": ["金酒"],
    "老汤姆金酒": ["金酒", "杜松子酒"],
    "Plymouth 金酒": ["金酒"],
    "海军强度金酒": ["金酒"],
    # === 17. 利口酒补全 ===
    "马利宝": ["椰子利口酒", "椰子朗姆酒"],
    "椰子朗姆酒": ["马利宝", "椰子利口酒"],
    "Kahlua": ["甘露咖啡利口酒", "咖啡力娇酒"],
    "Triple Sec": ["君度", "干库拉索"],
    "Aperol": ["金巴利", "Campari"],
    "Campari": ["金巴利", "Aperol"],
    "意大利开胃酒": ["Aperol", "Campari"],
    "法国开胃酒": ["Lillet Blanc", "Lillet"],
    # === 18. 调味料与糖浆补全 ===
    "白糖水": ["糖浆", "蜂蜜糖浆"],
    "红糖水": ["糖浆", "蜂蜜糖浆"],
    "枫糖浆": ["蜂蜜糖浆", "糖浆"],
    "玉米糖浆": ["糖浆"],
    "香草糖浆": ["糖浆", "蜂蜜糖浆"],
    # === 19. 奶制品补全 ===
    "燕麦奶": ["杏仁奶", "牛奶"],
    "杏仁奶": ["燕麦奶", "牛奶"],
    "豆奶": ["燕麦奶", "牛奶"],
    # === 20. 互补条目补全（反向引用） ===
    "Prosecco": ["香槟", "起泡酒"],
    "蜂蜜": ["蜂蜜糖浆", "糖浆"],
    "绿薄荷利口酒": ["薄荷利口酒", "Creme de Menthe"],
    "Creme de Menthe": ["薄荷利口酒", "绿薄荷利口酒"],
}


def get_substitutes_preset(canonical: str) -> list[str]:
    """查询 L1 预置替代关系。"""
    return SUBSTITUTES_PRESET.get(canonical, [])


def get_substitutes(canonical: str) -> list[str]:
    """合并查询 L1 + L2 替代关系。"""
    result = list(get_substitutes_preset(canonical))
    with get_session() as session:
        rows = session.exec(
            select(IngredientSubstitute).where(
                IngredientSubstitute.canonical == canonical
            )
        ).all()
        for row in rows:
            if row.substitute not in result:
                result.append(row.substitute)
    return result


def add_user_substitute(canonical: str, substitute: str) -> None:
    """添加 L2 用户自定义替代关系。

    P1-5: DB 层 UniqueConstraint(canonical, substitute) 兜底，
    select-then-insert 的 TOCTOU race 由 IntegrityError 兜住。
    """
    canonical = canonical.strip()
    substitute = substitute.strip()
    if not canonical or not substitute:
        return
    with get_session() as session:
        existing = session.exec(
            select(IngredientSubstitute).where(
                IngredientSubstitute.canonical == canonical,
                IngredientSubstitute.substitute == substitute,
            )
        ).first()
        if existing:
            return
        session.add(
            IngredientSubstitute(
                canonical=canonical, substitute=substitute, source="user"
            )
        )
        try:
            session.commit()
        except IntegrityError:
            # 并发写入时唯一约束兜底：重复记录视为已存在
            session.rollback()


def remove_user_substitute(canonical: str, substitute: str) -> None:
    """删除 L2 用户自定义替代（仅删 source='user'）。"""
    with get_session() as session:
        rows = session.exec(
            select(IngredientSubstitute).where(
                IngredientSubstitute.canonical == canonical,
                IngredientSubstitute.substitute == substitute,
                IngredientSubstitute.source == "user",
            )
        ).all()
        for row in rows:
            session.delete(row)
        session.commit()


def list_all_substitutes() -> dict[str, list[str]]:
    """列出所有材料的替代关系（L1+L2 合并）。用于运营看板覆盖率统计。"""
    all_subs: dict[str, set[str]] = {}
    for canon, subs in SUBSTITUTES_PRESET.items():
        all_subs.setdefault(canon, set()).update(subs)
    with get_session() as session:
        rows = session.exec(select(IngredientSubstitute)).all()
        for row in rows:
            all_subs.setdefault(row.canonical, set()).add(row.substitute)
    return {k: sorted(v) for k, v in all_subs.items()}
