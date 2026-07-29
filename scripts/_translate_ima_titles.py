"""将 102 条 IMA 英文 slug 标题翻译为中文，同时清理 __OLD 重复条目。"""
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, "src")

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document

# ===== 翻译映射 =====
_TITLE_MAP = {
    # 葡萄酒类型
    "wine_wine_red": "红葡萄酒",
    "wine_wine_orange": "橙葡萄酒",
    "wine_wine_white": "白葡萄酒",
    "wine_wine_rose": "桃红葡萄酒",
    "wine_wine_dessert": "甜型葡萄酒",
    "wine_wine_sparkling_blend": "起泡葡萄酒混酿",
    # 葡萄品种
    "wine_grape_marselan": "马瑟兰葡萄",
    "wine_grape_gamay": "佳美葡萄",
    "wine_grape_riesling": "雷司令葡萄",
    "wine_grape_merlot": "梅洛葡萄",
    "wine_grape_tannat": "塔娜葡萄",
    "wine_grape_syrah": "西拉葡萄",
    "wine_grape_grenache": "歌海娜葡萄",
    "wine_grape_nebbiolo": "内比奥罗葡萄",
    "wine_grape_viognier": "维欧尼葡萄",
    "wine_grape_moscato": "莫斯卡托葡萄",
    "wine_grape_chardonnay": "霞多丽葡萄",
    "wine_grape_vermentino": "维蒙蒂诺葡萄",
    "wine_grape_barbera": "巴贝拉葡萄",
    "wine_grape_semillon": "赛美蓉葡萄",
    "wine_grape_malbec": "马尔贝克葡萄",
    "wine_grape_chenin_blanc": "白诗南葡萄",
    "wine_grape_sangiovese": "桑娇维塞葡萄",
    "wine_grape_gewurztraminer": "琼瑶浆葡萄",
    "wine_grape_zinfandel": "金粉黛葡萄",
    "wine_grape_carmenere": "佳美娜葡萄",
    "wine_grape_cabernet_gernischt": "蛇龙珠葡萄",
    "wine_grape_pinot_noir": "黑皮诺葡萄",
    "wine_grape_mourvedre": "慕合怀特葡萄",
    "wine_grape_carignan": "佳丽酿葡萄",
    "wine_grape_pinot_grigio": "灰皮诺葡萄",
    "wine_grape_dolcetto": "多姿桃葡萄",
    "wine_grape_tempranillo": "丹魄葡萄",
    "wine_grape_albarino": "阿尔巴利诺葡萄",
    "wine_grape_torrontes": "特浓情葡萄",
    "wine_grape_albariño": "阿尔巴利诺葡萄",
    "wine_grape_petit_verdot": "小维多葡萄",
    "wine_grape_gruner_veltliner": "绿维特利纳葡萄",
    "wine_grape_cabernet_sauvignon": "赤霞珠葡萄",
    "wine_grape_sauvignon_blanc": "长相思葡萄",
    # 产区
    "wine_region_veneto": "威尼托产区",
    "wine_region_douro": "杜罗产区",
    "wine_region_alsace": "阿尔萨斯产区",
    "wine_region_sicily": "西西里产区",
    "wine_region_mendoza": "门多萨产区",
    "wine_region_ningxia": "宁夏产区",
    "wine_region_napa": "纳帕产区",
    "wine_region_barossa": "巴罗萨产区",
    "wine_region_alentejo": "阿连特茹产区",
    "wine_region_rhone": "罗讷河谷产区",
    "wine_region_tuscany": "托斯卡纳产区",
    "wine_region_rioja": "里奥哈产区",
    "wine_region_mosel": "摩泽尔产区",
    "wine_region_burgundy": "勃艮第产区",
    "wine_region_washington": "华盛顿产区",
    "wine_region_marlborough": "马尔堡产区",
    "wine_region_bordeaux": "波尔多产区",
    "wine_region_sonoma": "索诺玛产区",
    "wine_region_loire": "卢瓦尔河谷产区",
    "wine_region_tokaj": "托卡伊产区",
    "wine_region_champagne": "香槟产区",
    "wine_region_piedmont": "皮埃蒙特产区",
    "wine_region_priorat": "普里奥拉托产区",
    "wine_region_hunter_valley": "猎人谷产区",
    "wine_region_stellenbosch": "斯泰伦博斯产区",
    "wine_region_central_coast": "中央海岸产区",
    # 果酒/ cider
    "cider_fruit_wine_fruit_wine_plum": "李子果酒",
    "cider_fruit_wine_yangmei": "杨梅果酒",
    "cider_fruit_wine_sangzhi": "桑葚果酒",
    "cider_fruit_wine_mead": "蜂蜜酒",
    "cider_fruit_wine_pear": "梨子果酒",
    "cider_fruit_wine_lychee": "荔枝果酒",
    "cider_fruit_wine_guihua": "桂花酒",
    "cider_fruit_wine_cherry": "樱桃果酒",
    "cider_fruit_wine_berry": "莓果果酒",
    "cider_fruit_wine_hawthorn": "山楂果酒",
    "cider_fruit_wine_kumquat": "金桔果酒",
    "cider_fruit_wine_peach": "桃子果酒",
    "cider_fruit_wine_cider_apple": "苹果 cider",
    # 工艺
    "process_wine": "葡萄酒酿造工艺",
    # 网页标题（保留原文但清理）
    "Wine Folly | Learn about Wine-Wine Folly": "Wine Folly 葡萄酒学习指南",
    "Wine Reviews & News, Learn About Wine": "葡萄酒评论与资讯",
}

# __OLD 后缀的条目是重复旧版本，需要清理
_OLD_SUFFIX = "__OLD"


def main():
    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.source == "ima")
        ).all()
        print(f"IMA 文档数: {len(docs)}")

        translated = 0
        deleted = 0
        kept = 0

        for doc in docs:
            title = doc.title or ""
            # 清理 __OLD 重复条目
            if _OLD_SUFFIX in title:
                # 检查是否有非 OLD 版本存在
                base_title = title.replace(_OLD_SUFFIX, "")
                has_non_old = any(
                    d.title == base_title or d.title == _TITLE_MAP.get(base_title, "")
                    for d in docs
                    if d.doc_id != doc.doc_id
                )
                if has_non_old:
                    # 删除重复的 OLD 条目
                    session.delete(doc)
                    deleted += 1
                    continue

            # 翻译标题
            if title in _TITLE_MAP:
                doc.title = _TITLE_MAP[title]
                session.add(doc)
                translated += 1
            else:
                kept += 1

        session.commit()

    print("\n=== 结果 ===")
    print(f"  翻译: {translated}")
    print(f"  删除(__OLD重复): {deleted}")
    print(f"  保留原文: {kept}")


if __name__ == "__main__":
    main()
