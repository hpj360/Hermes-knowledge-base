#!/usr/bin/env python3
"""扩展 eval_set.jsonl：追加 21 条百科维度查询（q181-q201）。

覆盖 7 个新维度：
- 法规分级（5 条）：AOC/DOCG/德国/新世界/1855 波尔多
- 品鉴方法（4 条）：观色闻香/品味回味/品鉴术语/盲品训练
- 配餐指南（4 条）：总则/红肉/海鲜/甜点奶酪
- 季节性（3 条）：春季/夏季/冬季
- 酒具档案（3 条）：摇酒壶/滤冰器/量酒器
- 调酒师认证（2 条）：认证体系/职业发展

幂等：检测 id 是否已存在，已存在则跳过。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

EVAL = Path(__file__).resolve().parent.parent / "tests" / "eval" / "eval_set.jsonl"

NEW_ENTRIES = [
    # === 法规分级（5 条）===
    {
        "id": "q181",
        "query": "AOC 是什么意思 法国葡萄酒分级",
        "expected_doc_title": "法国 AOC 葡萄酒分级体系百科",
        "expected_keywords": ["AOC", "原产地命名控制", "AOP", "VdP", "VdF"],
        "category": "法规分级",
    },
    {
        "id": "q182",
        "query": "DOCG 分级是什么 意大利葡萄酒等级",
        "expected_doc_title": "意大利 DOCG 葡萄酒分级体系百科",
        "expected_keywords": ["DOCG", "DOC", "IGT", "VdT", "意大利"],
        "category": "法规分级",
    },
    {
        "id": "q183",
        "query": "德国葡萄酒分级 Prädikatswein 是什么",
        "expected_doc_title": "德国 Prädikatswein 葡萄酒分级百科",
        "expected_keywords": ["Prädikatswein", "Kabinett", "Spätlese", "Auslese", "Eiswein"],
        "category": "法规分级",
    },
    {
        "id": "q184",
        "query": "美国 AVA 澳大利亚 GI 新世界葡萄酒分级",
        "expected_doc_title": "新世界葡萄酒分级体系百科",
        "expected_keywords": ["AVA", "GI", "新世界", "美国", "澳大利亚"],
        "category": "法规分级",
    },
    {
        "id": "q185",
        "query": "1855 波尔多分级 列级庄体系",
        "expected_doc_title": "1855 波尔多分级与列级庄百科",
        "expected_keywords": ["1855", "波尔多", "梅多克", "一级庄", "列级庄"],
        "category": "法规分级",
    },
    # === 品鉴方法（4 条）===
    {
        "id": "q186",
        "query": "葡萄酒观色闻香品鉴技巧",
        "expected_doc_title": "观色与闻香品鉴方法百科",
        "expected_keywords": ["观色", "闻香", "挂杯", "香气", "颜色"],
        "category": "品鉴方法",
    },
    {
        "id": "q187",
        "query": "葡萄酒品味回味单宁评估方法",
        "expected_doc_title": "品味与回味品鉴方法百科",
        "expected_keywords": ["品味", "回味", "单宁", "酒体", "酸度"],
        "category": "品鉴方法",
    },
    {
        "id": "q188",
        "query": "葡萄酒品鉴术语 酒体平衡度复杂度",
        "expected_doc_title": "品鉴术语体系百科",
        "expected_keywords": ["酒体", "平衡度", "复杂度", "典型性", "术语"],
        "category": "品鉴方法",
    },
    {
        "id": "q189",
        "query": "盲品技巧训练 葡萄酒品种识别",
        "expected_doc_title": "盲品技巧与训练百科",
        "expected_keywords": ["盲品", "训练", "品种识别", "产区推断"],
        "category": "品鉴方法",
    },
    # === 配餐指南（4 条）===
    {
        "id": "q190",
        "query": "餐酒搭配总则 红酒配什么菜",
        "expected_doc_title": "餐酒搭配总则百科",
        "expected_keywords": ["餐酒搭配", "总则", "重量匹配", "风味互补", "酸度平衡"],
        "category": "配餐指南",
    },
    {
        "id": "q191",
        "query": "牛排配什么红酒 红肉搭配指南",
        "expected_doc_title": "红肉搭配指南百科",
        "expected_keywords": ["牛排", "红肉", "赤霞珠", "西拉", "马尔贝克"],
        "category": "配餐指南",
    },
    {
        "id": "q192",
        "query": "海鲜配什么白葡萄酒 鱼类贝类搭配",
        "expected_doc_title": "海鲜搭配指南百科",
        "expected_keywords": ["海鲜", "白葡萄酒", "长相思", "霞多丽", "雷司令"],
        "category": "配餐指南",
    },
    {
        "id": "q193",
        "query": "甜点奶酪搭配甜酒 波特贵腐配餐",
        "expected_doc_title": "甜点与奶酪搭配指南百科",
        "expected_keywords": ["甜点", "奶酪", "波特", "贵腐", "蓝纹奶酪"],
        "category": "配餐指南",
    },
    # === 季节性（3 条）===
    {
        "id": "q194",
        "query": "春季适合喝什么酒 春日酒文化",
        "expected_doc_title": "春季酒文化专题百科",
        "expected_keywords": ["春季", "花香型", "白葡萄酒", "樱花", "清酒"],
        "category": "季节性专题",
    },
    {
        "id": "q195",
        "query": "夏季清凉鸡尾酒 冰镇桃红热带饮品",
        "expected_doc_title": "夏季酒文化专题百科",
        "expected_keywords": ["夏季", "冰镇", "桃红", "热带", "高球"],
        "category": "季节性专题",
    },
    {
        "id": "q196",
        "query": "冬季热饮鸡尾酒 热饮酒蛋奶酒",
        "expected_doc_title": "冬季酒文化专题百科",
        "expected_keywords": ["冬季", "热饮", "热酒", "蛋奶酒", "威士忌热饮"],
        "category": "季节性专题",
    },
    # === 酒具档案（3 条）===
    {
        "id": "q197",
        "query": "摇酒壶种类选择 波士顿三段式巴黎式",
        "expected_doc_title": "摇酒壶深度档案百科",
        "expected_keywords": ["摇酒壶", "波士顿", "三段式", "巴黎式", "材质"],
        "category": "酒具档案",
    },
    {
        "id": "q198",
        "query": "滤冰器类型 哈氏朱利普细网滤冰器",
        "expected_doc_title": "滤冰器深度档案百科",
        "expected_keywords": ["滤冰器", "哈氏", "朱利普", "细网", "适用场景"],
        "category": "酒具档案",
    },
    {
        "id": "q199",
        "query": "量酒器与吧匙使用 双头量酒器刻度",
        "expected_doc_title": "量酒器与吧匙深度档案百科",
        "expected_keywords": ["量酒器", "吧匙", "双头", "刻度", "搅拌"],
        "category": "酒具档案",
    },
    # === 调酒师认证（2 条）===
    {
        "id": "q200",
        "query": "IBA 调酒师认证体系 WSET 葡萄酒认证",
        "expected_doc_title": "调酒师认证体系百科",
        "expected_keywords": ["IBA", "认证", "WSET", "CMS", "Sake Kikisake-shi"],
        "category": "调酒师认证",
    },
    {
        "id": "q201",
        "query": "调酒师职业发展路径 技能树开店指南",
        "expected_doc_title": "调酒师职业发展路径百科",
        "expected_keywords": ["职业发展", "技能树", "行业人脉", "开店", "职业阶段"],
        "category": "调酒师认证",
    },
]


def main() -> int:
    # 读取现有条目
    existing_lines = EVAL.read_text(encoding="utf-8").splitlines()
    existing_ids: set[str] = set()
    for line in existing_lines:
        if line.strip():
            d = json.loads(line)
            existing_ids.add(d.get("id", ""))

    print(f"现有评估集条目数：{len(existing_lines)}")
    print(f"现有 ID 集合大小：{len(existing_ids)}")

    # 过滤出尚未添加的新条目
    to_add = [e for e in NEW_ENTRIES if e["id"] not in existing_ids]
    skipped = [e for e in NEW_ENTRIES if e["id"] in existing_ids]

    if skipped:
        print(f"跳过已存在的条目：{[e['id'] for e in skipped]}")

    if not to_add:
        print("无新条目需要添加，全部已存在。")
        return 0

    # 追加到文件末尾
    new_lines = [json.dumps(e, ensure_ascii=False) for e in to_add]
    with EVAL.open("a", encoding="utf-8") as f:
        for line in new_lines:
            f.write(line + "\n")

    print(f"已追加 {len(to_add)} 条新条目：{[e['id'] for e in to_add]}")

    # 验证最终条目数
    final_lines = EVAL.read_text(encoding="utf-8").splitlines()
    final_count = sum(1 for l in final_lines if l.strip())
    print(f"最终评估集条目数：{final_count}")

    # 验证 JSONL 格式
    for line in final_lines:
        if line.strip():
            json.loads(line)  # 解析失败会抛出异常
    print("JSONL 格式验证通过。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
