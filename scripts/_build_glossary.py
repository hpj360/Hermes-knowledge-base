#!/usr/bin/env python3
"""中英双语调酒术语对照表构建脚本。

生成 200+ 词条，覆盖技法/器具/材料/配方四大类。
每条含：zh_name、en_name、category、description。
以 encyclopedia 类别文档形式存入知识库，source="glossary"。

幂等：通过 source_id="glossary:<en_name>" 去重，重复运行不重复插入。

使用方式：
    $env:KB_EMBEDDING_PROVIDER="hash"
    python scripts/_build_glossary.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# 术语词条：每条含 zh_name / en_name / category / description
# category 取值：technique（技法）/ tool（器具）/ material（材料）/ recipe（配方）
# ---------------------------------------------------------------------------
GLOSSARY: list[dict[str, str]] = [
    # ====================================================================
    # 技法 technique（33 条）
    # ====================================================================
    {
        "zh_name": "摇和",
        "en_name": "Shake",
        "category": "technique",
        "description": (
            "摇和核心技法，将原料与冰块放入摇酒壶双手用力摇晃 10-15 秒，"
            "使原料充分混合、冷却、稀释并注入空气，适用于含果汁、糖浆、"
            "奶制品、蛋清的配方，是戴基里、玛格丽特等酸酒类的基础。"
        ),
    },
    {
        "zh_name": "搅拌",
        "en_name": "Stir",
        "category": "technique",
        "description": (
            "用长柄吧勺在调和杯中沿杯壁缓慢旋转搅拌 20-30 圈，使酒液冷却"
            "并适度稀释，适用于全烈酒配方（无果汁/奶制品），追求丝滑口感"
            "与清澈酒液，是马天尼、曼哈顿等经典配方的代表技法。"
        ),
    },
    {
        "zh_name": "兑和",
        "en_name": "Build",
        "category": "technique",
        "description": (
            "将各原料直接倒入最终盛酒杯中加冰简单搅拌，不使用摇酒壶或调和杯，"
            "适用于原料本身易融合（如烈酒加汤力水、烈酒加果汁）且希望保留"
            "碳酸气泡的配方，如金汤力、螺丝刀、古典鸡尾酒。"
        ),
    },
    {
        "zh_name": "分层",
        "en_name": "Layer",
        "category": "technique",
        "description": (
            "利用不同液体的密度差异，将原料一层层叠加形成色彩分明的视觉层次，"
            "密度大的在下、密度小的在上，常用吧勺背引流缓慢倒入，是 B-52、"
            "彩虹鸡尾酒等视觉系配方的核心技法。"
        ),
    },
    {
        "zh_name": "捣压",
        "en_name": "Muddle",
        "category": "technique",
        "description": (
            "用捣碎器在杯中压碎新鲜水果、香草、糖块，释放香气与汁液，"
            "常用于莫吉托、卡琵林尼亚、Old Fashioned 古法等配方。"
            "注意薄荷捣压需轻柔，避免释放苦味；柑橘类需切块一同捣压。"
        ),
    },
    {
        "zh_name": "搅拌机",
        "en_name": "Blend",
        "category": "technique",
        "description": (
            "将原料与冰块放入电动搅拌机打成均匀冰沙状，热带与 Tiki 风格"
            "常用技法，适用于 Frozen 系列冰沙鸡尾酒，如 Frozen Daiquiri、"
            "Frozen Margarita、Piña Colada 部分版本。"
        ),
    },
    {
        "zh_name": "过滤",
        "en_name": "Strain",
        "category": "technique",
        "description": (
            "用滤冰器将摇和或搅拌后的酒液与冰块分离，使最终出品不含冰块，"
            "常用霍桑滤冰器配金属杯、朱利普滤冰器配玻璃调和杯，是出品前"
            "的关键步骤，确保酒液纯净且温度适中。"
        ),
    },
    {
        "zh_name": "双重过滤",
        "en_name": "Fine Strain",
        "category": "technique",
        "description": (
            "在常规过滤后再用细网滤器过滤碎冰与果肉，确保酒液纯净无渣，"
            "多用于含果肉或碎冰的配方，如含鲜果捣压的鸡尾酒，是高级调酒"
            "标准流程，提升出品质感与视觉清澈度。"
        ),
    },
    {
        "zh_name": "漂浮",
        "en_name": "Float",
        "category": "technique",
        "description": (
            "将密度较低的液体缓慢倒在密度较高液体表面形成漂浮层，如爱尔兰"
            "咖啡顶部的奶油漂浮、Tequila Sunrise 中红石榴糖浆下沉橙汁上浮"
            "的反向应用，是构建视觉层次的经典技法。"
        ),
    },
    {
        "zh_name": "洗杯",
        "en_name": "Rinse",
        "category": "technique",
        "description": (
            "用少量酒液润湿杯壁后倒出，赋予载杯淡淡香气而不改变酒体颜色，"
            "如萨泽拉克中的苦艾洗杯、部分鸡尾酒的苦精洗杯，是提升嗅觉层次"
            "又不影响视觉的高级技法。"
        ),
    },
    {
        "zh_name": "杯口装饰",
        "en_name": "Rim",
        "category": "technique",
        "description": (
            "将杯口用柠檬或青柠片湿润后蘸取盐、糖或香料粉（如辣椒粉、"
            "可可粉），如玛格丽特的盐边、咸狗的盐边、糖边鸡尾酒，是提升"
            "视觉与味觉层次的装饰技法。"
        ),
    },
    {
        "zh_name": "装饰",
        "en_name": "Garnish",
        "category": "technique",
        "description": (
            "在鸡尾酒最终加入的装饰物，如果皮扭（释放精油）、酒渍樱桃、"
            "绿橄榄、薄荷枝、水果切片等，提升视觉与嗅觉体验，是鸡尾酒"
            "出品不可忽视的收尾环节。"
        ),
    },
    {
        "zh_name": "浸泡",
        "en_name": "Infuse",
        "category": "technique",
        "description": (
            "将风味原料（水果、香草、香料）浸泡在烈酒中使其吸收风味的过程，"
            "如辣椒伏特加、香草朗姆、Hendrick's 风格黄瓜玫瑰金酒，浸泡"
            "时间因原料而异：柑橘皮 24 小时，香草 1-2 周。"
        ),
    },
    {
        "zh_name": "陈酿",
        "en_name": "Age",
        "category": "technique",
        "description": (
            "烈酒在橡木桶中陈年的过程，陈年时间影响色泽、香气、口感与价格，"
            "常见标注如威士忌 12 年、干邑 VS/VSOP/XO、朗姆酒 Blanco/"
            "Reposado/Añejo，是烈酒品质的核心指标。"
        ),
    },
    {
        "zh_name": "干摇",
        "en_name": "Dry Shake",
        "category": "technique",
        "description": (
            "不加冰块先摇和一次使蛋白充分起泡，再加冰块摇和冷却，常用于"
            "含蛋清的酸酒类配方如威士忌酸、皮斯科酸、克莱帕克，是产生"
            "绵密泡沫层的关键技法。"
        ),
    },
    {
        "zh_name": "反摇",
        "en_name": "Reverse Shake",
        "category": "technique",
        "description": (
            "先加冰摇和再过滤掉冰块后干摇一次，使泡沫更绵密细腻，是高级"
            "调酒技巧，比常规干摇-湿摇顺序产生更持久的泡沫层，常用于"
            "追求极致质感的蛋白酸酒。"
        ),
    },
    {
        "zh_name": "投冰",
        "en_name": "Throw",
        "category": "technique",
        "description": (
            "将酒液在两个容器间来回倾倒混合，同时冷却并注入空气，是古典"
            "调酒师的表演性技法，常用于热饮如爱尔兰咖啡或苏格兰烫热"
            "威士忌，兼具混合、冷却与柔化酒体之效。"
        ),
    },
    {
        "zh_name": "烟熏",
        "en_name": "Smoke",
        "category": "technique",
        "description": (
            "用烟熏枪或燃烧木材对酒液或载杯熏烟，赋予烟熏风味，多用于"
            "威士忌基酒的复古配方如烟熏古典、烟熏曼哈顿，是现代调酒"
            "提升复杂度与戏剧感的进阶技法。"
        ),
    },
    {
        "zh_name": "燃烧",
        "en_name": "Flaming",
        "category": "technique",
        "description": (
            "点燃酒液表面的高酒精成分产生火焰效果，如火焰咖啡、蓝 blazer、"
            "燃烧 B-52，需谨慎操作，是表演性调酒的视觉高潮，高酒精度"
            "利口酒如 151 朗姆常作为燃料。"
        ),
    },
    {
        "zh_name": "滚动",
        "en_name": "Roll",
        "category": "technique",
        "description": (
            "将原料在两个摇酒壶间轻轻来回倾倒 4-6 次混合，比摇和温和、"
            "比搅拌剧烈，常用于血腥玛丽等含浓稠果汁又希望保留质感"
            "的配方，是介于 Stir 与 Shake 之间的柔和混合技法。"
        ),
    },
    {
        "zh_name": "冰雕",
        "en_name": "Ice Carving",
        "category": "technique",
        "description": (
            "用冰锥雕刻大冰块成特定形状如钻石、球、柱，提升视觉与减缓"
            "融化稀释，是高级酒吧的视觉招牌，手工雕刻冰球与钻石冰"
            "是日式调酒的代表性技艺。"
        ),
    },
    {
        "zh_name": "制冰",
        "en_name": "Ice Making",
        "category": "technique",
        "description": (
            "制作不同形态的冰块如大方冰、球冰、碎冰、冰沙，不同冰型"
            "影响冷却速度与稀释率：大冰块融化慢适合烈酒，碎冰快速"
            "冷却适合朱莉普与热带鸡尾酒，是调酒基础准备工艺。"
        ),
    },
    {
        "zh_name": "切片",
        "en_name": "Slice",
        "category": "technique",
        "description": (
            "将水果切成片状如橙片、柠檬片、青柠轮，用于装饰或投入杯中，"
            "是基础备料技法，切片厚度与切法影响视觉与香气释放，"
            "橙轮、柠檬半圆片是高球类鸡尾酒的标准装饰。"
        ),
    },
    {
        "zh_name": "削皮",
        "en_name": "Peel",
        "category": "technique",
        "description": (
            "用削皮刀或吧刀削下柑橘外皮释放精油，扭成螺旋状装饰杯口，"
            "是马天尼、古典鸡尾酒的标志性装饰，削皮需避免白色苦味"
            "海绵层，仅取彩色外皮释放精油香气。"
        ),
    },
    {
        "zh_name": "榨汁",
        "en_name": "Juice",
        "category": "technique",
        "description": (
            "用手动或电动榨汁器榨取柠檬、青柠、橙等新鲜果汁，鲜榨果汁"
            "是高品质鸡尾酒的基础，柠檬汁与青柠汁是鸡尾酒第一酸源，"
            "建议现榨现用以保留鲜活酸度。"
        ),
    },
    {
        "zh_name": "量酒",
        "en_name": "Measure",
        "category": "technique",
        "description": (
            "用量酒器精确量取原料，确保配方比例准确，是专业调酒与家用"
            "调酒的根本区别之一，标准量酒器双头 30ml/60ml 或 25ml/50ml，"
            "精准量酒是稳定出品的基石。"
        ),
    },
    {
        "zh_name": "调和",
        "en_name": "Mix",
        "category": "technique",
        "description": (
            "泛指将多种原料按比例混合成为鸡尾酒的过程，是调酒的核心动作，"
            "涵盖摇和、搅拌、兑和等所有混合方式，调酒师通过调和构建"
            "酸、甜、苦、烈的味觉平衡。"
        ),
    },
    {
        "zh_name": "装杯",
        "en_name": "Serve",
        "category": "technique",
        "description": (
            "将调好的鸡尾酒倒入合适的载杯中并提供装饰，载杯选择影响"
            "口感温度与视觉：马天尼杯冰镇、古典杯加冰、高球杯长饮，"
            "是出品前的最后一步。"
        ),
    },
    {
        "zh_name": "加气",
        "en_name": "Carbonate",
        "category": "technique",
        "description": (
            "通过添加碳酸饮料或苏打水为鸡尾酒注入气泡，增加清爽感与"
            "口感层次，常用于高球类长饮如金汤力、莫吉托、汤姆柯林斯，"
            "气泡提升嗅觉释放与解腻感。"
        ),
    },
    {
        "zh_name": "甜化",
        "en_name": "Sweeten",
        "category": "technique",
        "description": (
            "添加糖浆、利口酒或蜂蜜等甜味剂平衡酸度与酒感，是构建"
            "鸡尾酒风味平衡的关键，单糖浆是最常用甜化剂，2:1 rich "
            "syrup 更甜更稠，常用于高档配方。"
        ),
    },
    {
        "zh_name": "酸化",
        "en_name": "Acidulate",
        "category": "technique",
        "description": (
            "添加柠檬汁、青柠汁等柑橘果汁提供酸度，与甜味剂共同构建"
            "酸甜平衡，是酸酒类鸡尾酒如戴基里、威士忌酸、玛格丽特"
            "的核心技法，鲜榨果汁优于瓶装。"
        ),
    },
    {
        "zh_name": "冰镇",
        "en_name": "Chill",
        "category": "technique",
        "description": (
            "将载杯或酒液预先冷却降低温度，常用冰块预冷载杯或冷藏"
            "酒瓶提升出品品质，冰镇马天尼杯是 Stir 类配方的标准准备，"
            "香槟杯冰镇可保持气泡持久。"
        ),
    },
    {
        "zh_name": "澄清",
        "en_name": "Clarify",
        "category": "technique",
        "description": (
            "通过离心、过滤、明胶沉淀等方法去除鸡尾酒中的悬浮颗粒"
            "与果肉，得到透明酒液，是现代高级调酒技法，如澄清奶潘趣、"
            "澄清血腥玛丽，兼具视觉与口感提升。"
        ),
    },

    # ====================================================================
    # 器具 tool（55 条）
    # ====================================================================
    {
        "zh_name": "摇酒壶",
        "en_name": "Shaker",
        "category": "tool",
        "description": (
            "调酒核心器具，用于摇和混合原料与冰块，分为波士顿摇酒壶、"
            "三段式摇酒壶、巴黎摇酒壶三种主要类型，专业调酒师必备，"
            "容量通常 500-700ml，影响混合效率与出品温度。"
        ),
    },
    {
        "zh_name": "波士顿摇酒壶",
        "en_name": "Boston Shaker",
        "category": "tool",
        "description": (
            "两件套金属大杯加玻璃调和杯（或两金属杯），调酒师专业首选，"
            "容量大、操作快、密封性好，敲击密封后摇和，需配独立滤冰器，"
            "是商业酒吧标准配置。"
        ),
    },
    {
        "zh_name": "三段式摇酒壶",
        "en_name": "Cobbler Shaker",
        "category": "tool",
        "description": (
            "金属壶身加内置滤网加顶盖三件套，自带滤网便于家用，"
            "无需另配滤冰器；缺点是容量小、易堵塞果肉，适合家庭"
            "调酒与初学者使用，欧洲传统酒吧常用。"
        ),
    },
    {
        "zh_name": "巴黎摇酒壶",
        "en_name": "Parisian Shaker",
        "category": "tool",
        "description": (
            "两件全金属外观优雅，类似波士顿但更圆润，法国高端酒吧"
            "常用，密封性极佳，需配独立滤冰器，造型美观兼具专业性能，"
            "是高端酒吧的审美选择。"
        ),
    },
    {
        "zh_name": "量酒器",
        "en_name": "Jigger",
        "category": "tool",
        "description": (
            "量取原料的金属双头锥形容器，常见 30ml/60ml、25ml/50ml、"
            "15ml/30ml 组合，确保配方比例精确，是专业调酒与家用调酒"
            "的根本区别之一，日本款细长精致专业调酒师偏好。"
        ),
    },
    {
        "zh_name": "滤冰器",
        "en_name": "Strainer",
        "category": "tool",
        "description": (
            "将摇和或搅拌后的酒液与冰块分离的器具，分为霍桑滤冰器、"
            "朱利普滤冰器、细网滤冰器三种主要类型，是摇和搅拌后"
            "出品的必备器具。"
        ),
    },
    {
        "zh_name": "霍桑滤冰器",
        "en_name": "Hawthorne Strainer",
        "category": "tool",
        "description": (
            "金属丝圈滤网，专配金属调酒杯或波士顿摇酒壶，最常用的"
            "滤冰器类型，弹簧圈贴合杯口拦截冰块与果肉，是商业酒吧"
            "标配，适配大部分摇和操作。"
        ),
    },
    {
        "zh_name": "朱利普滤冰器",
        "en_name": "Julep Strainer",
        "category": "tool",
        "description": (
            "浅碗状带孔勺，专配玻璃调和杯，常用于搅拌后滤酒，造型"
            "优雅古典，是 Stir 技法如曼哈顿、马天尼的标准配置，"
            "也是薄荷朱莉普的传统器具。"
        ),
    },
    {
        "zh_name": "细网滤冰器",
        "en_name": "Fine Strainer",
        "category": "tool",
        "description": (
            "双层细网滤器，二次过滤碎冰与果肉确保酒液纯净，双重过滤"
            "必备器具，多用于含果肉或碎冰的配方，提升出品质感，"
            "常与霍桑滤冰器串联使用。"
        ),
    },
    {
        "zh_name": "吧勺",
        "en_name": "Bar Spoon",
        "category": "tool",
        "description": (
            "长柄螺旋勺约 30cm，一端小勺一端压扁器或叉，用于搅拌、"
            "量取少量糖浆、取橄榄/樱桃等多种用途，螺旋柄便于在杯中"
            "旋转搅拌，是调酒师手中的万能工具。"
        ),
    },
    {
        "zh_name": "捣碎棒",
        "en_name": "Muddler",
        "category": "tool",
        "description": (
            "木质或金属捣棒，用于捣压薄荷、柑橘、糖块释放香气与汁液，"
            "莫吉托、卡琵林尼亚、Old Fashioned 古法必备器具，木质"
            "捣棒不可水洗浸泡，用湿布擦拭即可。"
        ),
    },
    {
        "zh_name": "调和杯",
        "en_name": "Mixing Glass",
        "category": "tool",
        "description": (
            "玻璃材质容积 400-600ml，用于搅拌技法调制曼哈顿、马天尼"
            "等全烈酒配方，厚壁玻璃耐温差，配合朱利普滤冰器使用，"
            "是 Stir 技法的核心器具。"
        ),
    },
    {
        "zh_name": "调酒杯",
        "en_name": "Mixing Tin",
        "category": "tool",
        "description": (
            "金属调和杯，常与玻璃调和杯组成波士顿摇酒壶，也可单独"
            "用于搅拌或滚摇，不锈钢材质导热快、坚固耐用，是商业"
            "酒吧标准配置。"
        ),
    },
    {
        "zh_name": "砧板",
        "en_name": "Cutting Board",
        "category": "tool",
        "description": (
            "切割水果装饰的木质或塑料砧板，调酒师备料基础工具，"
            "需保持清洁干燥，避免交叉污染，常配有防滑垫或湿毛巾"
            "固定，是吧台卫生的第一道防线。"
        ),
    },
    {
        "zh_name": "吧刀",
        "en_name": "Paring Knife",
        "category": "tool",
        "description": (
            "小型锋利刀具，用于切果皮、削果皮、切水果片，是装饰"
            "制作的核心工具，需保持刀刃锋利以确保切片整齐美观，"
            "削柑橘皮需避开白色苦味层。"
        ),
    },
    {
        "zh_name": "榨汁器",
        "en_name": "Citrus Juicer",
        "category": "tool",
        "description": (
            "手动或电动榨柠檬、青柠的工具，鲜榨果汁是高品质鸡尾酒"
            "的基础，手动榨汁器便携适合家用，电动榨汁器高效适合"
            "商业酒吧，现榨现用保留鲜活酸度。"
        ),
    },
    {
        "zh_name": "冰锥",
        "en_name": "Ice Pick",
        "category": "tool",
        "description": (
            "雕刻大冰块的尖锥工具，用于分裂冰块或雕刻冰球、钻石冰"
            "等造型，是日式调酒与高端酒吧的必备工具，使用需谨慎，"
            "配合冰锥套保护存放。"
        ),
    },
    {
        "zh_name": "冰夹",
        "en_name": "Ice Tongs",
        "category": "tool",
        "description": (
            "夹取冰块的工具，金属或塑料材质，常见于吧台冰桶旁便于"
            "取冰，部分冰夹带齿设计稳固夹取球形冰，是吧台标准"
            "配置工具。"
        ),
    },
    {
        "zh_name": "冰铲",
        "en_name": "Ice Scoop",
        "category": "tool",
        "description": (
            "铲取冰块的金属或塑料铲子，比冰夹效率高，常用于从制冰机"
            "或冰桶取冰，容量大适合高峰期快速取冰，是商业酒吧"
            "必备工具。"
        ),
    },
    {
        "zh_name": "冰模",
        "en_name": "Ice Mold",
        "category": "tool",
        "description": (
            "制作大方形、球形、柱形冰块的硅胶模具，缓慢融化降低"
            "稀释率提升出品品质，大冰块表面积小融化慢，是高端"
            "酒吧的标准配备。"
        ),
    },
    {
        "zh_name": "喷壶",
        "en_name": "Atomizer",
        "category": "tool",
        "description": (
            "装苦艾或苦精的喷雾器，喷洒装饰载杯或酒液表面，控制"
            "极小用量，常用于萨泽拉克的苦艾洗杯替代倒出，是"
            "现代调酒精确控制香气的工具。"
        ),
    },
    {
        "zh_name": "酒嘴",
        "en_name": "Pour Spout",
        "category": "tool",
        "description": (
            "安装在酒瓶口控制倒酒速度与流量的器具，分为标准、塔形、"
            "量酒酒嘴等，提升倒酒精度与流畅度，是商业酒吧高效出品的"
            "标准配置。"
        ),
    },
    {
        "zh_name": "冰桶",
        "en_name": "Ice Bucket",
        "category": "tool",
        "description": (
            "隔热容器存放冰块防止融化，金属或塑料材质，配冰夹使用，"
            "是吧台与餐桌的标准配备，双层隔热设计提升保温效果，"
            "常用于香槟桶与冰酒桶。"
        ),
    },
    {
        "zh_name": "量杯",
        "en_name": "Measuring Cup",
        "category": "tool",
        "description": (
            "玻璃或塑料刻度杯，量取大量液体如果汁、苏打水，比量酒器"
            "容量大，常用于备料与批量调酒，玻璃刻度杯便于观察液位，"
            "是吧台辅助量具。"
        ),
    },
    {
        "zh_name": "漏斗",
        "en_name": "Funnel",
        "category": "tool",
        "description": (
            "倒酒或转移液体的辅助工具，常用于将利口酒分装到酒瓶或"
            "制作浸泡酒，是小口瓶分装的必备工具，配合滤纸可用于"
            "澄清鸡尾酒过滤。"
        ),
    },
    {
        "zh_name": "制冰机",
        "en_name": "Ice Maker",
        "category": "tool",
        "description": (
            "自动制冰设备，生产方形、碎冰或雪花冰，是商业酒吧的"
            "核心设备，产量与冰型影响出品效率与质量，部分高端"
            "机型可生产透明大方冰。"
        ),
    },
    {
        "zh_name": "碎冰机",
        "en_name": "Ice Crusher",
        "category": "tool",
        "description": (
            "将冰块打碎成碎冰的设备，手动或电动，常用于朱莉普、"
            "斯威齐等需要碎冰的配方，碎冰快速冷却且贴合杯壁，"
            "是热带鸡尾酒的必备工具。"
        ),
    },
    {
        "zh_name": "调酒棒",
        "en_name": "Stirrer",
        "category": "tool",
        "description": (
            "长条塑料或金属棒，用于在杯中搅拌兑和类鸡尾酒，常作为"
            "客人自助搅拌工具，高球类长饮标配，部分可降解材质"
            "更环保。"
        ),
    },
    {
        "zh_name": "吸管",
        "en_name": "Straw",
        "category": "tool",
        "description": (
            "塑料、金属或纸质吸管，提供饮用体验并保护客人牙齿"
            "免受酸性饮料侵蚀，金属吸管可重复使用环保，纸质吸管"
            "可降解但易软化，是现代调酒环保趋势。"
        ),
    },
    {
        "zh_name": "杯垫",
        "en_name": "Coaster",
        "category": "tool",
        "description": (
            "隔热防滑的垫子，保护桌面免受杯壁冷凝水侵蚀，材质有"
            "软木、纸、金属、硅胶，也是酒吧品牌宣传的载体，"
            "是吧台与餐桌的标配。"
        ),
    },
    {
        "zh_name": "鸡尾酒签",
        "en_name": "Cocktail Pick",
        "category": "tool",
        "description": (
            "金属或塑料签，串樱桃、橄榄、水果片装饰，提升视觉与"
            "便于取食，长签串多层水果短签串单颗橄榄，是马天尼、"
            "曼哈顿等配方的装饰配件。"
        ),
    },
    {
        "zh_name": "滴管",
        "en_name": "Dasher",
        "category": "tool",
        "description": (
            "苦精瓶的专用瓶口，控制每次滴出几滴苦精，是剂量控制"
            "的关键配件，1 dash 约等于 6-9 滴，安高天娜与佩肖德"
            "苦精均标配 dasher 瓶口。"
        ),
    },
    {
        "zh_name": "滤纸",
        "en_name": "Coffee Filter",
        "category": "tool",
        "description": (
            "过滤澄清鸡尾酒的细密滤纸，用于高级调酒的澄清工艺"
            "去除杂质，配合漏斗使用可得到透明酒液，是现代"
            "澄清技法的耗材。"
        ),
    },
    {
        "zh_name": "马天尼杯",
        "en_name": "Martini Glass",
        "category": "tool",
        "description": (
            "V 形浅口高脚杯，容量 90-180ml，是马天尼、曼哈顿等"
            "经典鸡尾酒的标志性载杯，冰镇后使用保持低温，"
            "V 形设计便于装饰与握持。"
        ),
    },
    {
        "zh_name": "古典杯",
        "en_name": "Rocks Glass",
        "category": "tool",
        "description": (
            "短厚壁平底杯，容量 180-300ml，用于古典鸡尾酒、加冰"
            "威士忌等，厚壁保持冰镇手感，是烈酒加冰与 Build "
            "技法的标准载杯。"
        ),
    },
    {
        "zh_name": "高球杯",
        "en_name": "Highball Glass",
        "category": "tool",
        "description": (
            "高直壁圆柱杯，容量 240-350ml，用于海波、莫吉托、"
            "汤力等长饮，直壁设计便于加冰与碳酸饮料分层，是"
            "吧台最常用的载杯之一。"
        ),
    },
    {
        "zh_name": "柯林斯杯",
        "en_name": "Collins Glass",
        "category": "tool",
        "description": (
            "比高球杯更高更窄的圆柱杯，容量 300-410ml，用于汤姆"
            "柯林斯、约翰柯林斯等长饮，窄口减少气泡流失，是"
            "长饮类鸡尾酒的标准载杯。"
        ),
    },
    {
        "zh_name": "飓风杯",
        "en_name": "Hurricane Glass",
        "category": "tool",
        "description": (
            "矮胖曲线杯，容量 350-600ml，用于热带鸡尾酒如飓风、"
            "龙舌兰日出，曲线造型源于飓风灯，是新奥尔良法国区"
            "标志性的载杯。"
        ),
    },
    {
        "zh_name": "玛格丽特杯",
        "en_name": "Margarita Glass",
        "category": "tool",
        "description": (
            "双层碗状高脚杯，容量 200-300ml，专用于玛格丽特"
            "鸡尾酒，可加糖边盐边，双层设计便于装饰与握持，"
            "是墨西哥国饮的标志性载杯。"
        ),
    },
    {
        "zh_name": "香槟杯",
        "en_name": "Champagne Flute",
        "category": "tool",
        "description": (
            "细长笛形杯，容量 180-240ml，用于香槟、起泡酒及含"
            "气泡鸡尾酒如含羞草、法兰西 75，细长造型减少气泡"
            "流失，保持气泡持久。"
        ),
    },
    {
        "zh_name": "郁金香杯",
        "en_name": "Coupe Glass",
        "category": "tool",
        "description": (
            "浅碗形高脚杯，容量 120-180ml，用于古典酸酒类鸡尾酒"
            "如戴基里、侧车、Aviation，也是香槟的传统载杯，"
            "造型优雅复古。"
        ),
    },
    {
        "zh_name": "白兰地杯",
        "en_name": "Snifter",
        "category": "tool",
        "description": (
            "矮胖圆肚短脚杯，容量 240-450ml，用于白兰地纯饮，"
            "掌心温酒提升香气，窄口聚香设计，是白兰地品鉴的"
            "标准载杯。"
        ),
    },
    {
        "zh_name": "葡萄酒杯",
        "en_name": "Wine Glass",
        "category": "tool",
        "description": (
            "高脚大肚杯，分为红葡萄酒杯、白葡萄酒杯，容量"
            "240-450ml，红葡萄酒杯肚大聚香，白葡萄酒杯略小"
            "保持冰镇，是品鉴与佐餐的标准载杯。"
        ),
    },
    {
        "zh_name": "老式杯",
        "en_name": "Old Fashioned Glass",
        "category": "tool",
        "description": (
            "同古典杯，短壁平底杯，专用于古典鸡尾酒，容量"
            "180-240ml，厚壁设计保持冰镇手感，是 Build 技法"
            "与烈酒加冰的经典载杯。"
        ),
    },
    {
        "zh_name": "铜杯",
        "en_name": "Copper Mug",
        "category": "tool",
        "description": (
            "铜制马克杯，专用于莫斯科骡子，铜导热性强使饮品"
            "更冰凉，是 1940 年代美国营销创意的经典搭配，"
            "内壁镀镍或不锈钢避免铜离子溶出。"
        ),
    },
    {
        "zh_name": "威士忌杯",
        "en_name": "Whisky Glass",
        "category": "tool",
        "description": (
            "类似古典杯的短壁厚底杯，部分为格兰凯恩品鉴杯"
            "专用于威士忌纯饮，厚底聚香设计，是威士忌品鉴"
            "与加冰饮用的标准载杯。"
        ),
    },
    {
        "zh_name": "嗅杯",
        "en_name": "Glencairn Glass",
        "category": "tool",
        "description": (
            "苏格兰威士忌专用品鉴杯，郁金香形聚香设计，是"
            "威士忌品鉴的标准杯型，窄口聚拢香气提升嗅觉体验，"
            "广泛用于专业品鉴与酒厂品酒室。"
        ),
    },
    {
        "zh_name": "利口酒杯",
        "en_name": "Cordial Glass",
        "category": "tool",
        "description": (
            "小型高脚杯，容量 60-90ml，用于纯饮利口酒或餐后"
            "甜酒，是小杯慢饮的标准载杯，造型精致优雅，"
            "常用于餐后消化酒服务。"
        ),
    },
    {
        "zh_name": "雪莉杯",
        "en_name": "Sherry Glass",
        "category": "tool",
        "description": (
            "窄口小高脚杯，容量 60-120ml，用于雪莉酒、波特酒"
            "及部分餐后酒，窄口聚香设计适合加强酒品鉴，是"
            "西班牙与葡萄牙传统酒具。"
        ),
    },
    {
        "zh_name": "试管杯",
        "en_name": "Shot Glass",
        "category": "tool",
        "description": (
            "小型直壁杯，容量 30-60ml，用于烈酒直饮或分层"
            "鸡尾酒如 B-52，是烈酒纯饮与短饮的标准载杯，"
            "也是量酒器的参考量具。"
        ),
    },
    {
        "zh_name": "玻璃调和杯",
        "en_name": "Glass Mixing Cup",
        "category": "tool",
        "description": (
            "波士顿摇酒壶的玻璃部分，用于盛装原料观察摇和过程，"
            "可与金属杯组合成波士顿摇酒壶，厚壁玻璃耐温差，"
            "也可单独用于 Stir 技法。"
        ),
    },
    {
        "zh_name": "不锈钢调酒杯",
        "en_name": "Stainless Tin",
        "category": "tool",
        "description": (
            "波士顿摇酒壶的金属部分，用于摇和冷却原料，坚固"
            "耐用导热快，是商业酒吧标准配置，常与玻璃调和杯"
            "组合使用，也可单独用于 Roll 技法。"
        ),
    },
    {
        "zh_name": "冰球模具",
        "en_name": "Sphere Ice Mold",
        "category": "tool",
        "description": (
            "制作球形冰块的硅胶模具，球冰表面积小融化慢，"
            "常用于威士忌加冰，减少稀释保持酒体醇厚，是"
            "高端酒吧与家用调酒的品质提升器具。"
        ),
    },
    {
        "zh_name": "方冰模具",
        "en_name": "Cube Ice Mold",
        "category": "tool",
        "description": (
            "制作方形大冰块的硅胶模具，方冰融化均匀适合"
            "古典杯类鸡尾酒，大方冰表面积小减缓稀释，是"
            "Old Fashioned 与加冰烈酒的理想选择。"
        ),
    },
    {
        "zh_name": "温酒器",
        "en_name": "Wine Warmer",
        "category": "tool",
        "description": (
            "温热清酒或葡萄酒的设备，控温精准，是日式酒吧"
            "与传统欧式酒吧的辅助器具，清酒燗酒与热红酒"
            "Mulled Wine 的专用设备。"
        ),
    },

    # ====================================================================
    # 材料 material（86 条）
    # ====================================================================
    {
        "zh_name": "金酒",
        "en_name": "Gin",
        "category": "material",
        "description": (
            "以谷物为原料经蒸馏后用杜松子等植物香料浸泡或二次"
            "蒸馏而成的烈酒，酒精度 35-55%，被誉为鸡尾酒心脏，"
            "是马天尼、尼格罗尼、金汤力等经典配方的核心基酒。"
        ),
    },
    {
        "zh_name": "威士忌",
        "en_name": "Whisky",
        "category": "material",
        "description": (
            "以谷物发酵蒸馏橡木桶陈酿而成的烈酒，酒精度 40-60%，"
            "主要产地苏格兰、美国、爱尔兰、日本、加拿大，是曼哈顿、"
            "古典、威士忌酸等配方的核心基酒。"
        ),
    },
    {
        "zh_name": "朗姆酒",
        "en_name": "Rum",
        "category": "material",
        "description": (
            "以甘蔗糖蜜或甘蔗汁为原料发酵蒸馏陈酿而成的烈酒，"
            "酒精度 40-75%，加勒比海国酒，是莫吉托、戴基里、"
            "椰林飘香等热带鸡尾酒的核心基酒。"
        ),
    },
    {
        "zh_name": "龙舌兰",
        "en_name": "Tequila",
        "category": "material",
        "description": (
            "以蓝色龙舌兰植物心部为原料烘烤发酵蒸馏而成的"
            "墨西哥国酒，酒精度 35-55%，是玛格丽特、龙舌兰日出、"
            "帕洛玛等配方的核心基酒。"
        ),
    },
    {
        "zh_name": "伏特加",
        "en_name": "Vodka",
        "category": "material",
        "description": (
            "以谷物或马铃薯为原料多次蒸馏过滤而成的中性烈酒，"
            "酒精度 35-50%，纯净无味为核心特征，是莫斯科骡子、"
            "血腥玛丽、螺丝刀等配方的万能基酒。"
        ),
    },
    {
        "zh_name": "白兰地",
        "en_name": "Brandy",
        "category": "material",
        "description": (
            "以水果为原料发酵蒸馏橡木桶陈酿而成的烈酒，"
            "酒精度 35-60%，葡萄白兰地为主流，是侧车、亚历山大、"
            "白兰地古典等配方的核心基酒，干邑与雅文邑为高端代表。"
        ),
    },
    {
        "zh_name": "中国白酒",
        "en_name": "Baijiu",
        "category": "material",
        "description": (
            "以高粱等谷物为原料曲类糖化发酵蒸馏陈酿勾兑而成的"
            "中国特产蒸馏酒，酒精度 38-65%，分酱香、浓香、清香"
            "等 12 大香型，茅台、五粮液、汾酒为代表品牌。"
        ),
    },
    {
        "zh_name": "日本清酒",
        "en_name": "Sake",
        "category": "material",
        "description": (
            "以米、米麹、水为原料并行复发酵酿制的日本传统"
            "酒精饮料，酒精度 15-20%，分纯米、本酿造、吟酿等"
            "级别，獭祭、久保田、八海山为代表品牌。"
        ),
    },
    {
        "zh_name": "韩国烧酒",
        "en_name": "Soju",
        "category": "material",
        "description": (
            "以米或淀粉原料发酵蒸馏稀释而成的韩国传统蒸馏酒，"
            "酒精度 16-25%，全球销量最大品类之一，真露、好天"
            "好饮为代表品牌，与韩式烤肉搭配绝佳。"
        ),
    },
    {
        "zh_name": "梅斯卡尔",
        "en_name": "Mezcal",
        "category": "material",
        "description": (
            "泛指所有龙舌兰酒，可使用多种龙舌兰，烟熏风味明显，"
            "龙舌兰酒 Tequila 是其子集，主要产自瓦哈卡州，"
            "是现代调酒中烟熏元素的代表烈酒。"
        ),
    },
    {
        "zh_name": "卡夏萨",
        "en_name": "Cachaca",
        "category": "material",
        "description": (
            "巴西甘蔗汁蒸馏酒，与朗姆酒不同类（朗姆用糖蜜），"
            "酒精度 38-48%，是卡琵林尼亚的核心原料，巴西国酒，"
            "带有新鲜甘蔗青草香。"
        ),
    },
    {
        "zh_name": "波本威士忌",
        "en_name": "Bourbon",
        "category": "material",
        "description": (
            "美国威士忌，≥51% 玉米新橡木桶陈酿，甜润香草感，"
            "代表品牌美格、四玫瑰、Jim Beam，是古典鸡尾酒、"
            "威士忌酸、薄荷朱莉普的核心基酒。"
        ),
    },
    {
        "zh_name": "黑麦威士忌",
        "en_name": "Rye Whiskey",
        "category": "material",
        "description": (
            "≥51% 黑麦的美国或加拿大威士忌，辛香、胡椒感，"
            "是曼哈顿、萨泽拉克、古典鸡尾酒的经典原料，"
            "代表品牌布克、莱特曼、Rittenhouse。"
        ),
    },
    {
        "zh_name": "苏格兰威士忌",
        "en_name": "Scotch Whisky",
        "category": "material",
        "description": (
            "苏格兰产威士忌，至少陈酿 3 年，分单一麦芽、单一谷物、"
            "调和三类，代表品牌麦卡伦、格兰菲迪、尊尼获加，是教父、"
            "锈钉、罗伯罗伊的核心基酒。"
        ),
    },
    {
        "zh_name": "爱尔兰威士忌",
        "en_name": "Irish Whiskey",
        "category": "material",
        "description": (
            "通常三次蒸馏、不使用泥煤，口感柔顺、清甜，代表品牌"
            "尊美醇、知更鸟、Tullamore DEW，是爱尔兰咖啡与部分"
            "酸酒的经典基酒。"
        ),
    },
    {
        "zh_name": "田纳西威士忌",
        "en_name": "Tennessee Whiskey",
        "category": "material",
        "description": (
            "波本变种，经糖枫木炭过滤，代表品牌杰克丹尼、George "
            "Dickel，口感顺滑独特，是杰克丹尼古典与部分长饮的"
            "核心基酒。"
        ),
    },
    {
        "zh_name": "日本威士忌",
        "en_name": "Japanese Whisky",
        "category": "material",
        "description": (
            "借鉴苏格兰工艺，清新细腻，代表品牌山崎、白州、响、"
            "余市，是日式海波 Highball 与现代鸡尾酒的高品质"
            "基酒，21 世纪全球威士忌热潮代表。"
        ),
    },
    {
        "zh_name": "干邑",
        "en_name": "Cognac",
        "category": "material",
        "description": (
            "法国干邑区产的葡萄白兰地，二次壶式蒸馏，分 VS、"
            "VSOP、XO 等级，最负盛名，代表品牌轩尼诗、人头马、"
            "马爹利，是侧车、萨泽拉克的经典基酒。"
        ),
    },
    {
        "zh_name": "雅文邑",
        "en_name": "Armagnac",
        "category": "material",
        "description": (
            "法国最古老的白兰地产区，连续蒸馏为主，风格比干邑"
            "更粗犷浓郁，被称为男人的白兰地，代表品牌 Château "
            "de Laubade、Darroze，是法式餐后酒代表。"
        ),
    },
    {
        "zh_name": "皮斯科",
        "en_name": "Pisco",
        "category": "material",
        "description": (
            "秘鲁与智利的国酒，葡萄汁发酵蒸馏的未陈酿白兰地，"
            "是皮斯科酸的核心原料，带有新鲜葡萄花果香，分秘鲁"
            "Puro 与智利风格，秘鲁受 AOC 保护。"
        ),
    },
    {
        "zh_name": "雪莉酒",
        "en_name": "Sherry",
        "category": "material",
        "description": (
            "西班牙赫雷斯产区加强葡萄酒，从干型到甜型风格多样，"
            "Fino、Manzanilla 干爽，Oloroso、Pedro Ximénez 甜润，"
            "是调酒与品鉴的重要原料。"
        ),
    },
    {
        "zh_name": "波特酒",
        "en_name": "Port",
        "category": "material",
        "description": (
            "葡萄牙波特产区加强葡萄酒，加入白兰地终止发酵保留"
            "甜度，是经典餐后甜酒，分 Ruby、Tawny、Vintage 等"
            "类型，也是部分鸡尾酒的甜味与色泽来源。"
        ),
    },
    {
        "zh_name": "苹果白兰地",
        "en_name": "Calvados",
        "category": "material",
        "description": (
            "法国诺曼底苹果白兰地，橡木桶陈酿，带有苹果香与"
            "木质感，是苹果白兰地代表，用于部分古典鸡尾酒变体"
            "与杰克玫瑰等配方。"
        ),
    },
    {
        "zh_name": "单一麦芽威士忌",
        "en_name": "Single Malt Whisky",
        "category": "material",
        "description": (
            "单一酒厂 100% 麦芽壶式蒸馏的威士忌，是苏格兰"
            "威士忌的高端类型，代表品牌麦卡伦、格兰菲迪、"
            "拉弗格，是纯饮与高端鸡尾酒的基酒。"
        ),
    },
    {
        "zh_name": "调和威士忌",
        "en_name": "Blended Whisky",
        "category": "material",
        "description": (
            "麦芽威士忌与谷物威士忌调和而成，代表品牌尊尼获加、"
            "芝华士、响，风格平衡易饮，是商业酒吧与日常调酒的"
            "常用基酒，性价比高。"
        ),
    },
    {
        "zh_name": "老汤姆金酒",
        "en_name": "Old Tom Gin",
        "category": "material",
        "description": (
            "介于 London Dry 与荷兰 Genever 之间的微甜金酒，"
            "是古典鸡尾酒配方常用，也是汤姆柯林斯的传统基酒，"
            "代表品牌 Hayman's、Ransom，18-19 世纪流行风格复兴。"
        ),
    },
    {
        "zh_name": "荷兰金酒",
        "en_name": "Genever",
        "category": "material",
        "description": (
            "荷兰原版金酒，麦芽基底带有谷物感，是金酒的祖先，"
            "风味比 London Dry 更厚重，代表品牌 Bols、Nolet's，"
            "适合纯饮与古典鸡尾酒。"
        ),
    },
    {
        "zh_name": "农业朗姆",
        "en_name": "Rhum Agricole",
        "category": "material",
        "description": (
            "以甘蔗汁为原料的法属马提尼克朗姆酒，AOC 法定产区，"
            "带有清新草香，代表品牌 Rhum Clément、Neisson，"
            "是高端热带鸡尾酒的优选基酒。"
        ),
    },
    {
        "zh_name": "白朗姆",
        "en_name": "White Rum",
        "category": "material",
        "description": (
            "未陈年或短暂陈年的朗姆酒，清爽轻盈，是莫吉托、"
            "戴基里、椰林飘香的核心原料，代表品牌百加得、"
            "哈瓦那俱乐部，是热带鸡尾酒最常用的朗姆类型。"
        ),
    },
    {
        "zh_name": "金朗姆",
        "en_name": "Gold Rum",
        "category": "material",
        "description": (
            "橡木桶陈年 1-3 年的朗姆酒，琥珀色，风味平衡，"
            "常用于热带鸡尾酒，代表品牌百加得 Gold、苹果顿 "
            "Vatted，是莫吉托变体与黑暗风暴的过渡选择。"
        ),
    },
    {
        "zh_name": "黑朗姆",
        "en_name": "Dark Rum",
        "category": "material",
        "description": (
            "深度陈年或加焦糖调色的朗姆酒，浓郁厚重，是朗姆"
            "可乐、自由古巴、黑暗风暴的核心，代表品牌 Myers's、"
            "Gosling's Black Seal，赋予鸡尾酒深沉色泽与风味。"
        ),
    },
    {
        "zh_name": "龙舌兰陈年",
        "en_name": "Anejo Tequila",
        "category": "material",
        "description": (
            "橡木桶陈年 1-3 年的龙舌兰酒，琥珀色，带有橡木香"
            "与香草感，适合纯饮与高端鸡尾酒，代表品牌 Don "
            "Julio、Patron，是陈年龙舌兰入门级别。"
        ),
    },
    {
        "zh_name": "龙舌兰银",
        "en_name": "Blanco Tequila",
        "category": "material",
        "description": (
            "未陈年或陈年不足 2 个月的龙舌兰酒，纯净龙舌兰香，"
            "是玛格丽特首选，代表品牌 Patron Silver、Don Julio "
            "Blanco，展现龙舌兰植物本味的清新风格。"
        ),
    },
    {
        "zh_name": "龙舌兰微陈",
        "en_name": "Reposado Tequila",
        "category": "material",
        "description": (
            "橡木桶陈年 2-12 个月的龙舌兰酒，金色，平衡了纯净"
            "与陈年感，代表品牌 Hornitos、Casamigos，是玛格丽特"
            "与帕洛玛的进阶选择。"
        ),
    },
    {
        "zh_name": "君度",
        "en_name": "Cointreau",
        "category": "material",
        "description": (
            "法国橙味利口酒，1849 年创立，是玛格丽特、大都会、"
            "白色佳人、侧车的核心原料，酒精度 40%，橙香纯净"
            "平衡，是橙味利口酒的行业标杆。"
        ),
    },
    {
        "zh_name": "卡帕诺",
        "en_name": "Carpano",
        "category": "material",
        "description": (
            "意大利味美思品牌，味美思发明者 Antonio Benedetto "
            "Carpano 于 1786 年都灵创立，Antica Formula 是顶级"
            "甜味美思代表，是尼格罗尼、曼哈顿的高端选择。"
        ),
    },
    {
        "zh_name": "金巴利",
        "en_name": "Campari",
        "category": "material",
        "description": (
            "意大利苦味利口酒，1860 年米兰 Gaspare Campari 发明，"
            "鲜红色苦甜风味，是尼格罗尼、美式咖啡、罗伯罗伊"
            "变体的核心原料，也是 Spritz 系列代表。"
        ),
    },
    {
        "zh_name": "安高天娜",
        "en_name": "Angostura",
        "category": "material",
        "description": (
            "委内瑞拉/特立尼达生产的芳香苦精，1824 年医生 "
            "Johann Siegert 发明，全球最畅销苦精，标签过大是"
            "品牌标志，是古典、曼哈顿、尼格罗尼的必备苦精。"
        ),
    },
    {
        "zh_name": "佩肖德",
        "en_name": "Peychaud's",
        "category": "material",
        "description": (
            "新奥尔良 Sazerac 公司生产的苦精，1830 年药剂师 "
            "Antoine Peychaud 创制，茴香樱桃调、浅红色，是"
            "萨泽拉克鸡尾酒的核心苦精。"
        ),
    },
    {
        "zh_name": "查特绿",
        "en_name": "Chartreuse Verte",
        "category": "material",
        "description": (
            "法国卡尔特教派秘方草药利口酒，55% 酒精度，130 种"
            "草药复杂风味，配方至今保密，是 Last Word、Chartreuse "
            "Swipe 等配方的核心。"
        ),
    },
    {
        "zh_name": "查特黄",
        "en_name": "Chartreuse Jaune",
        "category": "material",
        "description": (
            "查特绿的温和版本，40% 酒精度，甜润芳香，适合餐后"
            "纯饮或调制鸡尾酒，是查特系列中更易饮用的版本，"
            "配方同样由卡尔特教派僧侣保密传承。"
        ),
    },
    {
        "zh_name": "百利甜",
        "en_name": "Baileys Irish Cream",
        "category": "material",
        "description": (
            "爱尔兰奶油利口酒，1974 年诞生，丝滑浓郁，常用于 "
            "B-52 分层或咖啡鸡尾酒，是奶油利口酒的代表品牌，"
            "酒精度 17%，需冷藏保存。"
        ),
    },
    {
        "zh_name": "迪萨罗诺",
        "en_name": "Disaronno",
        "category": "material",
        "description": (
            "意大利杏仁味利口酒，深琥珀色，杏仁香气明显，"
            "是教父、烘烤杏仁等鸡尾酒的核心，1525 年配方起源，"
            "酒精度 28%，可纯饮或调酒。"
        ),
    },
    {
        "zh_name": "加利亚诺",
        "en_name": "Galliano",
        "category": "material",
        "description": (
            "意大利香草利口酒，金黄高瓶身，香草茴香风味，"
            "是哈维撞墙者、Yellow Bird 等配方的核心，酒精度 "
            "42.3%，1896 年 Arturo Vaccari 创制。"
        ),
    },
    {
        "zh_name": "德兰布依",
        "en_name": "Drambuie",
        "category": "material",
        "description": (
            "苏格兰威士忌加蜂蜜加香料的利口酒，源于 1746 年 "
            "Bonnie Prince Charlie 配方，甜润复杂，是锈钉 "
            "Rusty Nail 的核心原料，酒精度 40%。"
        ),
    },
    {
        "zh_name": "圣日耳曼",
        "en_name": "Saint Germain",
        "category": "material",
        "description": (
            "法国接骨木花利口酒，花香清新，是现代调酒中花香"
            "元素的代表，2007 年首次进口美国，用于 Elderflower "
            "Spritz、仙黛丽等配方，酒精度 20%。"
        ),
    },
    {
        "zh_name": "卡鲁瓦",
        "en_name": "Kahlua",
        "category": "material",
        "description": (
            "墨西哥咖啡利口酒，咖啡香浓郁，是黑俄罗斯、白俄罗斯、"
            "B-52、爱尔回声的核心原料，酒精度 20%，1936 年诞生，"
            "全球最畅销咖啡利口酒。"
        ),
    },
    {
        "zh_name": "提亚玛丽亚",
        "en_name": "Tia Maria",
        "category": "material",
        "description": (
            "牙买加咖啡利口酒，比卡鲁瓦更干爽，带有牙买加朗姆酒底，"
            "是咖啡鸡尾酒的替代选择，1940 年代配方，使用蓝山咖啡"
            "豆与香草，酒精度 20%。"
        ),
    },
    {
        "zh_name": "柑曼怡",
        "en_name": "Grand Marnier",
        "category": "material",
        "description": (
            "法国橙味利口酒，干邑加橙皮，比君度更厚重，是经典"
            "法式橙味利口酒代表，1880 年创立，用于 Sidecar 变体、"
            "B-52 顶层及多种高端鸡尾酒。"
        ),
    },
    {
        "zh_name": "香博",
        "en_name": "Chambord",
        "category": "material",
        "description": (
            "法国覆盆子利口酒，黑紫色，覆盆子香浓郁，是法兰西 75、"
            "少女杀手、玛格丽特变体等配方常用，酒精度 16.5%，"
            "灵感源自 17 世纪路易十四宫廷配方。"
        ),
    },
    {
        "zh_name": "三秒",
        "en_name": "Triple Sec",
        "category": "material",
        "description": (
            "通用橙味利口酒类型，比君度便宜，是多种鸡尾酒的橙味"
            "利口酒替代选择，酒精度 15-40%，源于 19 世纪法国，"
            "用于长岛冰茶、玛格丽特等配方。"
        ),
    },
    {
        "zh_name": "蓝柑橘",
        "en_name": "Blue Curacao",
        "category": "material",
        "description": (
            "蓝色橙味利口酒，添加食用色素赋予鸡尾酒蓝色，是蓝色"
            "夏威夷、蓝色潟湖、B-52 变体的核心原料，酒精度 21%，"
            "源自加勒比库拉索岛。"
        ),
    },
    {
        "zh_name": "椰子利口酒",
        "en_name": "Malibu",
        "category": "material",
        "description": (
            "椰子味朗姆利口酒，21% 酒精度，椰香浓郁，是椰林飘香、"
            "马利布可乐等配方的核心原料，1980 年代诞生于牙买加，"
            "易饮性强适合长饮。"
        ),
    },
    {
        "zh_name": "阿玛雷托",
        "en_name": "Amaretto",
        "category": "material",
        "description": (
            "杏仁味利口酒统称，意大利产，甜美杏仁香，常用于教父、"
            "烘烤杏仁等配方，代表品牌 Disaronno、Lazzaroni，"
            "酒精度 28%，源自 Saronno 镇。"
        ),
    },
    {
        "zh_name": "黑刺李金酒",
        "en_name": "Sloe Gin",
        "category": "material",
        "description": (
            "黑刺李果实浸泡的金酒，红色甜美，是经典鸡尾酒 Sloe "
            "Gin Fizz、Sloe Screwdriver 的核心原料，酒精度 "
            "25-30%，英国传统利口酒。"
        ),
    },
    {
        "zh_name": "玛拉斯奇诺",
        "en_name": "Maraschino",
        "category": "material",
        "description": (
            "克罗地亚樱桃核利口酒，清澈微甜带有杏仁香，是经典 "
            "Aviation、Hemingway Special、 Martinez 的核心原料，"
            "代表品牌 Luxardo，1760 年 Drioli 家族创制。"
        ),
    },
    {
        "zh_name": "比灵列",
        "en_name": "Benedictine",
        "category": "material",
        "description": (
            "法国诺曼底本笃会利口酒，1510 年修士 Don Bernardo "
            "Vincelli 发明，27 种草药香料复杂风味，是 B&B、"
            "Singapore Sling 的核心原料，酒精度 40%。"
        ),
    },
    {
        "zh_name": "阿佩罗",
        "en_name": "Aperol",
        "category": "material",
        "description": (
            "意大利苦味开胃酒，橙红色，苦甜带大黄与橙香，酒精度 "
            "11%，是阿佩罗海波 Aperol Spritz 的核心原料，"
            "1919 年 Padua 创立，21 世纪全球流行。"
        ),
    },
    {
        "zh_name": "味美思",
        "en_name": "Vermouth",
        "category": "material",
        "description": (
            "以白葡萄酒为基底加入苦艾等草药浸泡并加强的芳香"
            "葡萄酒，酒精度 15-22%，是马天尼、曼哈顿、尼格罗尼"
            "的核心原料，分干、甜、白三类。"
        ),
    },
    {
        "zh_name": "干味美思",
        "en_name": "Dry Vermouth",
        "category": "material",
        "description": (
            "白色含糖低的味美思，清爽带草本苦味，法国风格代表，"
            "是马天尼的核心原料，代表品牌 Noilly Prat、Dolin，"
            "开瓶后需冷藏并尽快饮用。"
        ),
    },
    {
        "zh_name": "甜味美思",
        "en_name": "Sweet Vermouth",
        "category": "material",
        "description": (
            "红色或琥珀色含糖高的味美思，意大利风格代表，是"
            "曼哈顿、尼格罗尼、罗伯罗伊的核心原料，代表品牌 "
            "Carpano Antica Formula、Cinzano。"
        ),
    },
    {
        "zh_name": "白味美思",
        "en_name": "Bianco Vermouth",
        "category": "material",
        "description": (
            "介于干与甜之间的浅金色味美思，香草甜感明显，"
            "适合餐前纯饮或调制鸡尾酒，代表品牌 Martini Bianco、"
            "Cinzano Bianco，是温和风格的味美思。"
        ),
    },
    {
        "zh_name": "利莱",
        "en_name": "Lillet",
        "category": "material",
        "description": (
            "法国波尔多产的开胃酒，类似味美思但更果香，分 "
            "Lillet Blanc、Lillet Rouge，是 Vesper、Corpse "
            "Reviver No.2 的核心原料，含少量奎宁。"
        ),
    },
    {
        "zh_name": "仙山露",
        "en_name": "Cinzano",
        "category": "material",
        "description": (
            "意大利味美思品牌，1757 年都灵创立，分干、甜、白"
            "三类，是马天尼品牌的传统竞争对手，用于多种经典"
            "鸡尾酒，性价比高。"
        ),
    },
    {
        "zh_name": "马天尼味美思",
        "en_name": "Martini Vermouth",
        "category": "material",
        "description": (
            "意大利味美思品牌，1863 年都灵创立，全球最畅销"
            "味美思，注意与鸡尾酒马天尼区分，分 Martini Extra "
            "Dry、Rosso、Bianco 等系列。"
        ),
    },
    {
        "zh_name": "多林",
        "en_name": "Dolin",
        "category": "material",
        "description": (
            "法国尚贝里产区的味美思品牌，干型代表，是法式"
            "味美思风格的标杆，Dolin Dry、Dolin Rouge、Dolin "
            "Blanc 三系列，性价比与品质兼具。"
        ),
    },
    {
        "zh_name": "诺利帕特",
        "en_name": "Noilly Prat",
        "category": "material",
        "description": (
            "法国味美思品牌，1813 年创立，干型风格奠基者，"
            "是法式干味美思的鼻祖，使用白葡萄酒在橡木桶陈酿"
            "2 年后加草药浸泡，是高端马天尼的优选。"
        ),
    },
    {
        "zh_name": "苦艾酒",
        "en_name": "Absinthe",
        "category": "material",
        "description": (
            "高酒精度茴香甜烈酒，曾禁酿百年，是萨泽拉克洗杯、"
            "经典 Sazerac、Corpse Reviver No.2 的核心原料，"
            "酒精度 45-74%，绿色仙女之名传世。"
        ),
    },
    {
        "zh_name": "单糖浆",
        "en_name": "Simple Syrup",
        "category": "material",
        "description": (
            "白糖与水 1:1 加热溶解的最常用糖浆，高档做法用 "
            "2:1 rich simple syrup 更甜更稠，是鸡尾酒甜化"
            "的核心原料，常温可存 1-2 周。"
        ),
    },
    {
        "zh_name": "蜂蜜糖浆",
        "en_name": "Honey Syrup",
        "category": "material",
        "description": (
            "蜂蜜与水 1:1 稀释的糖浆，纯蜂蜜难以混合，可加"
            "少许柠檬汁防腐，是 Bee's Knees、布朗德宾等配方的"
            "甜味剂，冷藏保存 2-3 周。"
        ),
    },
    {
        "zh_name": "枫糖浆",
        "en_name": "Maple Syrup",
        "category": "material",
        "description": (
            "加拿大特产糖浆，1:1 稀释，赋予鸡尾酒焦糖木质感，"
            "是威士忌基酒的特色甜味剂，用于 Maple Old Fashioned、"
            "Whiskey Sour 变体等配方。"
        ),
    },
    {
        "zh_name": "石榴糖浆",
        "en_name": "Grenadine",
        "category": "material",
        "description": (
            "红色石榴糖浆，酸甜染色，是龙舌兰日出、雪莉坦普尔、"
            "Jack Rose 的核心原料，优质产品使用真实石榴汁，"
            "劣质品用人工色素与香精。"
        ),
    },
    {
        "zh_name": "水果糖浆",
        "en_name": "Fruit Syrup",
        "category": "material",
        "description": (
            "水果与糖熬煮过滤的糖浆，如覆盆子糖浆、黑莓糖浆，"
            "赋予鸡尾酒果香与色彩，是 Clover Club、罗丝等"
            "配方的甜味与色泽来源。"
        ),
    },
    {
        "zh_name": "肉桂糖浆",
        "en_name": "Cinnamon Syrup",
        "category": "material",
        "description": (
            "肉桂棒煮制的糖浆，辛香温暖，用于 Tiki 风格与"
            "冬季热饮鸡尾酒，是 Autumn Old Fashioned、"
            "Hot Buttered Rum 的特色甜味剂。"
        ),
    },
    {
        "zh_name": "生姜糖浆",
        "en_name": "Ginger Syrup",
        "category": "material",
        "description": (
            "新鲜姜煮制的糖浆，辛辣提神，用于吉姆雷特、莫斯科"
            "骡子变体等配方，也是 Ginger Margarita 等现代"
            "鸡尾酒的核心甜味剂。"
        ),
    },
    {
        "zh_name": "焦糖糖浆",
        "en_name": "Demerara Syrup",
        "category": "material",
        "description": (
            "使用德梅拉拉糖的焦糖风味糖浆，是 Old Fashioned "
            "经典用糖，带有焦糖木质感，2:1 比例浓稠，赋予"
            "鸡尾酒深沉色泽与风味。"
        ),
    },
    {
        "zh_name": "椰浆",
        "en_name": "Coconut Cream",
        "category": "material",
        "description": (
            "浓稠的椰子乳制品替代品，是椰林飘香、查塔努加"
            "的核心原料，赋予浓郁椰香，椰青汁与椰浆比例影响"
            "口感浓稠度。"
        ),
    },
    {
        "zh_name": "蛋白",
        "en_name": "Egg White",
        "category": "material",
        "description": (
            "鸡尾酒用的鸡蛋白，增加绵密泡沫质感，是威士忌酸、"
            "皮斯科酸、克莱帕克的核心，需干摇起泡，提供丝滑"
            "口感与视觉层次。"
        ),
    },
    {
        "zh_name": "全蛋",
        "en_name": "Whole Egg",
        "category": "material",
        "description": (
            "鸡尾酒用的整颗鸡蛋，是 Flip 类鸡尾酒如雪莉 Flip、"
            "亚历山大、Golden Cadillac 的核心原料，提供醇厚"
            "蛋香与绵密质感。"
        ),
    },
    {
        "zh_name": "奶油",
        "en_name": "Heavy Cream",
        "category": "material",
        "description": (
            "浓稠奶油，是奶油鸡尾酒如亚历山大、白俄罗斯、"
            "Grasshopper 的核心，赋予丝滑口感，需当天使用"
            "避免隔夜变质。"
        ),
    },
    {
        "zh_name": "苏打水",
        "en_name": "Club Soda",
        "category": "material",
        "description": (
            "无味碳酸水，用于稀释与增加气泡，是海波、汤姆"
            "柯林斯、莫吉托的常用辅料，提供清爽气泡感，"
            "也用于清洁载杯。"
        ),
    },
    {
        "zh_name": "汤力水",
        "en_name": "Tonic Water",
        "category": "material",
        "description": (
            "含奎宁的苦甜碳酸水，是金汤力、伏特加汤力的核心"
            "辅料，带有特色苦味，源自英国殖民印度的抗疟疾"
            "药饮，现代有无糖版本。"
        ),
    },
    {
        "zh_name": "姜啤",
        "en_name": "Ginger Beer",
        "category": "material",
        "description": (
            "辛辣碳酸饮料，比姜汁汽水更浓烈，是莫斯科骡子、"
            "黑暗风暴的核心辅料，发酵型姜啤风味更复杂，"
            "代表品牌 Fever-Tree、Fentimans。"
        ),
    },
    {
        "zh_name": "姜汁汽水",
        "en_name": "Ginger Ale",
        "category": "material",
        "description": (
            "温和姜味碳酸饮料，比姜啤清淡，是威士忌海波、"
            "长老会、Snapper 等配方的辅料，代表品牌 Canada "
            "Dry、Schweppes，适合清淡长饮。"
        ),
    },
    {
        "zh_name": "可乐",
        "en_name": "Cola",
        "category": "material",
        "description": (
            "甜苦碳酸饮料，是朗姆可乐、自由古巴、长老会的"
            "核心辅料，可口可乐与百事可乐为主，赋予鸡尾酒"
            "焦糖色泽与可乐特有风味。"
        ),
    },
    {
        "zh_name": "柠檬汁",
        "en_name": "Lemon Juice",
        "category": "material",
        "description": (
            "黄色柠檬榨汁，酸度约 5-6%，是鸡尾酒第一酸源，"
            "威士忌酸、戴基里、汤姆柯林斯的核心酸源，建议"
            "现榨现用以保留鲜活酸度。"
        ),
    },
    {
        "zh_name": "青柠汁",
        "en_name": "Lime Juice",
        "category": "material",
        "description": (
            "青柠榨汁，酸度更高更清冽，是莫吉托、玛格丽特、"
            "戴基里的核心酸源，比柠檬汁更尖锐明亮，建议"
            "现榨现用。"
        ),
    },
    {
        "zh_name": "橙汁",
        "en_name": "Orange Juice",
        "category": "material",
        "description": (
            "鲜榨橙汁，酸甜平衡，是螺丝刀、含羞草、龙舌兰"
            "日出的核心辅料，建议鲜榨保留鲜活果香，是早午餐"
            "鸡尾酒的标准配料。"
        ),
    },
    {
        "zh_name": "西柚汁",
        "en_name": "Grapefruit Juice",
        "category": "material",
        "description": (
            "西柚榨汁，苦甜酸复杂风味，是帕洛玛、海风、"
            "棕榈树下的核心辅料，红宝石西柚汁色泽美观，"
            "苦味与龙舌兰搭配绝佳。"
        ),
    },
    {
        "zh_name": "蔓越莓汁",
        "en_name": "Cranberry Juice",
        "category": "material",
        "description": (
            "红色酸甜果汁，是大都会、海风、鳕鱼角的核心"
            "辅料，赋予鸡尾酒红色泽与酸甜果香，是 90 年代"
            "Cosmopolitan 风潮的关键原料。"
        ),
    },
    {
        "zh_name": "番茄汁",
        "en_name": "Tomato Juice",
        "category": "material",
        "description": (
            "咸鲜果汁，是血腥玛丽、红盲人、米勒拉特的核心"
            "辅料，搭配各种香料调味，是早午餐咸鲜鸡尾酒"
            "的标志性原料。"
        ),
    },
    {
        "zh_name": "菠萝汁",
        "en_name": "Pineapple Juice",
        "category": "material",
        "description": (
            "热带果汁，甜酸芳香，是椰林飘香、新加坡司令、"
            "Scorpion 的核心辅料，赋予鸡尾酒热带果香，"
            "也是 Tiki 鸡尾酒的基础原料。"
        ),
    },
    {
        "zh_name": "苹果酒",
        "en_name": "Apple Cider",
        "category": "material",
        "description": (
            "苹果发酵酒，酒精度低，是秋季热饮与苹果鸡尾酒"
            "的常用原料，用于 Apple Toddy、Stone Fence "
            "等配方，新鲜未过滤版本风味更佳。"
        ),
    },
    {
        "zh_name": "啤酒",
        "en_name": "Beer",
        "category": "material",
        "description": (
            "麦芽发酵酒，酒精度 4-8%，部分鸡尾酒如深色 Stout "
            "啤酒、拉德勒、Black Velvet 等使用，也是啤酒"
            "炸弹类混合饮品的核心。"
        ),
    },
    {
        "zh_name": "香槟",
        "en_name": "Champagne",
        "category": "material",
        "description": (
            "法国香槟产区起泡酒，酒精度 12-12.5%，是香槟"
            "鸡尾酒、含羞草、法兰西 75、Black Velvet 的核心"
            "原料，传统法酿造气泡细腻持久。"
        ),
    },
    {
        "zh_name": "普罗塞克",
        "en_name": "Prosecco",
        "category": "material",
        "description": (
            "意大利起泡酒，比香槟便宜，是阿佩罗海波、含羞草、"
            "贝里尼的常用替代，Charmat 法酿造果香清新，"
            "是现代 Spritz 风潮的核心。"
        ),
    },
    {
        "zh_name": "薄荷",
        "en_name": "Mint",
        "category": "material",
        "description": (
            "新鲜薄荷叶，捣压或装饰，是莫吉托、薄荷朱莉普、"
            "南方薄荷的核心原料，捣压释放香气需轻柔避免"
            "苦味，也是多种鸡尾酒的装饰。"
        ),
    },
    {
        "zh_name": "柑橘皮",
        "en_name": "Citrus Peel",
        "category": "material",
        "description": (
            "柠檬、橙、青柠等柑橘类外皮，扭成螺旋释放精油"
            "装饰，是马天尼、古典的标志性装饰，削皮需避开"
            "白色苦味海绵层。"
        ),
    },
    {
        "zh_name": "酒渍樱桃",
        "en_name": "Brandied Cherry",
        "category": "material",
        "description": (
            "鸡尾酒装饰用酒渍樱桃，常浸泡在马拉斯奇诺或"
            "白兰地中，是曼哈顿、古典、Aviation 的经典装饰，"
            "Luxardo 是高端代表。"
        ),
    },
    {
        "zh_name": "橄榄",
        "en_name": "Olive",
        "category": "material",
        "description": (
            "鸡尾酒装饰用绿橄榄，常串在签子上，是干马天尼"
            "的标志性咸鲜装饰，带核橄榄更经典，也可填芝士"
            "或蒜蓉增加风味。"
        ),
    },
    {
        "zh_name": "肉桂棒",
        "en_name": "Cinnamon Stick",
        "category": "material",
        "description": (
            "肉桂棒装饰或搅拌，温暖辛香，是热饮鸡尾酒如"
            "爱尔兰咖啡、托迪、Hot Buttered Rum 的装饰，"
            "也可煮制肉桂糖浆。"
        ),
    },
    {
        "zh_name": "豆蔻",
        "en_name": "Cardamom",
        "category": "material",
        "description": (
            "小豆蔻香料，整颗或粉末用于热饮鸡尾酒、Tiki "
            "鸡尾酒，辛香樟脑感，是部分咖哩鸡尾酒与印度"
            "风味鸡尾酒的特色香料。"
        ),
    },
    {
        "zh_name": "茴香",
        "en_name": "Anise",
        "category": "material",
        "description": (
            "茴香香料或茴香利口酒，是苦艾酒、Pastis、Ouzo "
            "等茴香甜酒的核心风味，也是部分 Tiki 与经典"
            "鸡尾酒的调味香料。"
        ),
    },
    {
        "zh_name": "香草荚",
        "en_name": "Vanilla Pod",
        "category": "material",
        "description": (
            "香草豆荚，浸泡或煮制糖浆，赋予鸡尾酒温润"
            "香草甜感，是奶油鸡尾酒常用，马达加斯加与"
            "塔希提香草荚是高端选择。"
        ),
    },

    # ====================================================================
    # 配方 recipe（50 条）
    # ====================================================================
    {
        "zh_name": "马天尼",
        "en_name": "Martini",
        "category": "recipe",
        "description": (
            "IBA 经典鸡尾酒之王，金酒加干味美思搅拌滤冰，"
            "柠檬皮或橄榄装饰，是 Stir 技法的标杆，被誉为"
            "鸡尾酒之王，配比与装饰争议百年不绝。"
        ),
    },
    {
        "zh_name": "曼哈顿",
        "en_name": "Manhattan",
        "category": "recipe",
        "description": (
            "IBA 经典，黑麦威士忌加甜味美思加安高天娜苦精"
            "搅拌，樱桃装饰，是 Stir 技法的代表，1874 年"
            "纽约曼哈顿俱乐部发明。"
        ),
    },
    {
        "zh_name": "尼格罗尼",
        "en_name": "Negroni",
        "category": "recipe",
        "description": (
            "IBA 经典，金酒加金巴利加甜味美思等比搅拌，"
            "橙皮装饰，苦甜平衡的意大利代表，1919 年佛罗伦萨"
            "Caffè Casoni 诞生。"
        ),
    },
    {
        "zh_name": "大都会",
        "en_name": "Cosmopolitan",
        "category": "recipe",
        "description": (
            "IBA 经典，伏特加加君度加蔓越莓汁加青柠汁摇和，"
            "是 90 年代纽约时尚鸡尾酒代表，因《欲望都市》"
            "剧集风靡全球。"
        ),
    },
    {
        "zh_name": "莫吉托",
        "en_name": "Mojito",
        "category": "recipe",
        "description": (
            "IBA 经典，白朗姆加薄荷加青柠加糖加苏打，是古巴"
            "高球代表，捣压技法的标杆，海明威在哈瓦那 Bodeguita "
            "del Medio 推广。"
        ),
    },
    {
        "zh_name": "玛格丽特",
        "en_name": "Margarita",
        "category": "recipe",
        "description": (
            "IBA 经典，龙舌兰加君度加青柠汁摇和盐边，是墨西哥"
            "国饮，酸咸平衡，1948 年达拉斯社交名媛 Margarita "
            "Sames 创制传说流传最广。"
        ),
    },
    {
        "zh_name": "戴基里",
        "en_name": "Daiquiri",
        "category": "recipe",
        "description": (
            "IBA 经典，白朗姆加青柠汁加单糖浆摇和，是古巴"
            "酸酒代表，海明威最爱的鸡尾酒之一，1898 年美国"
            "工程师 Jennings Cox 在古巴创制。"
        ),
    },
    {
        "zh_name": "古典鸡尾酒",
        "en_name": "Old Fashioned",
        "category": "recipe",
        "description": (
            "IBA 经典，威士忌加糖加安高天娜苦精加冰兑和，"
            "橙皮与樱桃装饰，是 Build 技法的标杆，肯塔基"
            "赛马官方饮品。"
        ),
    },
    {
        "zh_name": "威士忌酸",
        "en_name": "Whiskey Sour",
        "category": "recipe",
        "description": (
            "IBA 经典，波本加柠檬汁加单糖浆加蛋白摇和，"
            "是酸酒类的代表，干摇技法典型，1862 年 Jerry "
            "Thomas《How to Mix Drinks》首次记录。"
        ),
    },
    {
        "zh_name": "血腥玛丽",
        "en_name": "Bloody Mary",
        "category": "recipe",
        "description": (
            "IBA 经典，伏特加加番茄汁加柠檬汁加各种香料"
            "兑和，是早午餐经典咸鲜鸡尾酒，1920 年代巴黎 "
            "Harry's New York Bar 调酒师 Fernand Petiot 创制。"
        ),
    },
    {
        "zh_name": "螺丝刀",
        "en_name": "Screwdriver",
        "category": "recipe",
        "description": (
            "IBA 经典，伏特加加橙汁兑和，简单清爽，是早午餐"
            "与休闲场合的长饮代表，据说源自美国石油工人"
            "用螺丝刀搅拌伏特加与橙汁。"
        ),
    },
    {
        "zh_name": "金汤力",
        "en_name": "Gin and Tonic",
        "category": "recipe",
        "description": (
            "经典高球，金酒加汤力水兑和，青柠装饰，是英国"
            "殖民印度的经典饮品，奎宁抗疟疾药饮演变而来，"
            "最易入门的鸡尾酒。"
        ),
    },
    {
        "zh_name": "莫斯科骡子",
        "en_name": "Moscow Mule",
        "category": "recipe",
        "description": (
            "IBA 经典，伏特加加姜啤加青柠汁兑和，铜杯盛装，"
            "是 1940 年代美国 Smirnoff 营销创意，铜杯导热"
            "使饮品更冰凉。"
        ),
    },
    {
        "zh_name": "自由古巴",
        "en_name": "Cuba Libre",
        "category": "recipe",
        "description": (
            "IBA 经典，白朗姆加可乐加青柠兑和，是古巴独立"
            "战争的纪念鸡尾酒，1900 年代哈瓦那美国士兵"
            "庆祝独立时创制。"
        ),
    },
    {
        "zh_name": "龙舌兰日出",
        "en_name": "Tequila Sunrise",
        "category": "recipe",
        "description": (
            "IBA 经典，龙舌兰加橙汁加红石榴糖浆分层，色彩"
            "如日出渐变，是 70 年代摇滚代表，Rolling Stones "
            "1972 年巡回演出带火。"
        ),
    },
    {
        "zh_name": "椰林飘香",
        "en_name": "Pina Colada",
        "category": "recipe",
        "description": (
            "IBA 经典，白朗姆加椰浆加菠萝汁摇和或搅拌，"
            "是波多黎各国饮，热带鸡尾酒代表，1954 年圣胡安 "
            "Caribe Hilton 调酒师 Ramon Portas Mingot 创制。"
        ),
    },
    {
        "zh_name": "汤姆柯林斯",
        "en_name": "Tom Collins",
        "category": "recipe",
        "description": (
            "IBA 经典，老汤姆金酒加柠檬汁加糖加苏打兑和，"
            "是 19 世纪伦敦的经典长饮，柯林斯杯以此命名，"
            "1876 年 Jerry Thomas 首次记录配方。"
        ),
    },
    {
        "zh_name": "约翰柯林斯",
        "en_name": "John Collins",
        "category": "recipe",
        "description": (
            "IBA 经典，威士忌加柠檬汁加糖加苏打兑和，是"
            "汤姆柯林斯的威士忌版本，源自伦敦 Limmer's Hotel "
            "侍者 John Collins，使用波本或爱尔兰威士忌。"
        ),
    },
    {
        "zh_name": "边车",
        "en_name": "Sidecar",
        "category": "recipe",
        "description": (
            "IBA 经典，干邑加君度加柠檬汁摇和，糖边装饰，"
            "是两次世界大战间巴黎的经典酸酒，Harry's Bar "
            "调酒师 Harry MacElhone 1923 年首次记录。"
        ),
    },
    {
        "zh_name": "白色佳人",
        "en_name": "White Lady",
        "category": "recipe",
        "description": (
            "IBA 经典，金酒加君度加柠檬汁摇和，是 Harry's "
            "Bar 创始人 Harry MacElhone 1929 年定型的代表作，"
            "比边车更干爽优雅。"
        ),
    },
    {
        "zh_name": "法兰西75",
        "en_name": "French 75",
        "category": "recipe",
        "description": (
            "IBA 经典，金酒加柠檬汁加单糖浆加香槟，以一战"
            "法国 75 毫米炮命名，气泡长饮代表，1915 年巴黎 "
            "Harry's New York Bar 创制。"
        ),
    },
    {
        "zh_name": "含羞草",
        "en_name": "Mimosa",
        "category": "recipe",
        "description": (
            "经典早午餐鸡尾酒，香槟加橙汁等比兑和，是 1925 年"
            "巴黎丽兹饭店的发明，简单优雅，名字源自含羞草花"
            "的黄色。"
        ),
    },
    {
        "zh_name": "贝里尼",
        "en_name": "Bellini",
        "category": "recipe",
        "description": (
            "经典意大利开胃鸡尾酒，普罗塞克加白桃泥兑和，"
            "是 1948 年威尼斯 Harry's Bar 创始人 Giuseppe Cipriani "
            "的发明，以画家 Bellini 命名。"
        ),
    },
    {
        "zh_name": "阿佩罗海波",
        "en_name": "Aperol Spritz",
        "category": "recipe",
        "description": (
            "现代意大利开胃鸡尾酒代表，阿佩罗加普罗塞克加"
            "苏打兑和，3-2-1 比例，是 21 世纪全球流行饮品，"
            "威尼斯 Aperol 酒厂推广。"
        ),
    },
    {
        "zh_name": "萨泽拉克",
        "en_name": "Sazerac",
        "category": "recipe",
        "description": (
            "IBA 经典，干邑或黑麦加方糖加佩肖德苦精加苦艾"
            "洗杯，是新奥尔良的官方鸡尾酒，1850 年代 "
            "Antoine Amedee Peychaud 创制。"
        ),
    },
    {
        "zh_name": "教父",
        "en_name": "Godfather",
        "category": "recipe",
        "description": (
            "IBA 经典，苏格兰威士忌加阿玛雷托兑和加冰，"
            "简单浓烈，是黑帮电影文化的代表饮品，据说"
            "是电影《教父》主角的最爱。"
        ),
    },
    {
        "zh_name": "黑俄罗斯",
        "en_name": "Black Russian",
        "category": "recipe",
        "description": (
            "IBA 经典，伏特加加卡鲁瓦兑和加冰，是 1949 年"
            "布鲁塞尔 Metropole Hotel 调酒师 Gustave Tops "
            "为美国大使创制。"
        ),
    },
    {
        "zh_name": "白俄罗斯",
        "en_name": "White Russian",
        "category": "recipe",
        "description": (
            "黑俄罗斯变种，加奶油漂浮，是科恩兄弟电影"
            "《谋杀绿脚趾》主角 The Dude 的标志性饮品，"
            "60 年代美国流行。"
        ),
    },
    {
        "zh_name": "雪莉坦普尔",
        "en_name": "Shirley Temple",
        "category": "recipe",
        "description": (
            "经典无酒精鸡尾酒，姜汁汽水加红石榴糖浆加"
            "安高天娜，是童星雪莉·坦普尔的纪念饮品，"
            "1930 年代好莱坞餐厅创制。"
        ),
    },
    {
        "zh_name": "B-52",
        "en_name": "B-52",
        "category": "recipe",
        "description": (
            "经典分层鸡尾酒，咖啡利口酒加爱尔兰奶油加"
            "橙味利口酒分层，以美国 B-52 轰炸机命名，"
            "1970 年代加拿大 Ban Springs 调酒师创制。"
        ),
    },
    {
        "zh_name": "爱尔回声",
        "en_name": "Espresso Martini",
        "category": "recipe",
        "description": (
            "现代经典，伏特加加咖啡利口酒加浓缩咖啡加"
            "单糖浆摇和，是伦敦 Soho Brasserie 调酒师 "
            "Dick Bradsell 1983 年应超模要求创制。"
        ),
    },
    {
        "zh_name": "哈维撞墙者",
        "en_name": "Harvey Wallbanger",
        "category": "recipe",
        "description": (
            "IBA 经典，伏特加加橙汁加加利亚诺分层，是 70 年代"
            "加州冲浪文化的代表，调酒师 Donato Duke Antone "
            "1960 年代创制于加州。"
        ),
    },
    {
        "zh_name": "海风",
        "en_name": "Sea Breeze",
        "category": "recipe",
        "description": (
            "IBA 经典，伏特加加西柚汁加蔓越莓汁兑和，是 80 年代"
            "美国休闲饮品代表，红色色泽清爽口感，也是低度"
            "鸡尾酒的流行选择。"
        ),
    },
    {
        "zh_name": "帕洛玛",
        "en_name": "Paloma",
        "category": "recipe",
        "description": (
            "墨西哥国饮代表，龙舌兰加西柚苏打加青柠汁"
            "兑和盐边，是龙舌兰最流行的长饮，比玛格丽特"
            "更日常清爽。"
        ),
    },
    {
        "zh_name": "长岛冰茶",
        "en_name": "Long Island Iced Tea",
        "category": "recipe",
        "description": (
            "高烈度鸡尾酒，伏特加、金酒、朗姆、龙舌兰加君度"
            "加柠檬汁加可乐兑和，茶色但无茶，1972 年长岛 "
            "Oak Beach Inn 调酒师 Robert Butt 创制。"
        ),
    },
    {
        "zh_name": "草莓戴基里",
        "en_name": "Strawberry Daiquiri",
        "category": "recipe",
        "description": (
            "戴基里变种，加草莓摇和或搅拌，常冰沙版本，"
            "是热带度假村的热门鸡尾酒，Frozen Strawberry "
            "Daiquiri 是夏季海滩酒吧的招牌。"
        ),
    },
    {
        "zh_name": "飓风",
        "en_name": "Hurricane",
        "category": "recipe",
        "description": (
            "新奥尔良经典鸡尾酒，朗姆酒加西柚汁加热情果汁"
            "加糖浆摇和，飓风杯盛装，是法国区的代表，"
            "1940 年代 Pat O'Brien's 酒吧创制。"
        ),
    },
    {
        "zh_name": "美式咖啡",
        "en_name": "Americano",
        "category": "recipe",
        "description": (
            "IBA 经典，金巴利加甜味美思加苏打兑和，橙皮装饰，"
            "是尼格罗尼的前身，意大利开胃代表，1860 年代米兰 "
            "Gaspare Campari 创制。"
        ),
    },
    {
        "zh_name": "亚历山大",
        "en_name": "Alexander",
        "category": "recipe",
        "description": (
            "IBA 经典，白兰地加可可利口酒加奶油摇和，是 1920 年代"
            "巧克力甜鸡尾酒的代表作，Hugo Ensslin 1915 年纽约 "
            "Relection's Bar 首次记录。"
        ),
    },
    {
        "zh_name": "薄荷朱莉普",
        "en_name": "Mint Julep",
        "category": "recipe",
        "description": (
            "IBA 经典，波本加薄荷加糖加碎冰捣压兑和，是肯塔基"
            "赛马官方饮品，美国南方传统，银杯盛装是经典呈现。"
        ),
    },
    {
        "zh_name": "银菲士",
        "en_name": "Silver Fizz",
        "category": "recipe",
        "description": (
            "经典酸酒变种，金酒加柠檬汁加糖加蛋白加苏打摇和，"
            "是 Fizz 系列的清爽版本，蛋白赋予绵密泡沫，"
            "1887 年 Jerry Thomas 记录。"
        ),
    },
    {
        "zh_name": "拉莫斯金菲兹",
        "en_name": "Ramos Gin Fizz",
        "category": "recipe",
        "description": (
            "新奥尔良经典，金酒加柠檬青柠汁加糖加蛋白加奶油"
            "加橙花水摇和，需摇 12 分钟，1888 年 Henry C. Ramos "
            "创制，极致绵密泡沫代表。"
        ),
    },
    {
        "zh_name": "克莱帕克",
        "en_name": "Clover Club",
        "category": "recipe",
        "description": (
            "IBA 经典 Pre-Prohibition 鸡尾酒，金酒加柠檬汁"
            "加覆盆子糖浆加蛋白摇和，粉红色泽，费城绅士俱乐部"
            "1896 年创制。"
        ),
    },
    {
        "zh_name": "航空",
        "en_name": "Aviation",
        "category": "recipe",
        "description": (
            "IBA 经典，金酒加玛拉斯奇诺加紫罗兰利口酒加柠檬汁"
            "摇和，淡蓝紫色，是 Pre-Prohibition 优雅代表，"
            "1916 年 Hugo Ensslin 首次记录。"
        ),
    },
    {
        "zh_name": "卡琵林尼亚",
        "en_name": "Caipirinha",
        "category": "recipe",
        "description": (
            "IBA 经典，卡夏萨加青柠加糖捣压，是巴西国饮，"
            "muddle 技法的标杆，与莫吉托同为捣压类鸡尾酒"
            "代表，使用卡夏萨而非朗姆酒。"
        ),
    },
    {
        "zh_name": "玛提尼兹",
        "en_name": "Martinez",
        "category": "recipe",
        "description": (
            "IBA 经典，金酒加甜味美思加玛拉斯奇诺加橙味"
            "苦精摇和，是马天尼的祖先，19 世纪加州发明，"
            "Jerry Thomas 1887 年首次记录。"
        ),
    },
    {
        "zh_name": "锈钉",
        "en_name": "Rusty Nail",
        "category": "recipe",
        "description": (
            "IBA 经典，苏格兰威士忌加德兰布依兑和加冰，"
            "是苏格兰鸡尾酒代表，50 年代纽约 21 Club 创制，"
            "甜润烟熏风味平衡。"
        ),
    },
    {
        "zh_name": "罗伯罗伊",
        "en_name": "Rob Roy",
        "category": "recipe",
        "description": (
            "IBA 经典，苏格兰威士忌加甜味美思加安高天娜"
            "苦精搅拌，是曼哈顿的苏格兰版本，1894 年纽约 "
            "Waldorf Astoria 为音乐剧 Rob Roy 创制。"
        ),
    },
    {
        "zh_name": "新加坡司令",
        "en_name": "Singapore Sling",
        "category": "recipe",
        "description": (
            "IBA 经典，金酒加樱桃白兰地加君度加比内迪克汀"
            "加菠萝汁加柠檬汁摇和，是新加坡莱佛士酒店 "
            "Long Bar 1915 年调酒师 Ngiam Tong Boon 创制。"
        ),
    },
]


def build_glossary() -> dict[str, Any]:
    """构建并导入术语对照表到知识库。

    幂等：通过 source_id="glossary:<en_name>" 去重，已存在则跳过。
    每条作为一个独立的 Document，category="encyclopedia"、
    source="glossary"、source_id="glossary:<en_name>"、
    title="<zh_name> <en_name>"。

    Returns:
        汇总 dict：{"inserted", "skipped", "failed", "items", "total"}。
    """
    from sqlmodel import select

    from hermes_kb.database import get_session
    from hermes_kb.models import Document
    from hermes_kb.rag import ImportService

    importer = ImportService()
    inserted = 0
    skipped = 0
    failed = 0
    items: list[dict[str, Any]] = []

    for entry in GLOSSARY:
        source_id = f"glossary:{entry['en_name']}"
        # 幂等：按 source_id 查重，已存在则跳过
        with get_session() as session:
            existing = session.exec(
                select(Document).where(Document.source_id == source_id)
            ).first()
            if existing:
                skipped += 1
                items.append(
                    {
                        "title": f"{entry['zh_name']} {entry['en_name']}",
                        "status": "skipped",
                        "doc_id": existing.doc_id,
                    }
                )
                continue

        title = f"{entry['zh_name']} {entry['en_name']}"
        content = (
            f"# {entry['zh_name']} {entry['en_name']}\n\n"
            f"**类别**：{entry['category']}\n\n"
            f"{entry['description']}\n"
        )
        try:
            result = importer.import_text(
                content=content,
                title=title,
                source_type="seed",
                file_type="md",
                category="encyclopedia",
                source="glossary",
                source_id=source_id,
                verified=True,
                status="published",
            )
            inserted += 1
            items.append({**result, "status": "imported"})
        except (KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
            failed += 1
            items.append(
                {
                    "title": title,
                    "error": str(e),
                    "status": "failed",
                }
            )

    return {
        "inserted": inserted,
        "skipped": skipped,
        "failed": failed,
        "items": items,
        "total": len(GLOSSARY),
    }


def main() -> int:
    """主入口：导入术语对照表并打印统计。"""
    print("=== 构建中英双语调酒术语对照表 ===")

    # 1. 类别分布统计
    by_cat: dict[str, int] = {}
    for entry in GLOSSARY:
        by_cat[entry["category"]] = by_cat.get(entry["category"], 0) + 1
    print(f"\n词条总数：{len(GLOSSARY)}")
    print("各类别分布：")
    for cat, count in sorted(by_cat.items()):
        print(f"  {cat}: {count}")

    # 2. 导入到知识库
    print("\n=== 导入到知识库 ===")
    result = build_glossary()
    print("\n导入结果：")
    print(f"  新增：{result['inserted']}")
    print(f"  跳过（已存在）：{result['skipped']}")
    print(f"  失败：{result['failed']}")

    # 3. 失败详情
    if result["failed"] > 0:
        print("\n失败详情：")
        for item in result["items"]:
            if item.get("status") == "failed":
                print(f"  - {item.get('title', 'unknown')}: {item.get('error', '')}")

    # 4. 验证：统计 DB 中 glossary 文档总数及各类别分布
    from sqlmodel import func, select

    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    print("\n=== DB 验证 ===")
    with get_session() as session:
        total = session.exec(
            select(func.count(Document.doc_id)).where(Document.source == "glossary")
        ).one()
        print(f"  source='glossary' 文档总数：{total}")

    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
