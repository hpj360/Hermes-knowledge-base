"""酒类冷启动种子知识（5 篇）。

用于 M0/M1 开发测试与首次启动引导。覆盖六大基酒的代表酒种。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hermes_kb.ingredient_strength import estimate_recipe_stats
from hermes_kb.recipe_stats import classify_abv_bucket

if TYPE_CHECKING:
    from hermes_kb.rag import ImportService

SEED_DOCS: list[dict[str, str]] = [
    {
        "title": "金酒（Gin）百科",
        "content": """# 金酒 Gin

金酒，又称杜松子酒，是以谷物（大麦、黑麦、小麦）为原料发酵蒸馏得到中性烈酒，再用杜松子等植物香料浸泡或二次蒸馏而成的烈酒。酒精度通常在 35%-55% 之间。

## 起源与历史

金酒起源于 17 世纪的荷兰。荷兰莱顿大学的西尔维斯教授最初用杜松子浸泡酒精制成药物，用于治疗肾脏疾病和航海时的热带疾病。这种"杜松子酒"被荷兰人称为 Genever。

17 世纪末，英荷战争期间英国士兵将 Genever 带回英国，并简化工艺、降低成本，演变成今天的 London Dry Gin。18 世纪英国"金酒狂热"时期，金酒成为平民饮料，也引发了一系列社会问题。

## 风味特点

金酒的核心风味来自杜松子（juniper berry），呈现明显的松木、松针、柑橘类香气。除此之外，调香植物通常包括：
- 芫荽籽（coriander）—— 柑橘、香料感
- 当归根（angelica root）—— 土质、麝香
- 柑橘皮（citrus peel）—— 柠檬、橙花
- 小豆蔻（cardamom）—— 辛香、樟脑
- 肉桂、八角、鸢尾根等

按风格可分为：
1. **London Dry Gin**：杜松子主导，干爽清冽，最经典风格
2. **Plymouth Gin**：略甜，口感圆润，地理保护标志
3. **Old Tom Gin**：介于 London Dry 与荷兰 Genever 之间，微甜
4. **New Western / Contemporary Gin**：弱化杜松子，强调其他植物
5. **Genever**：荷兰原版，麦芽基底，带有谷物感

## 经典鸡尾酒

金酒被誉为"鸡尾酒的心脏"，是调制鸡尾酒最重要的基酒之一。

- **马天尼 Martini**：金酒 + 干味美思，被誉为"鸡尾酒之王"
- **金汤力 Gin & Tonic**：金酒 + 汤力水 + 青柠，最经典长饮
- **尼格罗尼 Negroni**：金酒 + 金巴利 + 甜味美思，苦甜平衡
- **白色佳人 White Lady**：金酒 + 君度 + 柠檬汁，酸香优雅

## 代表品牌

- **必富达 Beefeater**：伦敦经典 London Dry
- **哥顿 Gordon's**：全球销量最大的金酒
- **添加利 Tanqueray**：四倍蒸馏，杜松子香气浓郁
- **亨利爵士 Hendrick's**：黄瓜玫瑰 infused，新派代表
- **猴王 47 Monkey 47**：47 种植物，黑森林风格
""",
    },
    {
        "title": "威士忌 Whisky 百科",
        "content": """# 威士忌 Whisky

威士忌是以谷物（大麦、玉米、黑麦、小麦）为原料发酵、蒸馏、橡木桶陈酿而成的烈酒。酒精度通常在 40%-60% 之间，常见装瓶为 40%-46%。

## 主要分类

### 1. 苏格兰威士忌 Scotch Whisky

产地：苏格兰。法律要求至少在橡木桶中陈酿 3 年，装瓶酒精度不低于 40%。

- **单一麦芽威士忌 Single Malt**：单一酒厂、100% 麦芽、壶式蒸馏
- **单一谷物威士忌 Single Grain**：单一酒厂、谷物原料、柱式蒸馏
- **调和威士忌 Blended Whisky**：麦芽 + 谷物调和，代表品牌尊尼获加、芝华士

苏格兰主要产区：
1. **斯佩塞 Speyside**：花果香、轻盈优雅（麦卡伦、格兰菲迪）
2. **高地 Highlands**：风格多样，从轻盈到厚重
3. **低地 Lowlands**：轻盈柔和，入门友好
4. **艾雷岛 Islay**：重泥煤、烟熏、海盐（阿贝、拉弗格）
5. **坎贝尔镇 Campbeltown**：微咸、烟熏、油脂感

### 2. 爱尔兰威士忌 Irish Whiskey

通常三次蒸馏、不使用泥煤，口感柔顺、清甜。代表品牌：尊美醇、知更鸟。

### 3. 美国威士忌 American Whiskey

- **波本威士忌 Bourbon**：≥51% 玉米，新橡木桶陈酿，甜润香草感。代表：美格、四玫瑰
- **黑麦威士忌 Rye**：≥51% 黑麦，辛香、胡椒感。代表：布克、莱特曼
- **田纳西威士忌 Tennessee**：波本变种，糖枫木炭过滤。代表：杰克丹尼

### 4. 日本威士忌 Japanese Whisky

借鉴苏格兰工艺，清新细腻。代表：三得利响、山崎、白州、余市。

### 5. 加拿大威士忌 Canadian Whisky

以黑麦为特色，轻柔顺滑。代表：加拿大俱乐部。

## 品鉴要点

- **色泽**：从淡金到深琥珀，反映橡木桶类型与陈年时间
- **香气**：麦芽、橡木、香草、烟熏、泥煤、果干
- **口感**：酒体、甜度、单宁、油脂感
- **余韵**：长度、变化、烟熏、辛辣

## 经典饮法

- 纯饮 Neat：常温直接饮用
- 加水 With Water：开香、降度
- 加冰 On the Rocks：缓慢冷却稀释
- 海波 Highball：威士忌 + 苏打水，日式流行
""",
    },
    {
        "title": "葡萄酒 Wine 百科",
        "content": """# 葡萄酒 Wine

葡萄酒是以新鲜葡萄或葡萄汁为原料，经酵母发酵酿制而成的酒精饮料。酒精度通常在 8%-15% 之间。

## 类型分类

1. **静止酒 Still Wine**：无气泡，最常见
2. **起泡酒 Sparkling Wine**：含二氧化碳，如香槟、卡瓦、普罗塞克
3. **加强酒 Fortified Wine**：加入白兰地提高酒精度，如波特、雪莉
4. **甜酒 Sweet Wine**：甜度高，如冰酒、贵腐酒

## 颜色分类

- **红葡萄酒 Red**：带皮发酵，含单宁
- **白葡萄酒 White**：去皮发酵，无单宁或低单宁
- **桃红葡萄酒 Rosé**：短时浸皮或调配

## 主要葡萄品种

### 红葡萄
- **赤霞珠 Cabernet Sauvignon**：波尔多之王，单宁高、黑醋栗香
- **梅洛 Merlot**：圆润柔顺，李子香
- **黑皮诺 Pinot Noir**：优雅细腻，勃艮第主角
- **西拉 Syrah/Shiraz**：胡椒、黑色水果、香料
- **品丽珠 Cabernet Franc**：草本、紫罗兰

### 白葡萄
- **霞多丽 Chardonnay**：风格多变，从清瘦到浓郁
- **长相思 Sauvignon Blanc**：草本、醋栗、柑橘
- **雷司令 Riesling**：花香、矿物、酸度优雅
- **灰皮诺 Pinot Grigio**：清新轻盈
- **琼瑶浆 Gewürztraminer**：荔枝、玫瑰香

## 主要产区

### 旧世界
- **法国**：波尔多、勃艮第、香槟、罗讷河谷、卢瓦尔
- **意大利**：托斯卡纳、皮埃蒙特、威尼托
- **西班牙**：里奥哈、杜罗河岸
- **德国**：摩泽尔、莱茵高

### 新世界
- **美国加州**：纳帕谷、索诺玛
- **澳大利亚**：巴罗萨谷、克莱尔谷
- **智利**：中央山谷
- **新西兰**：马尔堡（长相思）
- **南非**：斯泰伦博斯

## 酿造工艺

1. **采摘 Harvest**：手工或机械
2. **破皮去梗 Destemming**：去梗保留整粒
3. **浸渍发酵 Maceration & Fermentation**：红葡萄带皮浸渍提取色素单宁
4. **压榨 Pressing**：分离酒液与酒渣
5. **陈酿 Aging**：橡木桶或不锈钢罐
6. **澄清装瓶 Fining & Bottling**：过滤、稳定、装瓶

## 品鉴步骤（5S）

- **See 看**：颜色深浅、边缘色调
- **Swirl 摇**：挂杯、酒体
- **Sniff 闻**：第一层果香、第二层工艺、第三层陈年
- **Sip 尝**：甜酸苦咸、单宁、酒精
- **Savor 评**：平衡、复杂、余韵
""",
    },
    {
        "title": "中国白酒百科",
        "content": """# 中国白酒

中国白酒是以高粱、小麦、玉米、大米、糯米等谷物为原料，以曲类为糖化发酵剂，经固态或液态发酵、蒸馏、陈酿、勾兑而成的中国特产蒸馏酒。酒精度通常在 38%-65% 之间。

## 12 大香型

### 1. 酱香型
- **代表**：茅台、郎酒、习酒
- **特点**：酱香突出、幽雅细腻、酒体醇厚、回味悠长
- **工艺**：端午制曲、重阳下沙、9 次蒸煮、8 次发酵、7 次取酒、4 年陈酿

### 2. 浓香型
- **代表**：五粮液、泸州老窖、剑南春、洋河
- **特点**：窖香浓郁、绵甜甘冽、香味协调、尾净爽口
- **工艺**：泥窖固态发酵，万年糟

### 3. 清香型
- **代表**：汾酒、牛栏山、二锅头
- **特点**：清香纯正、醇甜柔和、自然谐调、余味爽净
- **工艺**：地缸分离发酵，清蒸二次清

### 4. 米香型
- **代表**：桂林三花酒、湘山酒
- **特点**：蜜香清雅、入口柔绵、落口爽净、回味怡畅

### 5. 兼香型
- **代表**：白云边、口子窖
- **特点**：酱浓协调、一口两香

### 6. 芝麻香型
- **代表**：景芝、扳倒井
- **特点**：芝麻香突出、幽雅醇厚

### 7. 豉香型
- **代表**：玉冰烧
- **特点**：豉香独特、醇和甘滑

### 8. 凤香型
- **代表**：西凤酒
- **特点**：醇香秀雅、甘润挺爽

### 9. 药香型 / 其他香型
- **代表**：董酒
- **特点**：药香突出、醇厚甘爽

### 10. 特香型
- **代表**：四特酒
- **特点**：幽雅舒适、诸味协调

### 11. 老白干香型
- **代表**：衡水老白干
- **特点**：醇香清雅、甘冽挺拔

### 12. 馥郁香型
- **代表**：酒鬼酒
- **特点**：前浓中清后酱，馥郁三香

## 主要产地

- **川黔产区**：茅台、五粮液、泸州老窖、郎酒
- **黄淮产区**：洋河、古井贡、汾酒
- **北方产区**：二锅头、老白干、景芝

## 工艺特点

- **曲**：大曲（小麦）、小曲（米曲）、麸曲（麸皮）
- **发酵**：固态发酵（白酒主流）、液态发酵（米酒、洋酒）
- **蒸馏**：固态蒸馏甑桶
- **陈酿**：陶坛、酒海
- **勾兑**：以酒勾酒，不添加非发酵物质

## 饮用方式

- 常温纯饮
- 温饮（黄酒传统）
- 加冰（新派尝试）
- 调鸡尾酒（白酒国际化方向）
""",
    },
    {
        "title": "朗姆酒与龙舌兰百科",
        "content": """# 朗姆酒 Rum 与龙舌兰 Tequila

朗姆酒与龙舌兰都是具有鲜明地域特色的烈酒，分别是加勒比海与墨西哥的国酒。

## 朗姆酒 Rum

朗姆酒是以甘蔗糖蜜或甘蔗汁为原料，经发酵、蒸馏、陈酿而成的烈酒。酒精度通常在 40%-75% 之间。

### 起源

朗姆酒起源于 17 世纪的加勒比海地区。巴巴多斯的奴隶发现甘蔗榨汁后的糖蜜可以发酵蒸馏出酒精饮料，这就是朗姆酒的雏形。"Rum"一词来源众说纷纭，可能来自 rumbullion（喧嚣）或 rummer（大杯）。

### 分类

1. **按原料**：
   - **工业朗姆 Industrial Rum**：糖蜜为原料，最常见
   - **农业朗姆 Rhum Agricole**：甘蔗汁为原料，主要产自法属马提尼克

2. **按风格**：
   - **白朗姆 White/Light Rum**：未陈年或短暂陈年，清爽
   - **金朗姆 Gold Rum**：橡木桶陈年 1-3 年，琥珀色
   - **黑朗姆 Dark Rum**：深度陈年或加焦糖调色，浓郁

3. **按产地**：
   - **古巴**：轻盈清爽，代表哈瓦那俱乐部
   - **牙买加**：浓郁厚重，代表苹果顿
   - **波多黎各**：清淡顺滑，代表百加得
   - **法属马提尼克**：农业朗姆，AOC 法定产区
   - **巴巴多斯**：平衡醇厚，朗姆酒发源地

### 经典鸡尾酒

- **莫吉托 Mojito**：白朗姆 + 薄荷 + 青柠 + 苏打
- **大吉岭 Daiquiri**：白朗姆 + 青柠汁 + 糖
- **椰林飘香 Piña Colada**：朗姆 + 椰浆 + 菠萝汁
- **黑色风暴 Dark 'n' Stormy**：黑朗姆 + 姜啤 + 青柠

## 龙舌兰 Tequila / Mezcal

龙舌兰酒是以龙舌兰植物为原料，经烘烤、发酵、蒸馏而成的墨西哥国酒。

### Tequila vs Mezcal

- **Mezcal**：泛指所有龙舌兰酒，可使用多种龙舌兰
- **Tequila**：Mezcal 的子集，仅限使用蓝色龙舌兰（Weber Blue Agave），且必须在墨西哥指定产区生产

### 分类（按陈年）

1. **Blanco / Silver**：未陈年或陈年 <2 个月，纯净龙舌兰香
2. **Joven / Gold**：Blanco 调色，常加焦糖
3. **Reposado**：橡木桶陈年 2-12 个月，金色
4. **Añejo**：橡木桶陈年 1-3 年，琥珀色
5. **Extra Añejo**：陈年 3 年以上，深邃复杂

### 龙舌兰植物

- 蓝色龙舌兰 Weber Blue Agave：Tequila 唯一法定品种
- 成熟期 7-10 年
- 心部（piña）重 30-100 公斤
- 法定产区：哈利斯科州全境 + 周边 4 州部分

### 经典饮法与鸡尾酒

- **盐柠檬饮法**：舔盐 + 一口 Tequila + 咬柠檬
- **龙舌兰日出 Tequila Sunrise**：Tequila + 橙汁 + 红石榴糖浆
- **玛格丽特 Margarita**：Tequila + 君度 + 青柠汁 + 盐边
- **帕洛玛 Paloma**：Tequila + 西柚苏打 + 青柠

## 共同特点

- 都是非谷物烈酒（朗姆用甘蔗、龙舌兰用植物心）
- 都具有强烈地域标识（加勒比 vs 墨西哥）
- 都是鸡尾酒重要基酒
- 都有 AOC 或法定产区制度
""",
    },
    {
        "title": "伏特加 Vodka 百科",
        "content": """# 伏特加 Vodka

伏特加是以谷物（小麦、黑麦、玉米）或马铃薯为原料，经发酵、多次蒸馏、过滤而成的中性烈酒。酒精度通常在 35%-50% 之间，部分波兰传统伏特加可达 75% 甚至 96%。伏特加以"纯净无味"为核心特征，是世界上最畅销的烈酒之一。

## 起源与历史

伏特加起源于东欧，俄罗斯与波兰都宣称是发源地。"Vodka"一词源自斯拉夫语"voda"（水），意为"小水"。最早的伏特加可追溯到 8-9 世纪，最初作为药用与取暖饮品。

14 世纪伏特加生产工艺逐渐成熟，俄罗斯沙皇伊凡三世于 1474 年确立国家伏特加垄断。19 世纪发明的连续柱式蒸馏器使伏特加品质大幅提升，变得更加纯净。19 世纪 70 年代，斯米诺品牌在莫斯科崛起。

俄国革命后，许多伏特加酿酒师流亡欧洲，将伏特加带向世界。二战后，伏特加在全球流行，特别是搭配鸡尾酒成为美式酒吧的核心基酒之一。

## 分类与风格

按风味分两大类：

1. **中性伏特加 Neutral Vodka**：纯净无味，经过活性炭过滤，最常见风格
2. **风味伏特加 Flavored Vodka**：添加水果、香草、辣椒等风味，如柠檬伏特加、香草伏特加

按原料分类：
- **谷物伏特加**：小麦、黑麦为主，柔顺轻盈
- **马铃薯伏特加**：质感饱满，略带奶油感
- **葡萄/水果伏特加**：法国 Ciroc 等品牌使用葡萄原料

## 主要产区与代表品牌

主要产区：
- **俄罗斯**：传统风格，纯净有力。代表：斯米诺 Smirnoff、苏联红牌 Stolichnaya、俄罗斯标准 Russian Standard
- **波兰**：波兰风格，更注重原料香气。代表：雪树 Belvedere、野牛草 Żubrówka
- **瑞典**：纯净度极高，连续蒸馏。代表：绝对 Absolut
- **芬兰**：以冰川水酿造，纯净清冽。代表：芬兰 Finlandia
- **法国**：用小麦或葡萄酿造，时尚风格。代表：灰雁 Grey Goose、Ciroc
- **美国**：风格多样。代表：天宝 Skyy

## 风味特点

中性伏特加应呈现"无色无味"，仅带有酒精的温热感与微甜回甘。优质伏特加有丝绸般的顺滑口感，无杂味。黑麦伏特加略带香料感，小麦伏特加更柔顺，马铃薯伏特加更加饱满。

风味伏特加则保留所添加原料的明显香气，如柠檬、香草、覆盆子等。

## 经典鸡尾酒

伏特加因无强风味，是调制鸡尾酒的万能基酒。

- **莫斯科骡子 Moscow Mule**：伏特加 + 姜啤 + 青柠汁，铜杯盛装
- **血腥玛丽 Bloody Mary**：伏特加 + 番茄汁 + 各种香料调味
- **螺丝刀 Screwdriver**：伏特加 + 橙汁，简单清爽
- **大都会 Cosmopolitan**：伏特加 + 君度 + 蔓越莓汁 + 青柠
- **海风 Sea Breeze**：伏特加 + 西柚汁 + 蔓越莓汁
- **伏特加马天尼 Vodka Martini**：伏特加 + 干味美思，007 詹姆斯·邦德的最爱（shaken, not stirred）
""",
    },
    {
        "title": "白兰地 Brandy 百科",
        "content": """# 白兰地 Brandy

白兰地是以水果（葡萄、苹果、樱桃、梨等）为原料，经发酵、蒸馏、橡木桶陈酿而成的烈酒。酒精度通常在 35%-60% 之间，最常见为 40%。葡萄白兰地是主流，其他水果白兰地通常冠以水果名（如 Apple Brandy、Calvados）。

## 起源与历史

白兰地起源于 16-17 世纪的法国。为了减少葡萄酒运输体积并延长保存期，荷兰商人将葡萄酒蒸馏浓缩，到达目的地后再加水稀释，荷兰语称"brandewijn"（烧酒），后演变为英语"brandy"。

17 世纪法国干邑区开始系统生产优质葡萄白兰地，并发展出夏朗德壶式蒸馏器（Charentais Alembic）的二次蒸馏工艺。雅文邑（Armagnac）则是法国最古老的白兰地产区，采用连续蒸馏。

18-19 世纪，干邑白兰地成为欧洲贵族与皇室钟爱的饮品，轩尼诗、人头马、马爹利、拿破仑四大品牌相继崛起。

## 分类与风格

按原料分类：
- **葡萄白兰地**：以葡萄为原料，最主流
- **水果白兰地**：苹果、樱桃、梨、李子等，常以"Eau-de-Vie"命名
- **渣酿白兰地 Grappa/Marc**：用葡萄渣蒸馏

按产区分类：
- **干邑 Cognac**：法国干邑区，二次壶式蒸馏，最负盛名
- **雅文邑 Armagnac**：法国最古老白兰地，连续蒸馏为主
- **皮斯科 Pisco**：秘鲁与智利的国酒，未陈酿或短陈酿
- **西班牙白兰地**：赫雷斯产区，雪莉酒桶陈酿

## 陈年等级（干邑）

干邑白兰地按橡木桶陈年最短的酒液分级：
- **VS (Very Special)**：最年轻酒液陈年 ≥ 2 年
- **VSOP (Very Superior Old Pale)**：最年轻酒液陈年 ≥ 4 年
- **Napoleon**：最年轻酒液陈年 ≥ 6 年
- **XO (Extra Old)**：最年轻酒液陈年 ≥ 10 年（2018 年 4 月 1 日起从 6 年调整）
- **XXO (Extra Extra Old)**：最年轻酒液陈年 ≥ 14 年

## 主要产区与代表品牌

产区：
- **法国干邑区**：大香槟区、小香槟区、边缘区、植林区等六大子产区
- **法国雅文邑区**：下雅文邑、上雅文邑、雅文邑-特纳雷兹、特纳雷兹
- **秘鲁/智利**：皮斯科产区

代表品牌：
- **轩尼诗 Hennessy**：销量最大的干邑品牌
- **人头马 Rémy Martin**：以 "VSOP" 概念推广闻名，特优香槟干邑
- **马爹利 Martell**：最古老的干邑世家之一
- **拿破仑 Courvoisier**：拿破仑三世御用
- **卡慕 Camus**：家族独立经营
- **张裕**：中国知名白兰地品牌

## 风味特点

干邑白兰地呈琥珀色至深琥珀色，香气复杂。年轻干邑带有葡萄花、杏、桃子果香；陈年干邑则发展出橡木、香草、檀香、坚果、咖啡、皮革等陈年香气。口感圆润醇厚，余韵悠长。

雅文邑比干邑更粗犷、风格更浓郁，被称为"男人的白兰地"。皮斯科则带有新鲜葡萄花果香，无橡木桶陈酿风格。

## 经典应用

白兰地既是餐后酒，也是重要鸡尾酒基酒。

- **白兰地古典 Brandy Old Fashioned**：白兰地 + 糖 + 苦精 + 苏打水
- **侧车 Sidecar**：干邑 + 君度 + 柠檬汁
- **亚历山大 Alexander**：白兰地 + 可可利口酒 + 奶油
- **B&B**：白兰地 + Bénédictine 利口酒
- **皮斯科酸 Pisco Sour**：皮斯科 + 柠檬汁 + 糖浆 + 蛋白
- **纯饮 Neat**：室温白兰地杯，配以雪茄或甜点
""",
    },
    {
        "title": "利口酒 Liqueur 百科",
        "content": """# 利口酒 Liqueur

利口酒是以蒸馏酒（白兰地、朗姆、伏特加等）为基底，加入水果、草药、香料、坚果、奶油等风味原料，并加糖调味（含糖量 ≥ 2.5%）的烈酒。酒精度通常在 15%-55% 之间。利口酒又称"甜酒""餐后酒""配制酒"。

## 起源与历史

利口酒起源于中世纪欧洲修道院。僧侣们将草药浸泡在酒精中制成药剂，后逐渐演变为风味饮品。16-17 世纪意大利、法国成为利口酒制作中心。

- **查特 Chartreuse**：1605 年由卡尔特教派僧侣发明，配方至今保密
- **Bénédictine**：1510 年由诺曼底本笃会修士 Don Bernardo Vincelli 发明
- **金巴利 Campari**：1860 年意大利 Gaspare Campari 在米兰发明

19 世纪利口酒在欧洲上流社会流行，并随调酒文化兴起而成为鸡尾酒核心配料。

## 分类与风格

按风味原料分类：

1. **草药利口酒 Herbal Liqueur**：以多种草药为主，如查特（绿/黄）、Drambuie、Galliano
2. **水果利口酒 Fruit Liqueur**：以水果为主，如君度 Cointreau（橙味）、Chambord（覆盆子）
3. **坚果利口酒 Nut Liqueur**：如 Amaretto（杏仁味）、Frangelico（榛子味）
4. **奶油利口酒 Cream Liqueur**：含奶制品，如百利甜 Baileys（爱尔兰奶油）
5. **咖啡/可可利口酒**：如 Kahlúa（咖啡味）、Tia Maria
6. **花香利口酒**：如 Saint Germain（接骨木花）

## 代表品牌

- **君度 Cointreau**：法国橙味利口酒，1849 年创立
- **金巴利 Campari**：意大利苦味利口酒，米兰风格代表
- **查特绿 Chartreuse Verte**：法国卡尔特教派秘方，55% 酒精度
- **查特黄 Chartreuse Jaune**：温和甜润，40% 酒精度
- **百利甜 Baileys Irish Cream**：爱尔兰奶油利口酒，1974 年诞生
- **Drambuie**：苏格兰威士忌 + 蜂蜜 + 香料，源于 1746 年
- **Galliano**：意大利香草利口酒，金黄高瓶身
- **Amaretto Disaronno**：意大利杏仁味利口酒

## 风味特点

利口酒因风味原料不同而呈现极丰富的口感：
- 草药利口酒：复杂、辛香、有时带苦味
- 水果利口酒：果香浓郁、酸甜平衡
- 奶油利口酒：丝滑浓郁、甜而不腻
- 坚果利口酒：杏仁、榛子香气明显

糖度高是其核心特征，赋予利口酒"包裹"鸡尾酒风味、增加圆润度的能力。

## 经典鸡尾酒应用

利口酒在鸡尾酒中既可作为风味装饰，也可作为基酒。

- **尼格罗尼 Negroni**：金酒 + 金巴利 + 甜味美思
- **大都会 Cosmopolitan**：伏特加 + 君度 + 蔓越莓汁
- **白色佳人 White Lady**：金酒 + 君度 + 柠檬汁
- **教父 Godfather**：苏格兰威士忌 + Amaretto
- **B-52**：咖啡利口酒 + 爱尔兰奶油 + 橙味利口酒分层
- **金色梦幻 Golden Dream**：Galliano + 君度 + 橙汁 + 奶油
""",
    },
    {
        "title": "苦精 Bitters 百科",
        "content": """# 苦精 Bitters

苦精是以高浓度酒精为基底，将多种草药、香料、树皮、根茎浸提而成的浓缩调味液。苦精不属于烈酒，酒精度通常在 35%-45% 之间，但用量极小（几滴），不直接饮用，而是作为鸡尾酒的"调味盐"。

## 起源与历史

苦精起源于 18 世纪的药用酊剂。英国医生 Richard Stoughton 于 1712 年发明了最早的商用苦精"Elixir Vegetal"。19 世纪美国调酒师开始将苦精引入鸡尾酒，赋予饮品复杂层次。

- **安高天娜 Angostura**：1824 年委内瑞拉医生 Johann Siegert 发明，原用于治疗消化不良
- **佩肖德 Peychaud's**：1830 年新奥尔良药剂师 Antoine Amédée Peychaud 创制，与 Sazerac 鸡尾酒紧密相关
- **橙味苦精 Orange Bitters**：19 世纪末流行，曾一度衰落，21 世纪复兴

2000 年代后，精酿苦精运动兴起，出现 Fee Brothers、Bittermens、The Bitter Truth 等品牌，扩展了苦精风味多样性。

## 分类与风格

按风味类型分类：

1. **芳香苦精 Aromatic Bitters**：以肉桂、丁香、豆蔻为主，深褐色，最经典。代表：安高天娜
2. **橙味苦精 Orange Bitters**：橙皮主导，明亮柑橘感。代表：Regans'、Angostura Orange
3. **薄荷苦精 Mint Bitters**：薄荷风味，清凉感
4. **佩肖德苦精 Peychaud's**：以茴香、樱桃为主，浅红色，新奥尔良风格
5. **水果苦精**：以特定水果为主，如葡萄柚、樱桃、桃子
6. **香料苦精**：巧克力、咖啡、芹菜、可可等创新风味

## 用法

苦精的核心特征是"几滴即可"：

- **滴剂调味**：经典鸡尾酒中通常加 2-3 dashes（约 6-9 滴）
- **提升层次**：与基酒、糖浆协同，增强复杂度与平衡感
- **化解甜腻**：甜鸡尾酒中加苦精可解腻
- **装饰作用**：橙皮上的几滴苦精可提升嗅觉体验

苦精瓶常配有 dasher 瓶口，便于控制剂量。

## 代表品牌

- **安高天娜 Angostura**：委内瑞拉/特立尼达生产，全球最畅销苦精，标签过大是品牌标志
- **佩肖德 Peychaud's**：新奥尔良 Sazerac 公司生产，茴香樱桃调
- **Regans' Orange Bitters No.6**：Gary Regan 配方，橙味苦精代表
- **Fee Brothers**：美国老牌，1864 年创立，多风味系列
- **The Bitter Truth**：德国精酿品牌，复古配方复兴
- **Bittermens**：美国精创，创新风味

## 风味特点

苦精风味以"苦"为核心，但并非单一苦味。优质苦精呈现多层次：
- 初闻：草药、香料、柑橘精油
- 入口：苦、辛、甜、酸交织
- 余韵：根茎、木质、香料的悠长回味

苦精是鸡尾酒的"灵魂调味品"，没有苦精的 Old Fashioned 与 Manhattan 都不完整。

## 经典应用

苦精在经典鸡尾酒中不可或缺：

- **古典鸡尾酒 Old Fashioned**：威士忌 + 糖 + 安高天娜苦精
- **曼哈顿 Manhattan**：黑麦威士忌 + 甜味美思 + 安高天娜苦精
- **尼格罗尼 Negroni**：金酒 + 金巴利 + 甜味美思 + 橙味苦精（可选）
- **Sazerac**：干邑/黑麦 + 方糖 + 佩肖德苦精 + 苦艾洗杯
- **香槟鸡尾酒 Champagne Cocktail**：方糖 + 安高天娜苦精 + 香槟
""",
    },
    {
        "title": "味美思 Vermouth 百科",
        "content": """# 味美思 Vermouth

味美思是一种加强芳香葡萄酒，以白葡萄酒为基底，加入苦艾（wormwood， Artemisia absinthium）及其他草药、香料浸泡，并加入白兰地或中性酒精提高酒精度。味美思酒精度通常在 15%-22% 之间，含糖量从极干到甜润不等。

## 起源与历史

味美思起源于古希腊希波克拉底用苦艾浸泡葡萄酒的药用做法。现代味美思则诞生于 18 世纪末的意大利都灵。

- **1757 年**：意大利都灵的 Cinzano 仙山露创立
- **1786 年**：Antonio Benedetto Carpano 在都灵发明现代商业味美思
- **1813 年**：法国 Noilly Prat 创立，奠定干型法国味美思风格
- **1863 年**：Martini 马天尼品牌在都灵创立

19 世纪末到 20 世纪初，味美思成为鸡尾酒调酒的核心成分，与金酒搭配诞生了马天尼鸡尾酒。

## 分类与风格

按甜度与颜色分类：

1. **干味美思 Dry Vermouth**：白色，含糖低（≤5%），清爽带草本苦味，法国风格代表
2. **甜味美思 Sweet Vermouth**：红色或琥珀色，含糖高（10-15%），意大利风格代表
3. **白味美思 Bianco/White Vermouth**：介于干与甜之间，浅金色，香草甜感明显
4. **桃红味美思 Rosé**：浅粉色，介于干与甜之间的现代风格

按产区风格分类：
- **意大利风格**：甜润、浓郁香料感（甜/白）
- **法国风格**：干爽、海风矿物感（干）

## 风味特点

味美思是葡萄酒与草药酊剂的结合，风味复杂：
- **干味美思**：浅色，花香、青苹果、柑橘、苦艾尾韵
- **甜味美思**：深红色，焦糖、香草、肉桂、丁香、樱桃果酱
- **白味美思**：香草、八角、甘菊，温润甜柔

味美思开瓶后需冷藏保存，并尽快饮用（开瓶后建议 1-3 个月内），否则会氧化变味。

## 主要产区与代表品牌

主要产区：
- **意大利都灵**：现代味美思发源地，甜味美思代表
- **法国**：干味美思代表，Noilly Prat 与 Dolin 为主
- **西班牙**：具有较新的复古风格，如 Lacuesta

代表品牌：
- **马天尼 Martini**：意大利，全球最畅销味美思品牌
- **仙山露 Cinzano**：意大利，1757 年创立
- **Carpano**：意大利，味美思发明者品牌，Antica Formula 是顶级甜味美思
- **Dolin**：法国尚贝里产区，干型代表
- **Noilly Prat**：法国，1813 年创立，干型风格奠基者
- **Lillet**：法国波尔多，类似味美思但更果香，包括 Lillet Blanc/Rouge

## 经典鸡尾酒

味美思是经典鸡尾酒的灵魂伴侣：

- **马天尼 Martini**：金酒 + 干味美思，柠檬皮或橄榄装饰
- **尼格罗尼 Negroni**：金酒 + 金巴利 + 甜味美思
- **曼哈顿 Manhattan**：黑麦威士忌 + 甜味美思 + 安高天娜苦精
- **干曼哈顿 Dry Manhattan**：波本 + 干味美思
- **罗伯罗伊 Rob Roy**：苏格兰威士忌 + 甜味美思 + 苦精
- **史密斯柯林斯 Tom Collins**：老汤姆金酒 + 柠檬汁 + 糖 + 苏打 + 干味美思（可选）
""",
    },
    {
        "title": "糖浆与辅料百科",
        "content": """# 糖浆与辅料百科

调酒师手中除了烈酒与利口酒，糖浆与辅料是构建鸡尾酒风味与质感的核心元素。糖浆平衡酸度、增加圆润感；辅料如果汁、苏打、奶制品则丰富口感与层次。

## 糖浆分类

1. **单糖浆 Simple Syrup**：白糖与水 1:1 加热溶解，最常用。高档做法用 2:1（rich simple syrup）更甜更稠。
2. **蜂蜜糖浆 Honey Syrup**：蜂蜜与水 1:1 稀释（纯蜂蜜难以混合），可加入少许柠檬汁防腐。
3. **枫糖浆 Maple Syrup**：加拿大特产，1:1 稀释，赋予鸡尾酒焦糖木质感。
4. **水果糖浆 Fruit Syrup**：水果与糖熬煮过滤，如覆盆子糖浆（Grenadine 石榴糖浆属于此类）。
5. **金巴利糖浆 Campari Syrup**：将金巴利浓缩加糖，用于无酒精 Mocktail。
6. **肉桂糖浆 Cinnamon Syrup**：肉桂棒煮糖浆，用于 Tiki 风格鸡尾酒。
7. **生姜糖浆 Ginger Syrup**：新鲜姜煮糖浆，辛辣提神。
8. **焦糖糖浆 Demerara Syrup**：使用德梅拉拉糖，焦糖风味，Old Fashioned 经典用糖。

## 辅料分类

### 果汁类
- **柠檬汁 Lemon Juice**：黄色柠檬，酸度约 5-6%，鸡尾酒第一酸源
- **青柠汁 Lime Juice**：青柠，酸度更高且更清冽，Mojito/Margarita 用
- **橙汁 Orange Juice**：酸甜平衡，Screwdriver/Mimosa 用
- **西柚汁 Grapefruit Juice**：苦甜酸，Paloma/Sea Breeze 用
- **蔓越莓汁 Cranberry Juice**：红色酸甜，Cosmopolitan 用
- **番茄汁 Tomato Juice**：咸鲜，Bloody Mary 用

### 碳酸饮料
- **苏打水 Club Soda**：无味碳酸水，稀释与增加气泡
- **汤力水 Tonic Water**：含奎宁，苦甜感，金汤力用
- **姜啤 Ginger Beer**：辛辣碳酸，Moscow Mule/Dark 'n' Stormy 用
- **姜汁汽水 Ginger Ale**：温和姜味，Highball 用
- **可乐 Cola**：甜苦碳酸，朗姆可乐 Cuba Libre 用
- **雪碧/七喜 Sprite/7Up**：柠檬青柠甜碳酸

### 其他辅料
- **蛋白 Egg White**：增加绵密泡沫质感，Whiskey Sour/Pisco Sour 用
- **全蛋 Whole Egg**：Flip 类鸡尾酒用
- **奶油 Heavy Cream**：奶油鸡尾酒，Alexander 用
- **椰浆 Coconut Cream**：Piña Colada 用
- **薄荷 Fresh Mint**：Mojito/Julep 用，捣压释放香气
- **黑莓/覆盆子**：装饰与微调风味

## 用法与配比

调酒中常用"酸甜平衡"原则：糖浆与果汁按 1:1（或 2:1）配比。例如：
- 戴基里 Daiquiri：白朗姆 50ml + 青柠汁 25ml + 单糖浆 15ml
- 威士忌酸 Whiskey Sour：波本 60ml + 柠檬汁 25ml + 单糖浆 15ml + 蛋白 1 个

蛋白与全蛋需先 dry shake（不加冰摇和）以充分起泡，再加冰摇和。

## 保存方法

- **糖浆**：单糖浆常温可存 1-2 周，冷藏 1 个月。高糖比（2:1）保存更久。加入少量伏特加（10-20ml）可延长保质期。
- **蜂蜜糖浆**：冷藏 2-3 周。
- **水果糖浆**：冷藏 1-2 周，易发酵。
- **鲜榨果汁**：冷藏 24 小时内用完，柠檬/青柠汁冷冻可保存 1 个月。
- **蛋奶制品**：当天使用，避免隔夜。

所有糖浆建议使用玻璃瓶密封保存，避免塑料容器影响风味。
""",
    },
    {
        "title": "调酒器具百科",
        "content": """# 调酒器具百科

专业调酒师手中的器具，如同厨师手中的刀具，是构建鸡尾酒质感、温度、视觉的核心工具。从摇和到滤冰，每件器具都有特定用途。

## 摇酒壶 Shaker

摇酒壶是混合不易融合原料（如果汁、糖浆、蛋白、奶制品）的核心工具。

1. **波士顿摇酒壶 Boston Shaker**：两件套，金属大杯 + 玻璃调和杯（或两金属杯）。调酒师将玻璃杯倒扣在金属杯上，敲击密封。优点：容量大、操作快、专业首选。
2. **三段式摇酒壶 Cobbler Shaker**：金属壶身 + 内置滤网 + 顶盖。优点：自带滤网，便于家用；缺点：容量小、易堵塞。
3. **巴黎摇酒壶 Parisian Shaker**：两件全金属，外观优雅，类似波士顿但更圆润。法国高端酒吧常用，密封性极佳。

## 滤冰器 Strainer

滤冰器用于将摇和或搅拌后的酒液与冰块分离：

1. **霍桑滤冰器 Hawthorne Strainer**：金属丝圈滤网，专配金属调酒杯/波士顿摇酒壶。最常用。
2. **朱利普滤冰器 Julep Strainer**：浅碗状带孔勺，专配玻璃调和杯，常用于搅拌后滤酒。
3. **细网滤冰器 Fine Strainer / Tea Strainer**：双层细网，二次过滤碎冰与果肉，确保酒液纯净（Double Strain 双重过滤）。

## 量酒器 Jigger

量酒器是确保配方比例精确的核心器具：

- **基本款**：金属双头锥形，常见 30ml/60ml、25ml/50ml、15ml/30ml 组合
- **日本款**：细长精致，刻度精确，专业调酒师偏好
- **OZ 量杯**：1oz/2oz 配方使用的美式标准

精确量酒是专业调酒与家用调酒的根本区别之一。

## 吧勺 Bar Spoon

长柄螺旋吧勺（约 30cm），一端为小勺（量少量糖浆、捣樱桃），另一端为压扁器或叉（取橄榄/樱桃）。螺旋柄便于在杯中旋转搅拌。

## 捣碎器 Muddler

木质或金属的捣棒，用于捣压薄荷、柑橘、糖块释放香气。Mojito、Caipirinha、Old Fashioned（古法）必备。

## 其他器具

- **调和杯 Mixing Glass**：玻璃材质，用于 Stir 技法（曼哈顿、马天尼），容积 400-600ml
- **砧板 Cutting Board**：切割水果装饰
- **榨汁器 Citrus Juicer**：手动或电动榨柠檬/青柠
- **冰锥 Ice Pick**：雕刻大冰块
- **冰夹 Ice Tongs**：夹取冰块
- **吧刀 Paring Knife**：小型锋利刀，切果皮
- **冰模 Ice Mold**：制作大方形/球形冰块，缓慢融化降低稀释
- **喷壶 Atomizer**：装苦艾/苦精，喷洒装饰
- **酒嘴 Pour Spout**：控制倒酒速度与流量
- **细网筛 Fine Mesh Sieve**：双重过滤碎冰
- **温度计/比重计**：高级调酒实验室器具

## 器具保养

- 不锈钢器具使用后立即冲洗，避免氯水浸泡
- 玻璃调和杯避免骤冷骤热防止破裂
- 吧勺与量酒器定期抛光
- 摇酒壶密封圈定期更换，避免漏液
- 木质捣棒不可水洗浸泡，用湿布擦拭即可
""",
    },
    {
        "title": "调酒术语词典",
        "content": """# 调酒术语词典

调酒术语是国际通用的技法与流程术语，源于英语调酒传统。理解术语是读懂配方、复现经典鸡尾酒的基础。

## build 兑和/直接倒入

build（build in glass）是指将各原料直接倒入最终盛酒杯中，加入冰块后简单搅拌即可。不使用摇酒壶或调和杯。

适用：原料本身易融合（如烈酒 + 汤力水、烈酒 + 果汁），且希望保留碳酸气泡。

经典示例：
- 金汤力 Gin & Tonic
- 螺丝刀 Screwdriver
- 古典鸡尾酒 Old Fashioned

## stir 搅拌

stir 是将原料与冰块放入调和杯（Mixing Glass），用吧勺沿杯壁旋转搅拌 20-30 圈，使酒液冷却并适度稀释。

适用：全烈酒配方（无果汁/奶制品/糖浆黏稠原料），追求丝滑口感与清澈酒液。

经典示例：
- 马天尼 Martini
- 曼哈顿 Manhattan
- 马提尼兹 Martinez

## shake 摇和

shake 是将原料与冰块放入摇酒壶，双手用力摇晃 10-15 秒，使原料充分混合、冷却、稀释并注入空气。

适用：含果汁、糖浆、奶制品、蛋清的配方，需要强力混合与起泡。

经典示例：
- 戴基里 Daiquiri
- 玛格丽特 Margarita
- 威士忌酸 Whiskey Sour
- 蛋白类鸡尾酒

## blend 搅拌机

blend 是将原料与冰块放入电动搅拌机打成均匀冰沙状。热带与 Tiki 风格常用。

适用：Frozen 系列冰沙鸡尾酒。

经典示例：
- Frozen Daiquiri
- Frozen Margarita
- Piña Colada（部分版本）

## layer 分层

layer 是利用不同密度的液体，将原料一层层叠加，形成色彩分明的视觉层次。密度高的液体在下，密度低的在上。

常用工具：吧勺背引流，缓慢倒入。

经典示例：
- B-52（咖啡利口酒 + 爱尔兰奶油 + 橙味利口酒）
- Pousse Café
- 彩虹鸡尾酒 Rainbow

## muddle 捣压

muddle 是用捣碎器（Muddler）在杯中压碎新鲜水果、香草、糖块，释放香气与汁液。

适用：Mojito、Caipirinha、Old Fashioned（古法）。

注意：薄荷捣压需轻柔，避免释放苦味；柑橘类需切成块一同捣压。

## garnish 装饰

garnish 是在鸡尾酒最终加入的装饰物，提升视觉与嗅觉体验。

常见装饰：
- 柑橘皮扭 twist（释放精油）
- 樱桃 brandied cherry
- 橄榄 olive（马天尼）
- 薄荷枝 mint sprig
- 水果切片 fruit slice/wheel
- 盐边/糖边 rim

## float 漂浮

float 是将密度较低的液体缓慢倒在密度较高液体表面，形成漂浮层。

经典示例：
- Irish Coffee 顶部的奶油漂浮
- Tequila Sunrise 中红石榴糖浆下沉，橙汁上浮（反向应用）

## rim 杯口装饰

rim 是将杯口用柠檬/青柠片湿润后蘸取盐、糖、香料粉（如辣椒粉、可可粉）。

经典示例：
- Margarita 盐边
- Salty Dog 盐边
- Sugar Rim 糖边

## age 陈酿

age 指烈酒在橡木桶中陈年的过程。陈年时间影响色泽、香气、口感与价格。

常见标注：
- 威士忌：3 年、10 年、12 年、18 年、21 年
- 干邑：VS、VSOP、XO
- 朗姆酒：Blanco、Reposado、Añejo

## infuse 浸泡

infuse 是将风味原料（水果、香草、香料）浸泡在烈酒中，使其吸收风味的过程。

经典示例：
- 伏特加 + 辣椒 = 辣椒伏特加
- 朗姆酒 + 香草豆 = 香草朗姆
- 金酒 + 黄瓜/玫瑰 = Hendrick's 风格

浸泡时间因原料而异：柑橘皮 24 小时，香草 1-2 周，水果 3-7 天。
""",
    },
    {
        "title": "日本清酒 Sake 百科",
        "content": """# 日本清酒 Sake

日本清酒（Sake，日本酒 Nihonshu）是以米、米麹（Koji，米曲霉培养的米）与水为原料，经并行复发酵酿制而成的日本传统酒精饮料。酒精度通常在 15%-20% 之间。清酒被誉为"米之酒"，是日本国酒与文化象征之一。

## 起源与历史

清酒的历史可追溯至公元 3 世纪左右的弥生时代。最初的口嚼酒（由人咀嚼米饭吐出后发酵）是清酒的雏形。8 世纪奈良时代，米麹酿造法从中国传入日本，奠定了现代清酒工艺基础。

15 世纪室町时代，僧侣寺院酿造的"僧坊酒"工艺成熟。17 世纪江户时代，冬季酿造（寒造）成为主流，品质大幅提升。20 世纪明治时代引入酒税法与全国新酒鉴评会（1911 年起），确立了清酒评价体系。

二战时期米粮短缺，添加酿造酒精的"三倍增酿"清酒盛行，导致清酒品质声誉受损。1970 年代后，纯米酒与吟酿酒复兴，强调高品质米与精米工艺。

## 分类与风格

按精米步合（米磨去的比例）与是否添加酿造酒精分类：

1. **纯米酒 Junmai**：仅米、米麹、水，无添加酒精。精米步合无规定（通常 70% 以下）。米香浓郁。
2. **本酿造 Honjozo**：添加少量酿造酒精，精米步合 ≤ 70%。轻盈爽口。
3. **纯米吟酿酒 Junmai Ginjo**：精米步合 ≤ 60%，无添加酒精。果香华丽。
4. **吟酿酒 Ginjo**：精米步合 ≤ 60%，添加少量酒精。芳香细腻。
5. **纯米大吟酿酒 Junmai Daiginjo**：精米步合 ≤ 50%，无添加酒精。最高级清酒。
6. **大吟酿酒 Daiginjo**：精米步合 ≤ 50%，添加少量酒精。最高级清酒之一。

按风味特征分类：
- **熏酒 KUNSHU**：芳香的果香花酒（吟酿系）
- **爽酒 SOSHU**：清淡爽快（本酿造、普通酒）
- **醇酒 JUKUSHU**：浓郁的陈年香（古酒）
- **熟酒 JUKUSHU**：熟成香气复杂

## 精米步合 Seimaibuai

精米步合是清酒品质的核心指标，指米粒磨后剩余比例：
- **70%**：纯米酒、本酿造标准
- **60%**：吟酿系门槛
- **50%**：大吟酿门槛
- **35%**：顶级纯米大吟酿（如獭祭磨二割三分 23%）

磨米目的是去除米表层的蛋白质与脂肪，露出核心淀粉，使酒体更纯净芳香。精米过程极耗时，从 70% 到 35% 可能需 7 天以上。

## 主要产区与代表品牌

主要产区：
- **滩 Nada**（神户）：日本最大清酒产区，硬水"宫水"酿造，酒体强劲。代表：菊正宗、白鹤、富久娘
- **伏见 Fushimi**（京都）：中硬水，酒体优雅柔和。代表：月桂冠、黄樱
- **其他名产区**：广岛（贺茂鹤）、新潟（八海山、久保田）、秋田（高清水）、岩手（南部美人）

代表品牌：
- **獭祭 Dassai**：山口县旭酒造，纯米大吟酿代表，磨米二割三分（23%）
- **久保田 Kubota**：新潟县朝日酒造，千寿/万寿/八海山系
- **八海山 Hakkaisan**：新潟县八海酿造，爽快辛口代表
- **十四代 Juyondai**：山形县高木酒造，幻之酒
- **而今 Jikon**：三重县木屋正酒造，吟酿系热门
- **新政 Aramasa**：秋田县新政酒造，type 系列创新

## 风味特点

清酒风味因类别差异巨大：
- **纯米酒**：米香、旨味（鲜味）、五谷香气，浓郁饱满
- **本酿造**：清爽平衡，餐中酒首选
- **吟酿系**：哈密瓜、苹果、香蕉、洋梨等华丽果香（吟酿香 ginjo-ka）
- **古酒**：坚果、焦糖、酱油、咖喱等陈年复杂香

清酒同时具有"甘口"（甜）与"辛口"（不甜）的甜度划分，以及"淡丽"（轻）与"醇厚"（浓）的口感划分。

## 饮用温度

清酒是少数可冷可热饮用的酒类：

- **冷酒 Reishu**（5-15℃）：吟酿系首选，突出果香
- **常温 Jouon**（15-25℃）：纯米酒、本酿造，展现平衡
- **燗 Kan**：温热饮用
  - 日荣燗（30-40℃）：温和
  - 上燗（40-45℃）：经典温酒
  - 热燗 Atsukan（50-55℃）：冬季传统

不同温域展现不同风味层次，纯米酒与陈酒适合热燗，吟酿系宜冷饮。
""",
    },
    {
        "title": "韩国烧酒 Soju 百科",
        "content": """# 韩国烧酒 Soju

韩国烧酒（Soju，소주）是以米、小麦、大麦、甘薯、木薯等为原料，经发酵、蒸馏、稀释而成的韩国传统蒸馏酒。酒精度通常在 16.7%-25% 之间，是韩国国民酒类。烧酒是全球销量最大的蒸馏酒品类之一，年销量超过 30 亿瓶。

## 起源与历史

烧酒起源于 13 世纪高丽时代，由蒙古西征时从波斯带回的蒸馏技术（arak）传入朝鲜半岛。最早的烧酒称"阿剌吉"（arak 的音译），主要在开城与济州地区生产。

朝鲜王朝时期，烧酒由贵族与王室专用，原料以米为主。19 世纪末日据时期前，烧酒仍保持传统蒸馏法生产。

1965 年韩国政府颁布"粮食节约令"，禁止使用粮食酿造蒸馏酒，迫使厂家改用甘薯、木薯糖蜜等替代原料，并发展出"稀释式烧酒"（diluted soju）。这一时期真露 Jinro 崛起，成为韩国烧酒龙头品牌。

2000 年代后，米烧酒复兴，传统蒸馏法烧酒（如 Hwayo 和弘大烧酒）回归，并出现低酒精度（16-18%）与风味烧酒（柚子、葡萄柚、桃子等）潮流。

## 分类与风格

按工艺分类：

1. **稀释型烧酒 Diluted Soju（희석식 소주）**：以乙醇（来自甘薯/木薯糖蜜）稀释加水调配，加入甜味剂（麦芽糖醇、果糖）。主流烧酒，酒精度 16.7-25%。代表：真露 Chamisul、C1、Like First。
2. **蒸馏型烧酒 Distilled Soju（증류식 소주）**：以米、大麦等粮食直接发酵蒸馏，保留原料风味。传统工艺，酒精度 30-53%。代表：Hwayo 화요、Andong Soju 安东烧酒、Hongjo 홍조。

按风味分类：
- **原味烧酒**：无添加，纯净微甜
- **水果风味烧酒**：柚子、葡萄柚、桃子、青葡萄、苹果等
- **药用烧酒**：加入人参、灵芝等药材浸泡，如人参烧酒 Insamju

## 酒精度

韩国烧酒的主流酒精度在 16-25% 之间：
- **16-18%**：现代低度稀释烧酒，受年轻人与女性欢迎（真露 Chamisul Fresh 17.2%）
- **20-21%**：传统稀释烧酒标准（真露 Original 20.1%）
- **23-25%**：略高度数烧酒
- **30-45%**：传统蒸馏烧酒（Hwayo 41%）
- **40-53%**：安东烧酒等传统高酒精度版本

低度化是近年趋势，真露与好天好饮相继推出 16-17% 产品，更易入口。

## 主要产区与代表品牌

主要产区：
- **首尔/京畿**：稀释烧酒主要生产基地
- **安东 Andong**：传统蒸馏烧酒发源地，安东烧酒为韩国重要无形文化财
- **济州 Jeju**：以小米烧酒闻名，如汉拿山 Hallasan
- **釜山/庆尚**：C1 烧酒产地

代表品牌：
- **真露 Jinro**：1924 年创立，全球销量最大的烧酒品牌。Chamisul 系列是 flagship 产品
- **好天好饮 Chum Churum**：乐天酒业，以"初次一样"广告闻名，酒精度较低
- **C1（C1 Soju）**：釜山地区霸主，绵甜柔和
- **Jinro（真露）**：与 Chamisul 同公司，原始产品线
- **Hwayo 화요**：精品蒸馏米烧酒，35-53% 酒精度
- **Andong Soju 安东烧酒**：传统工艺，45-53% 高度数
- **Hallasan 汉拿山**：济州岛代表，21% 酒精度
- **Daesun 大巡**：釜山/庆尚南道地区

## 风味特点

- **稀释型烧酒**：纯净微甜，略带酒精温热感，几乎无风味特征。冷饮时口感清爽，与油腻韩国烤肉搭配绝佳。
- **蒸馏型烧酒**：米香明显，带有花香、谷物香，口感更复杂饱满，类似日本烧酎。
- **水果风味烧酒**：果香浓郁，甜度较高，易饮性强。

## 饮用文化

烧酒是韩国饮食与社交文化的核心：

- **饮法**：使用 50ml 小玻璃杯，常温饮用，配以烧酒壶（soju kettle）。先倒酒敬长辈，双手捧杯接受。
- **礼仪**：长辈递酒时需双手接杯，转身饮酒以示尊重。多人聚会时常"轮杯"分享同一瓶烧酒。
- **搭配**：与烤肉（烤五花肉、烤牛肉）、辣味料理（部队锅、辣炒年糕）等韩国料理绝佳搭配。烧酒解腻、降辣、平衡油腻感。
- **混合饮用**：
  - **烧啤 Somaek**：烧酒 + 啤酒 1:1 或 1:2 混合，韩国年轻人最流行的喝法
  - **烧酒炸弹 Poktanju**：将小杯烧酒投入大杯啤酒中一口饮尽
- **温度**：稀释型烧酒冷藏后饮用最佳；传统蒸馏烧酒可常温或微温。
- **SOJU 在全球**：随着韩流（K-pop、K-drama、K-food）传播，烧酒已成为亚洲酒类全球化的代表之一。
""",
    },
]


def _aggregate_flavor_profile(ingredients: list[str]) -> str:
    """聚合配方的风味标签。

    对每个材料名用 ``ingredients.canonicalize`` 归一化后查
    ``INGREDIENT_REGISTRY`` 的 ``tags``，收集所有 tags，去重（保留首次
    出现顺序），分号拼接。

    例如 ``["金酒","味美思"]`` → 金酒 tags
    ``["juniper","botanical","herbal","dry"]`` + 味美思 tags
    ``["botanical","aromatic","herbal","wine-fortified"]`` → 去重后
    ``"juniper;botanical;herbal;dry;aromatic;wine-fortified"``。

    未知材料（未注册）跳过，不影响其余材料聚合。
    """
    from hermes_kb.ingredients import canonicalize, get_tags

    tags: list[str] = []
    seen: set[str] = set()
    for name in ingredients:
        canonical = canonicalize(name)
        for tag in get_tags(canonical):
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return ";".join(tags)


def seed_recipes(importer: ImportService | None = None) -> dict[str, Any]:
    """导入 IBA 配方种子数据（幂等）。

    遍历 ``seed_recipes.SEED_RECIPES``（57 款 IBA 配方），对每款：
    1. 按标题查重，已存在则跳过（幂等，避免重复导入）
    2. 聚合 ``flavor_profile``（从 ``ingredients`` 的 tags 推导）
    3. 调用 ``ImportService.import_text`` 原子写入 doc + chunks + vectors
       以及结构化元数据（``technique``/``glassware``/``iba_category``
       /``flavor_profile``/``category="recipe"``/``source="iba"``）

    content 头部的 ``<!-- ingredients: a|b|c -->`` frontmatter 保持不变
    （RAG 解析兼容）。

    Args:
        importer: 可选的 ImportService 实例（用于测试注入）。为 None 时新建。

    Returns:
        汇总 dict：``{"seeded": int, "failed": int, "skipped": int,
        "items": list[dict]}``。
    """
    from sqlmodel import select

    from hermes_kb.database import get_session
    from hermes_kb.models import Document
    from hermes_kb.rag import ImportService
    from hermes_kb.seed_recipes import SEED_RECIPES

    if importer is None:
        importer = ImportService()

    seeded = 0
    failed = 0
    skipped = 0
    items: list[dict[str, Any]] = []

    for recipe in SEED_RECIPES:
        # 幂等：按标题查重
        with get_session() as session:
            existing = session.exec(
                select(Document).where(Document.title == recipe["title"])
            ).first()
            if existing:
                items.append(
                    {
                        "title": recipe["title"],
                        "status": "skipped",
                        "doc_id": existing.doc_id,
                    }
                )
                skipped += 1
                continue

        try:
            ingredients: list[str] = recipe.get("ingredients", [])
            flavor_profile = _aggregate_flavor_profile(ingredients)
            # 计算 ABV 档位：优先用 abv_override（Mocktail），否则估算
            abv_override = recipe.get("abv_override")
            if abv_override is not None:
                abv_bucket_value = classify_abv_bucket(float(abv_override))
            else:
                try:
                    stats = estimate_recipe_stats(ingredients)
                    abv_bucket_value = classify_abv_bucket(stats.get("estimated_abv", 0.0))
                except (KeyError, TypeError, ValueError):
                    abv_bucket_value = ""
            result = importer.import_text(
                content=recipe["content"],
                title=recipe["title"],
                source_type="seed",
                file_type="md",
                category="recipe",
                source="iba",
                technique=recipe.get("technique", ""),
                glassware=recipe.get("glassware", ""),
                iba_category=recipe.get("iba_category", ""),
                flavor_profile=flavor_profile,
                difficulty=recipe.get("difficulty", ""),
                abv_bucket=abv_bucket_value,
                season=recipe.get("season") or "",
            )
            seeded += 1
            items.append({**result, "status": "imported"})
        except (KeyError, TypeError, ValueError, RuntimeError, OSError) as e:  # 单条失败不阻塞其余配方导入
            failed += 1
            items.append(
                {
                    "title": recipe["title"],
                    "error": str(e),
                    "status": "failed",
                }
            )

    return {
        "seeded": seeded,
        "failed": failed,
        "skipped": skipped,
        "items": items,
    }


def seed_encyclopedia(importer: ImportService | None = None) -> dict[str, Any]:
    """导入百科种子数据（幂等）。

    遍历 ``SEED_DOCS`` 中每篇百科文档，按 ``title`` 在 Document 表查重，
    已存在则跳过；否则调用 ``ImportService.import_text`` 原子写入
    doc + chunks + vectors，``category="encyclopedia"``、``source="seed"``。

    Args:
        importer: 可选的 ImportService 实例（用于测试注入）。为 None 时新建。

    Returns:
        汇总 dict：``{"seeded": int, "failed": int, "skipped": int,
        "items": list[dict]}``。
    """
    from sqlmodel import select

    from hermes_kb.database import get_session
    from hermes_kb.models import Document
    from hermes_kb.rag import ImportService

    if importer is None:
        importer = ImportService()

    seeded = 0
    failed = 0
    skipped = 0
    items: list[dict[str, Any]] = []

    for doc in SEED_DOCS:
        title = doc["title"]
        content = doc["content"]

        with get_session() as session:
            existing = session.exec(
                select(Document).where(Document.title == title)
            ).first()
            if existing:
                items.append(
                    {
                        "title": title,
                        "status": "skipped",
                        "doc_id": existing.doc_id,
                    }
                )
                skipped += 1
                continue

        try:
            result = importer.import_text(
                content=content,
                title=title,
                source_type="seed",
                file_type="md",
                category="encyclopedia",
                source="seed",
            )
            seeded += 1
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
        "seeded": seeded,
        "failed": failed,
        "skipped": skipped,
        "items": items,
    }
