#!/usr/bin/env python3
"""材料档案库构建脚本。

为 INGREDIENT_REGISTRY 10 大类别代表材料（每类 Top 5）构建详细档案。
档案含 4 要素：生产工艺/主要品牌/产地/风味特征。
以 encyclopedia 类别文档形式存入知识库，source="ingredient_profile"。
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
from sqlmodel import func, select

load_dotenv()

from hermes_kb.database import get_session
from hermes_kb.ingredients import INGREDIENT_REGISTRY
from hermes_kb.models import Document
from hermes_kb.rag import ImportService

# ---------------------------------------------------------------------------
# 材料档案数据：canonical_name -> {production, brands, origin, flavor}
# 内容基于权威来源（Wikipedia/官方酒厂/行业百科）整理。
# 每条：production 50-100 字、brands 3-5 个、origin 国家或地区、flavor 50-100 字。
# ---------------------------------------------------------------------------
PROFILES: dict[str, dict[str, str]] = {
    # === base_spirit 基酒 ===
    "金酒": {
        "production": (
            "以谷物（大麦/黑麦/小麦）为原料发酵蒸馏得到中性烈酒，再用杜松子及芫荽籽、"
            "当归根、柑橘皮等植物香料浸泡或二次蒸馏（复馏法）而成。London Dry 采用复馏，"
            "Old Tom 微甜，新派 Western 弱化杜松子。"
        ),
        "brands": "- Gordon's 哥顿\n- Tanqueray 添加利\n- Beefeater 必富达\n- Hendrick's 亨利爵士\n- Bombay 孟买",
        "origin": "荷兰/英国（起源荷兰，发扬于英国）",
        "flavor": (
            "杜松子为主导的松木、松针香气，伴随芫荽籽的柑橘 spice、当归根的土质麝香与柑橘皮的明亮。"
            "London Dry 干爽清冽，新派带黄瓜玫瑰等创新风味，余韵有植物辛香。"
        ),
    },
    "威士忌": {
        "production": (
            "谷物（大麦/玉米/黑麦/小麦）发芽糖化后发酵，壶式或柱式蒸馏，必须在橡木桶中陈年至少 3 年。"
            "单一麦芽用壶式二次蒸馏，波本用新烧焦美国橡木桶，苏格兰法律要求陈年 ≥3 年。"
        ),
        "brands": "- Johnnie Walker 尊尼获加\n- Glenfiddich 格兰菲迪\n- Macallan 麦卡伦\n- Jim Beam 占边\n- Jameson 尊美醇",
        "origin": "苏格兰/美国/爱尔兰/日本/加拿大",
        "flavor": (
            "麦芽甜、橡木、香草、焦糖为核心，泥煤威士忌带烟熏海盐，波本偏甜润香草，"
            "爱尔兰柔顺轻盈，日本细腻花果。余韵从辛辣到悠长烟熏变化丰富。"
        ),
    },
    "朗姆酒": {
        "production": (
            "以甘蔗糖蜜或甘蔗汁为原料，加入酵母发酵 1-2 天，柱式或壶式蒸馏得到 60-95% 原酒，"
            "白朗姆不陈年或短陈，金/黑朗姆在橡木桶中陈年 1-10 年。农业朗姆用甘蔗汁直酿。"
        ),
        "brands": "- Bacardi 百加得\n- Havana Club 哈瓦那俱乐部\n- Captain Morgan 摩根船长\n- Mount Gay 蒙特盖\n- Appleton Estate 苹果顿",
        "origin": "加勒比海地区（古巴/牙买加/波多黎各/巴巴多斯/马提尼克）",
        "flavor": (
            "甘蔗糖蜜的甜润为基底，带焦糖、太妃糖、热带水果香。白朗姆清爽轻盈，"
            "金朗姆琥珀色带香草，黑朗姆浓郁厚重带烟熏与香料余韵。"
        ),
    },
    "龙舌兰": {
        "production": (
            "仅限使用蓝色龙舌兰（Weber Blue Agave）心部（piña），在砖窑中慢烤 50-72 小时转化糖分，"
            "压榨取汁后发酵 2-7 天，壶式双蒸馏得到约 55% 原酒，按陈年分 Blanco/Reposado/Añejo。"
        ),
        "brands": "- Patrón 培恩\n- Jose Cuervo 豪帅\n- Don Julio 唐胡里奥\n- Herradura 骏马\n- Sauza 紫罗",
        "origin": "墨西哥（哈利斯科州及周边四个州，法定产区）",
        "flavor": (
            "龙舌兰植物的 earthy 草本香为核心，带胡椒、柑橘、矿物质感。Blanco 纯净清新带青辣椒气息，"
            "Reposado 增加香草橡木，Añejo 深邃带焦糖巧克力余韵。"
        ),
    },
    "白兰地": {
        "production": (
            "以葡萄或其他水果为原料，先酿成基酒（9-12% ABV），用夏朗德壶式二次蒸馏得到 60-72% 原酒，"
            "在法国利穆赞橡木桶中陈年至少 2 年，期间挥发出果香并萃取橡木单宁与香草素。"
        ),
        "brands": "- Hennessy 轩尼诗\n- Rémy Martin 人头马\n- Martell 马爹利\n- Courvoisier 拿破仑\n- Camus 卡慕",
        "origin": "法国（干邑 Cognac / 雅文邑 Armagnac）",
        "flavor": (
            "葡萄花、杏、桃子果香为基础，陈年后发展出橡木、香草、檀香、坚果、咖啡、皮革等复合香气。"
            "干邑圆润醇厚，雅文邑更粗犷浓郁，余韵悠长。"
        ),
    },
    # === modifier 辅料 ===
    "味美思": {
        "production": (
            "以白葡萄酒为基底（酒精度 8-12%），加入苦艾（wormwood）及 20-40 种草药、香料（如肉桂、"
            "丁香、芫荽籽、橙皮）浸泡，再加入白兰地或中性酒精提高至 15-22%，陈年 3-12 个月后过滤装瓶。"
        ),
        "brands": "- Martini 马天尼\n- Noilly Prat 诺瓦利帕\n- Cinzano 仙山露\n- Dolin 多林\n- Carpano Antica 卡尔帕诺",
        "origin": "意大利都灵/法国尚贝里",
        "flavor": (
            "干味美思：浅色，花香、青苹果、柑橘、苦艾尾韵；甜味美思：深红色，焦糖、香草、肉桂、"
            "丁香、樱桃果酱；白味美思：香草、八角、甘菊，温润甜柔。"
        ),
    },
    "金巴利": {
        "production": (
            "1860 年意大利米兰 Gaspare Campari 创制。以中性酒精为基底，浸泡约 60 种草药、水果、香料"
            "（包括苦橘皮、茜草根、大黄、龙胆草等），加入焦糖调色，陈酿数月后过滤装瓶。配方至今保密。"
        ),
        "brands": "- Campari 金巴利（唯一原厂品牌）",
        "origin": "意大利米兰",
        "flavor": (
            "鲜红色，苦甜平衡。初闻苦橘皮、樱桃与草药香，入口先甜后苦，带大黄、龙胆的根茎苦韵，"
            "余韵悠长带香料回味。苦度中等，是 Negroni 与 Americano 的灵魂。"
        ),
    },
    "糖浆": {
        "production": (
            "由白糖与水按 1:1（Standard）或 2:1（Rich）比例加热至 80°C 搅拌溶解，冷却后装瓶。"
            "也可冷水摇溶（保留更多蔗糖香气）。高档吧台常用 2:1 Rich Syrup，更甜更稠、稀释影响小。"
        ),
        "brands": "- Monin 莫林\n- Torani 托拉尼\n- DaVinci 达芬奇\n- BG Reynolds\n- Liber & Co.",
        "origin": "全球（无特定产地，调酒基础材料）",
        "flavor": (
            "纯净的蔗糖甜味，无杂味。Standard 偏清淡，Rich 更浓郁粘稠带轻微太妃糖香。"
            "为鸡尾酒提供甜度与圆润口感，是酸甜平衡的基础要素。"
        ),
    },
    "君度": {
        "production": (
            "1849 年法国昂热 Adolphe Cointreau 创制。以甜橙与苦橙皮为原料，"
            "酒精浸泡蒸馏提取橙皮精油，与中性酒精、糖浆调和，最终装瓶 40% ABV。"
            "采用铜壶蒸馏，每批橙皮来自全球（西班牙、巴西、西西里）。"
        ),
        "brands": "- Cointreau 君度（唯一原厂品牌）",
        "origin": "法国昂热（Angers）",
        "flavor": (
            "清澈透明，浓郁的橙皮精油香气，甜橙与苦橙交织。入口先甜后干，带橙皮的白胡椒感与微苦，"
            "余韵清爽。比普通 Triple Sec 更干爽、酒精感更强。"
        ),
    },
    "苦精": {
        "production": (
            "1824 年委内瑞拉医生 Johann Siegert 在特立尼达 Port of Spain 创制。"
            "以高浓度酒精（约 44% ABV）为基底，浸泡龙胆草、肉桂、丁香、肉豆蔻、"
            "茴芹等约十余种草药香料数周，过滤后装瓶。标签过大是品牌标志。"
        ),
        "brands": "- Angostura 安高天娜\n- Peychaud's 佩肖德\n- Fee Brothers 费兄弟\n- The Bitter Truth\n- Bittermens",
        "origin": "委内瑞拉 → 特立尼达和多巴哥（现产地）",
        "flavor": (
            "深褐色，浓郁的肉桂、丁香、肉豆蔻香料感，伴随龙胆草的根茎苦韵。入口苦中带甜，"
            "余韵悠长带烟熏与樟脑。鸡尾酒“调味盐”，几滴即可提升层次。"
        ),
    },
    # === juice 果汁 ===
    "柠檬汁": {
        "production": (
            "黄色柠檬（如 Eureka/Lisbon 品种）鲜榨取汁。商用分 NFC（Not From Concentrate 鲜榨非浓缩）"
            "与还原汁两种。调酒推荐鲜榨：切开柠檬用 citrus juicer 或 hand press 压榨，"
            "过滤去籽，使用前 4 小时内榨取以保留挥发香气。"
        ),
        "brands": "- Santa Cruz Organic\n- Lakewood Organic\n- R.W. Knudsen\n- 365 Everyday Value\n- 海外鲜榨本地品牌",
        "origin": "全球（原产印度东北部，现主产美国加州/西班牙/意大利）",
        "flavor": (
            "明亮清新的柠檬酸，酸度约 5-6%，带柑橘精油香与微苦白瓤味。"
            "是鸡尾酒第一酸源，提供清脆酸度与平衡甜度，Whiskey Sour/Daiquiri 的核心。"
        ),
    },
    "青柠汁": {
        "production": (
            "青柠（Key lime 或 Persian lime）鲜榨取汁。Key Lime 体型小、酸度高、香气浓，"
            "Persian Lime 体型大、酸度温和。调酒推荐鲜榨：切半用 citrus press 压榨，"
            "过滤去籽与果肉，30 分钟内使用以避免氧化变苦。"
        ),
        "brands": "- Lakewood Organic\n- R.W. Knudsen\n- RW Knudson Family\n- Santa Cruz Organic\n- 本地鲜榨",
        "origin": "全球（原产东南亚，现主产墨西哥/巴西/加勒比）",
        "flavor": (
            "比柠檬更清冽的酸度，带独特青草与矿物香气，酸度 6-8%。"
            "Mojito/Margarita/Daiquiri 的灵魂，提供清爽不抢戏的酸度与热带气息。"
        ),
    },
    "橙汁": {
        "production": (
            "甜橙（如 Valencia/Hamlin 品种）鲜榨或冷压取汁。商用分 NFC 鲜榨与浓缩还原两种。"
            "调酒推荐 NFC：橙子切半用 electric juicer 压榨，过滤去果肉，使用前 1 小时内榨取，"
            "避免苦味素（limonin）释出。"
        ),
        "brands": "- Tropicana 果粒橙\n- Minute Maid 美汁源\n- Simply Orange\n- Florida's Natural\n- Innocent",
        "origin": "全球（原产中国/印度东北部，现主产巴西/美国佛罗里达）",
        "flavor": (
            "酸甜平衡的橙香，糖度 10-14°Brix，酸度 1-1.5%。带果肉感的饱满口感与新鲜柑橘精油香。"
            "Screwdriver/Mimosa 的基础，提供甜度与果香。"
        ),
    },
    "蔓越莓汁": {
        "production": (
            "蔓越莓（Vaccinium macrocarpon）鲜果压榨取汁，因纯果汁过酸通常调和为 Cocktail（含糖 25-30%）。"
            "100% 纯汁需与其他果汁调和。商用 Ocean Spray 主导全球市场。调酒推荐 Cocktail 版本以平衡酸甜。"
        ),
        "brands": "- Ocean Spray 优鲜沛\n- Lakewood Organic\n- R.W. Knudsen\n- Northland\n-动态 Native Brands",
        "origin": "北美（美国马萨诸塞/威斯康星/加拿大魁北克）",
        "flavor": (
            "鲜红色，明亮的酸度与明显的甜味（Cocktail 版），带独特的蔓越莓果香与微涩。"
            "Cosmopolitan/Sea Breeze 的核心，提供红色与酸甜基础。"
        ),
    },
    "菠萝汁": {
        "production": (
            "成熟菠萝（如 Smooth Cayenne 品种）去皮压榨取汁，商用分 NFC 与还原汁。"
            "调酒推荐冷压 NFC：菠萝切块用 cold press 榨汁，过滤去纤维。"
            "鲜榨含菠萝蛋白酶（bromelain）可分解蛋白，是少数“活性”果汁。"
        ),
        "brands": "- Dole 都乐\n- Del Monte 地门\n- Lakewood Organic\n- R.W. Knudsen\n- Ceres",
        "origin": "热带（原产巴西/巴拉圭，现主产泰国/菲律宾/哥斯达黎加）",
        "flavor": (
            "浓郁的热带菠萝香，糖度 12-16°Brix，酸度 0.8-1.2%。甜中带酸，"
            "带矿物质与硫化物的复杂气息。Piña Colada 与热带 Tiki 鸡尾酒的核心。"
        ),
    },
    # === garnish 装饰 ===
    "橄榄": {
        "production": (
            "橄榄（Olea europaea）未成熟绿色果实采摘，用盐水（brine）浸泡发酵 6-12 个月去除苦味，"
            "装瓶时加入海盐与香草（如迷迭香/月桂）。Cocktail Olive 选 Manzanilla 或 Castelvetrano 品种，"
            "去核或夹入蓝芝士/大蒜。"
        ),
        "brands": "- Mezzetta\n- Divina\n- Castella\n- Lindsay\n- Musco Family",
        "origin": "地中海（西班牙/意大利/希腊/摩洛哥）",
        "flavor": (
            "咸鲜、微酸、带橄榄果实的油脂感与草本香。Martini 的经典装饰，"
            "咸鲜味与金酒的杜松子香气互补，橄榄油融入酒液增加圆润口感。"
        ),
    },
    "柠檬片": {
        "production": (
            "黄色柠檬洗净后切成 5-8mm 厚的圆片或半圆片，去籽避免苦味。"
            "可用刀在果皮与果肉之间划一圈（twist）释放精油。商用可脱水制成 dry slice，"
            "但调酒推荐鲜切以保留精油挥发物。"
        ),
        "brands": "- 鲜果本地采购（无品牌化）\n- Fees Brothers 脱水柠檬片\n- Urban Moon Apothecary",
        "origin": "全球（原产印度，现主产美国加州/西班牙/意大利）",
        "flavor": (
            "柑橘精油的明亮香气，果肉提供酸度，果皮带轻微苦韵。"
            "装饰同时释放柠檬精油覆盖酒面，提升嗅觉体验。Gin & Tonic/Whiskey Sour 经典装饰。"
        ),
    },
    "薄荷叶": {
        "production": (
            "薄荷（Mentha，调酒多用 spearmint 留兰香或 peppermint 胡椒薄荷）鲜叶采摘，"
            "保留枝条以维持新鲜。使用前在掌心拍击或在杯中轻捣（muddle）释放精油，"
            "避免过度捣压出苦味。需冷藏保湿保存，2-3 天内用完。"
        ),
        "brands": "- 鲜栽本地采购（无品牌化）\n- Frontier Co-op 有机干薄荷\n- Simply Organic",
        "origin": "全球（原产地中海，现主产美国/摩洛哥/印度）",
        "flavor": (
            "清新凉爽的薄荷脑香气，带草本青草感与微甜。Mojito/Mint Julep 的灵魂，"
            "提供清凉感与视觉绿意，与朗姆酒和威士忌绝配。"
        ),
    },
    "樱桃": {
        "production": (
            "Maraschino Cherry 最初用 Marasca 樱桃与 Maraschino 利口酒浸泡，"
            "现代工业版用 Royal Anne 樱桃经二氧化硫漂白后用糖浆与红色素染色。"
            "高档品牌如 Luxardo 还原传统 Marasca 浸泡配方，带利口酒香。"
        ),
        "brands": "- Luxardo 卢萨多（传统顶级）\n- Amarena Fabbri\n- Tillen Farms\n- Pathfinder\n- Reed's",
        "origin": "意大利/美国（Marasca 樱桃原产克罗地亚达尔马提亚）",
        "flavor": (
            "甜润的樱桃果香，带杏仁般的核果香与轻微烟熏。Luxardo 版本带 Marasca 利口酒的复杂气息，"
            "工业版本糖浆甜腻。Manhattan/Aviation 的经典装饰。"
        ),
    },
    "橙皮": {
        "production": (
            "甜橙（如 Valencia/Navel 品种）洗净后用削皮刀取外层橙色表皮，避免白色海绵层（带苦味）。"
            "可切成 twist 卷状、宽片状或窄条。使用前在酒杯上方挤压释放橙皮精油，再用火柴炙烤（expressed）增香。"
        ),
        "brands": "- 鲜果本地采购（无品牌化）\n- The Bitter Truth 脱水橙皮\n- Scrappy's Bitters 橙皮酊",
        "origin": "全球（原产中国/印度，现主产巴西/美国/西班牙）",
        "flavor": (
            "浓缩的橙皮精油香，带花香、微苦与轻微辛辣。释放的精油覆盖酒面，"
            "提升嗅觉层次。Old Fashioned/Negroni 的经典装饰，与苦精和威士忌绝配。"
        ),
    },
    # === wine 葡萄酒 ===
    "香槟": {
        "production": (
            "仅法国香槟区（Champagne AOC）法定产区生产，采用传统法（Méthode Champenoise）："
            "葡萄（主要 Chardonnay/Pinot Noir/Meunier）压榨后基酒发酵，加糖与酵母二次发酵，"
            "在瓶中陈年 15 个月-NV、3 年以上-年份香槟，转瓶去渣后补液装瓶。"
        ),
        "brands": "- Moët & Chandon 酩悦\n- Veuve Clicquot 凯歌\n- Dom Pérignon 唐培里侬\n- Krug 库克\n- Bollinger 伯林杰",
        "origin": "法国香槟区（Champagne AOC）",
        "flavor": (
            "细腻持久的气泡，酵母烤面包、白花、青苹果、柑橘与杏仁香气，"
            "陈年发展出蜂蜜、烤榛子、焦糖。酒体饱满，酸度明亮，余韵悠长。Champagne Cocktail/Mimosa 用。"
        ),
    },
    "普罗塞克": {
        "production": (
            "意大利东北部 Veneto 与 Friuli 产区生产，主要用 Glera 葡萄（≥85%）。"
            "采用 Charmat 法（罐中二次发酵）：基酒在大型不锈钢罐中加糖酵母二次发酵 30-40 天，"
            "过滤加压装瓶。比传统法成本低、果香更鲜明。"
        ),
        "brands": "- Valdo 瓦尔多\n- Bottega 博特加\n- La Marca 拉马尔卡\n- Mionetto 米奥内托\n- Zonin 卓林",
        "origin": "意大利 Veneto/Friuli（Prosecco DOC/DOCG）",
        "flavor": (
            "气泡较粗但清新，明显的梨、青苹果、白桃与花香，酸度明快。"
            "比香槟更轻盈果香，适合 Aperol Spritz/Negroni Sbagliato 等清爽长饮。"
        ),
    },
    "红葡萄酒": {
        "production": (
            "红葡萄（如赤霞珠/梅洛/黑皮诺）破皮去梗后带皮浸渍发酵 1-3 周提取色素与单宁，"
            "压榨分离酒液与酒渣，橡木桶或不锈钢罐陈年 6-36 个月，"
            "装瓶后部分需瓶中陈年。法国/意大利/西班牙为旧世界代表。"
        ),
        "brands": "- 主要按产区与酒庄（如 Château Lafite/Margaux/Opus One）\n- Robert Mondavi\n- Penfolds 奔富\n- Concha y Toro",
        "origin": "全球（法国/意大利/西班牙/美国加州/澳大利亚/智利）",
        "flavor": (
            "单宁结构、酸度、酒精与果香平衡。赤霞珠带黑醋栗与雪松，"
            "黑皮诺带樱桃与玫瑰，西拉带胡椒与黑果。Mulled Wine/Sangria 用作调酒基酒。"
        ),
    },
    "波特酒": {
        "production": (
            "葡萄牙杜罗河谷（Douro DOC）生产。葡萄（Touriga Nacional 等）破碎后发酵至 6-9% ABV，"
            "加入 77% 中性葡萄酒精终止发酵保留糖分，得到 19-22% 加强酒。"
            "在橡木桶中陈年，Ruby 短陈年保持果香，Tawny 长陈年氧化出坚果香。"
        ),
        "brands": "- Graham's\n- Fonseca\n- Taylor Fladgate\n- Dow's\n- Warre's",
        "origin": "葡萄牙杜罗河谷（Douro DOC）",
        "flavor": (
            "甜润醇厚，Ruby 带黑莓/李子/巧克力果酱香，Tawny 带焦糖/坚果/无花果/橙皮氧化香。"
            "甜度高、酒体饱满，余韵带温暖酒精感。餐后酒或 Port Tonic 长饮。"
        ),
    },
    "白葡萄酒": {
        "production": (
            "白葡萄（如霞多丽/长相思/雷司令）破皮后立即压榨分离果汁与果皮，"
            "无浸渍过程保持浅色。低温 15-18°C 发酵保留果香，部分过橡木桶（如霞多丽）"
            "或苹果酸乳酸发酵（如奶油霞多丽）。陈年时间通常短于红酒。"
        ),
        "brands": "- 主要按产区与酒庄（如 Chablis/Cloudy Bay）\n- Kendall-Jackson\n- Santa Margherita\n- Oyster Bay",
        "origin": "全球（法国/意大利/德国/新西兰/美国加州）",
        "flavor": (
            "无单宁或低单宁，酸度突出。霞多丽带苹果/黄油/橡木，"
            "长相思带醋栗/百香果/草本，雷司令带花香/矿物/ petrol。Spritzer/White Sangria 用。"
        ),
    },
    # === sake 清酒 ===
    "清酒": {
        "production": (
            "以米、米麹（Koji 米曲霉培养的米）与水为原料，采用“并行复发酵”——"
            "米淀粉被曲菌酶糖化的同时酵母发酵成酒精，这一独特工艺使酒精度可达 18-20%。"
            "低温 5-10°C 发酵 18-32 天，过滤巴氏杀菌后装瓶。"
        ),
        "brands": "- 獭祭 Dassai\n- 久保田 Kubota\n- 八海山 Hakkaisan\n- 十四代 Juyondai\n- 月桂冠 Gekkeikan",
        "origin": "日本（滩 Nada/伏见 Fushimi/新潟/秋田等）",
        "flavor": (
            "米香、旨味（鲜味）与微甜平衡，吟酿系带哈密瓜/苹果/香蕉等华丽果香（吟酿香）。"
            "纯米酒浓郁饱满，本酿造清爽平衡。冷饮突出果香，温饮展现米旨味。"
        ),
    },
    "纯米酒": {
        "production": (
            "仅用米、米麹、水三种原料，不添加酿造酒精。精米步合通常 70% 以下"
            "（无法律规定上限）。采用并行复发酵 18-32 天，过滤巴氏杀菌后装瓶。"
            "米香浓郁、口感饱满，是清酒最传统的形态。"
        ),
        "brands": "- 獭祭 纯米大吟酿（旭酒造）\n- 八海山 纯米酒\n- 久保田 纯米酒\n- 飛露喜\n- 富久長",
        "origin": "日本（全国各地酒造）",
        "flavor": (
            "米香、五谷香与旨味（鲜味）浓郁，口感饱满醇厚，带轻微酸度与苦韵。"
            "适合温燗（40-45°C）展现米旨味，搭配油脂料理绝佳。"
        ),
    },
    "本酿造": {
        "production": (
            "米、米麹、水加少量酿造酒精（精米步合 ≤70%）。添加少量酒精可调整风味、"
            "使酒体更轻盈爽口。采用短期低温发酵 15-20 天，过滤巴氏杀菌后装瓶。"
            "比纯米酒更清爽、更适合餐中饮用。"
        ),
        "brands": "- 月桂冠 本酿造\n- 日本盛 本酿造\n- 大关 本酿造\n- 白鹤 本酿造\n- 菊正宗 本酿造",
        "origin": "日本（滩 Nada/伏见 Fushimi 等主产区）",
        "flavor": (
            "清爽平衡，米香清淡，带轻微果香与旨味。口感轻快、酸度适中，"
            "易饮性强，是清酒入门与餐中搭配的首选。冷饮或常温饮用最佳。"
        ),
    },
    "纯米大吟酿": {
        "production": (
            "仅用米、米麹、水，精米步合 ≤50%（即磨去 ≥50% 米粒外层），"
            "去除蛋白质与脂肪露出核心淀粉。低温 5-10°C 长期发酵 30-40 天，"
            "精米过程极耗时（从 70% 到 50% 需 2-3 天）。是清酒最高级分类。"
        ),
        "brands": "- 獭祭 磨二割三分（23%）\n- 十四代 纯米大吟酿\n- 而今 纯米大吟酿\n- 醸し人九平次\n- 信州亀齢",
        "origin": "日本（山口/山形/三重/长野等名产地）",
        "flavor": (
            "华丽的吟酿香（哈密瓜/苹果/洋梨/香蕉），酒体纯净透明，"
            "口感细腻丝滑，余韵优雅带果香。冷饮（5-10°C）最能展现香气，是清酒顶级代表。"
        ),
    },
    "大吟酿": {
        "production": (
            "米、米麹、水加少量酿造酒精，精米步合 ≤50%。"
            "添加少量酒精可提香（吟酿香更突出）。低温 5-10°C 长期发酵 30-40 天，"
            "精米成本极高（核心淀粉仅剩 50% 以下）。属最高级清酒之一。"
        ),
        "brands": "- 獭祭 大吟酿\n- 久保田 大吟酿 万寿\n- 八海山 大吟酿\n- 北邮政 大吟酿\n- 出羽桜 大吟酿",
        "origin": "日本（滩 Nada/伏见 Fushimi/新潟/山形等）",
        "flavor": (
            "比纯米大吟酿更强调吟酿香（哈密瓜/苹果/香蕉），酒体更轻盈透明，"
            "口感丝滑、余韵优雅。冷饮（5-10°C）最佳，适合作为餐前酒或庆祝场合。"
        ),
    },
    # === vermouth 味美思细分品牌 ===
    "力洛酒": {
        "production": (
            "法国波尔多 Lillet 公司 1872 年创制。以波尔多 Semillon/Sauvignon Blanc 葡萄酒为基底，"
            "浸泡柑橘皮（包括秘鲁奎宁皮）与水果利口酒，在橡木桶中陈年 12 个月，"
            "装瓶前过滤。比传统味美思更果香、更轻盈。"
        ),
        "brands": "- Lillet Blanc\n- Lillet Rouge\n- Lillet Rosé（同一酒庄三款）",
        "origin": "法国波尔多（Podensac）",
        "flavor": (
            "Blanc 带蜂蜜、橙花、柑橘与松脂香，微甜清爽；Rouge 带红色浆果与橡木；Rosé 带花果香。"
            "比传统味美思更果香，是 Vesper/Martini 配方中的关键。"
        ),
    },
    "多林味美思": {
        "production": (
            "法国阿尔卑斯山尚贝里（Chambéry）Dolin 公司 1821 年创制。"
            "以当地白葡萄酒为基底，浸泡阿尔卑斯山草药（包括苦艾 Artemisia）与香料，"
            "加少量中性酒精提高至 16% ABV。尚贝里是法国唯一 AOC 味美思产区。"
        ),
        "brands": "- Dolin Dry\n- Dolin Rouge\n- Dolin Blanc（同一酒庄三款）",
        "origin": "法国尚贝里（Chambéry AOC）",
        "flavor": (
            "Dry 浅色，干爽带青苹果、茴香、苦艾尾韵；Rouge 深红色，焦糖、香草、丁香；"
            "Blanc 浅金色，香草、八角、甘菊。干型代表，是 Martini/Manhattan 的法国选择。"
        ),
    },
    "诺瓦利帕味美思": {
        "production": (
            "法国南部 Sète 市 Noilly Prat 公司 1813 年创制。"
            "以 Picpoul 与 Clairette 葡萄酒为基底，在户外橡木桶中陈年 8 个月受海风吹拂，"
            "再转移至室内陈年 2 年，期间加入 20 种草药（包括苦艾、罗马洋甘菊）浸泡。"
        ),
        "brands": "- Noilly Prat Original Dry\n- Noilly Prat Rouge\n- Noilly Prat Extra Dry",
        "origin": "法国南部 Sète",
        "flavor": (
            "干型主导，带海风矿物感、苹果、茴香、百里香与苦艾。"
            "比 Dolin 更醇厚复杂，是干型法国味美思的奠基者，Martini 干味美思经典选择。"
        ),
    },
    "奎纳味美思": {
        "production": (
            "意大利味美思细分类型，添加奎宁（Quinine）皮提取物，"
            "以中性葡萄酒为基底浸泡苦艾与多种草药（包括 Cinchona 树皮）。"
            "奎宁带来独特苦韵与防疟疾历史渊源。常用于 Americano/Negroni 变体。"
        ),
        "brands": "- Cocchi Americano\n- Carpano Quina\n- Antica Formula\n- Punt e Mes\n- Mauro Vergano",
        "origin": "意大利都灵",
        "flavor": (
            "比传统味美思多一层奎宁苦韵，带橙皮、香草、肉桂与苦艾。"
            "甜苦平衡，余韵带矿物与香料。Vesper 中的 Cocchi Americano 是经典替代。"
        ),
    },
    # === ice 冰 ===
    "方块冰": {
        "production": (
            "纯净水经冷冻制成约 2.5×2.5×2.5cm 立方体。商用制冰机采用流动水冷冻法，"
            "气泡少、透明度高。高端吧台用_directional freezing_定向冷冻法制透明冰，"
            "去除杂质。家用冰格冰通常带气泡、易碎。"
        ),
        "brands": "- Hoshizaki 星崎\n- Scotsman\n- Kold-Draft\n- Wessmith\n- Glacio Premium",
        "origin": "全球（无产地概念，吧台基础材料）",
        "flavor": (
            "无味，提供冷却与稀释功能。方块冰表面积小、融化慢，适合 Old Fashioned/Stir 类"
            "需要缓慢稀释的鸡尾酒，保持酒体强度。"
        ),
    },
    "碎冰": {
        "production": (
            "方块冰经碎冰机（ice crusher）或 Lewis bag 加锤击碎成 5-10mm 不规则颗粒，"
            "或商用 shaved ice 机直接制成。需即制即用以避免结块。"
            "南方冰块经破碎后表面积大幅增加，冷却快但稀释也快。"
        ),
        "brands": "- Waring Pro 碎冰机\n- Scotsman 碎冰机\n- Lewis Bag（手工）\n- Vueoux\n- Implus",
        "origin": "全球（无产地概念，吧台基础材料）",
        "flavor": (
            "无味，提供快速冷却与高稀释。表面积大、融化极快，"
            "适合 Mojito/Julep/Tiki 等需要霜冻感与高稀释的鸡尾酒，形成冰水混合质感。"
        ),
    },
    "老冰": {
        "production": (
            "约 5×5×5cm 以上的大方块或大圆柱冰，采用 directional freezing 定向冷冻法"
            "（自上而下冷冻，杂质下沉到底部切除）制成。透明度高、密度大、杂质少，"
            "融化速度远慢于普通冰块。手工切割成所需形状。"
        ),
        "brands": "- Glacio Premium\n- Wintersmiths\n- Ice Barrel\n- ClearlyFrozen\n- Tovolo",
        "origin": "全球（高端吧台制作）",
        "flavor": (
            "无味，提供极慢的冷却与极低稀释。密度大、融化慢，"
            "适合 Old Fashioned/Negroni 等烈酒型鸡尾酒，保持酒体强度与温度平衡。"
        ),
    },
    "球冰": {
        "production": (
            "直径约 5-7cm 的球形大冰块，采用硅胶冰模或专用制冰机（如 Taisin）制成。"
            "高端吧台用 directional freezing 法 + 球模组合，或用冰雕刀手工切割老冰成球。"
            "比同体积方块表面积更小，融化更慢。"
        ),
        "brands": "- Tovolo 球模\n- Taisin 制冰机\n- Glacio Sphere\n- Wintersmiths\n- ClearlyFrozen",
        "origin": "全球（日式调酒推动流行）",
        "flavor": (
            "无味，提供极慢冷却与最低稀释。球形几何最优（最小表面积/体积比），"
            "适合 Old Fashioned/Whiskey Neat 等需要保持酒体强度的场合，视觉优雅。"
        ),
    },
    "冰沙": {
        "production": (
            "方块冰经 shaved ice 机或刨冰机刨成 1-3mm 细小颗粒，呈雪花状。"
            "需即制即用，避免融化结块。商用机可调节颗粒粗细。"
            "Tiki 类与 Frozen 类鸡尾酒的核心材料，提供冰沙质感。"
        ),
        "brands": "- Hatsuyuki 刨冰机\n- Swan Ice Shaver\n- Hawaiian Shaved Ice\n- Nostalgia\n- Vevor",
        "origin": "全球（无产地概念，吧台/Tiki 调酒材料）",
        "flavor": (
            "无味，提供霜冻感与高稀释。极细颗粒快速冷却酒液，"
            "形成冰沙质感。适合 Frozen Daiquiri/Snow Cone 等 Tiki 风格鸡尾酒。"
        ),
    },
    # === syrup 糖浆细分 ===
    "薰衣草糖浆": {
        "production": (
            "干燥薰衣草花（Lavandula angustifolia）用热水浸泡 15-20 分钟萃取香气，"
            "过滤后加入等量白糖加热至 80°C 溶解，冷却装瓶。也可冷浸法："
            "薰衣草在 1:1 糖浆中冷藏浸泡 24-48 小时。注意用量过多会变肥皂味。"
        ),
        "brands": "- Monin 莫林 薰衣草\n- Torani 托拉尼\n- Sonoma Syrup Co.\n- Small Hand Foods\n- BG Reynolds",
        "origin": "法国普罗旺斯/英国（薰衣草主产地）",
        "flavor": (
            "清新的薰衣草花香，带草本与轻微胡椒感，甜度中等。"
            "为鸡尾酒增加花香味调，与杜松子金酒、柠檬、蓝莓等搭配绝佳。"
            "Aviation/Martini 变体的特色调味。"
        ),
    },
    # === spirit 通用烈酒 ===
    "烧酎": {
        "production": (
            "日本传统蒸馏酒，以大麦（麦烧酎）、米（米烧酎）、甘薯（芋烧酎）、黑糖（黑糖烧酎）"
            "或荞麦（荞麦烧酎）为原料，单式或减压蒸馏得到 20-40% ABV。"
            "常温陈年 3-6 个月，比烧酒更注重原料风味保留。"
        ),
        "brands": "- iichiko 获得白岳\n- Kuro Kirishima 黑雾岛\n- Satsuma Shochu 萨摩\n- Zenkuro\n- Mizubasho",
        "origin": "日本九州（鹿儿岛/宫崎/熊本）",
        "flavor": (
            "因原料不同差异巨大：芋烧酎带甘薯的甜香与 earthy，麦烧酎带谷物与麦芽香，"
            "米烧酎带清酒的米旨味。口感比烧酒更复杂，余韵带原料本味。"
        ),
    },
}


def get_representatives() -> dict[str, list[tuple[str, dict]]]:
    """每类取前 5 个 (canonical, info) 元组（不足 5 则全取）。"""
    by_category: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for info in INGREDIENT_REGISTRY.values():
        by_category[info["category"]].append((info["canonical"], info))
    return {cat: items[:5] for cat, items in by_category.items()}


def build_profile_content(canonical: str, info: dict, profile: dict) -> str:
    """生成 markdown 档案内容。"""
    aliases = ", ".join(info.get("aliases", [])[:5]) or "（无）"
    abv = float(info.get("abv", 0.0))
    abv_str = f"{abv:.1%}" if abv > 0 else "0%（非酒精）"
    return f"""# {canonical}

## 基本信息
- 类别：{info["category"]}
- 别名：{aliases}
- ABV：{abv_str}

## 生产工艺
{profile["production"]}

## 主要品牌
{profile["brands"]}

## 产地
{profile["origin"]}

## 风味特征
{profile["flavor"]}
"""


def main() -> None:
    reps = get_representatives()
    total_reps = sum(len(items) for items in reps.values())

    print("=" * 60)
    print("材料档案库构建")
    print("=" * 60)
    print(f"10 大类别代表材料总数: {total_reps}")
    for cat, items in reps.items():
        print(f"  {cat}: {len(items)} 种")

    importer = ImportService()
    inserted = 0
    skipped = 0
    missing = 0
    failed = 0
    missing_names: list[str] = []

    for cat, items in reps.items():
        print(f"\n[{cat}]")
        for canonical, info in items:
            # 用 registry 中的原始 key 作为 source_id 一部分
            # 通过 canonical 反查 key
            reg_key = next(
                k for k, v in INGREDIENT_REGISTRY.items() if v["canonical"] == canonical
            )
            source_id = f"ingredient_profile:{reg_key}"

            # 幂等：按 source_id 查重
            with get_session() as s:
                existing = s.exec(
                    select(Document).where(Document.source_id == source_id)
                ).first()
                if existing:
                    print(f"  SKIP  {canonical} (已存在 doc_id={existing.doc_id})")
                    skipped += 1
                    continue

            profile = PROFILES.get(canonical)
            if not profile:
                print(f"  MISS  {canonical} (无档案数据)")
                missing += 1
                missing_names.append(canonical)
                continue

            content = build_profile_content(canonical, info, profile)
            title = f"{canonical} 材料档案"

            try:
                result = importer.import_text(
                    content=content,
                    title=title,
                    source_type="seed",
                    file_type="md",
                    category="encyclopedia",
                    source="ingredient_profile",
                    source_id=source_id,
                )
                inserted += 1
                print(f"  OK    {canonical} (chunks={result.get('chunk_count', 0)})")
            except (KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
                print(f"  FAIL  {canonical}: {e}")
                failed += 1

    # ------------------------------------------------------------------
    # 汇总报告
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("汇总")
    print("=" * 60)
    print(f"  代表材料总数: {total_reps}")
    print(f"  已插入: {inserted}")
    print(f"  已跳过: {skipped}")
    print(f"  缺失档案数据: {missing}")
    print(f"  失败: {failed}")
    if missing_names:
        print(f"  缺失材料: {missing_names}")
    coverage = (inserted + skipped) / total_reps * 100 if total_reps else 0.0
    print(f"  覆盖率: {coverage:.1f}% (>= 80% 验收)")

    # 最终验证：数据库中 ingredient_profile 文档数
    with get_session() as s:
        count = s.exec(
            select(func.count(Document.doc_id)).where(
                Document.source == "ingredient_profile"
            )
        ).one()
        print(f"  数据库 ingredient_profile 文档总数: {count}")


if __name__ == "__main__":
    main()
