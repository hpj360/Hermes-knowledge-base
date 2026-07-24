"""IBA 经典鸡尾酒配方种子数据（50 款 IBA 全量）。

每款配方作为 Markdown 文档导入知识库（category=recipe）。
ingredients 字段为标准化材料名列表（用于匹配算法）。
content 开头的 HTML 注释 `<!-- ingredients: a|b|c -->` 为 A4-2 显式标注，
供 _parse_ingredients_from_frontmatter 优先解析，避免 title 反查与裸子串误匹配。

IBA 三大分类（iba_category 字段）：
- unforgettables: The Unforgettables 不朽经典
- contemporary_classics: Contemporary Classics 当代经典
- new_era_drinks: New Era Drinks 新时代

调酒技法（technique 字段）：
- build: 兑和（直接在杯中混合）
- stir: 搅拌（调酒杯中搅拌后过滤）
- shake: 摇和（摇酒壶摇匀）
- blend: 搅拌机打碎
- layer: 分层（沿吧匙缓缓倒入形成层次）
- muddle: 捣压（捣碎新鲜材料释放汁液）
"""
from __future__ import annotations

SEED_RECIPES: list[dict] = [
    # ============================================================
    # The Unforgettables 不朽经典（23 款）
    # ============================================================
    {
        "title": "马天尼 Martini",
        "base_spirit": "gin",
        "difficulty": "easy",
        "season": "autumn",
        "iba_category": "unforgettables",
        "technique": "stir",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "味美思", "橄榄"],
        "history": "起源众说纷纭，常见说法之一由 Jerry Thomas 于 1880 年代在加州 Martinez 镇创制，后演变为干型金酒版本。被誉为「鸡尾酒之王」。",
        "content": """<!-- ingredients: 金酒|味美思|橄榄 -->
# 马天尼 Martini

## 配方
- 金酒 60ml
- 干味美思 10ml
- 橄榄 1 颗（装饰）

## 步骤
1. 冰镇马天尼杯
2. 调酒杯加冰，倒入金酒与味美思
3. 搅拌 30 秒
4. 滤冰倒入杯中
5. 放入橄榄

## 风味
干爽、清冽、杜松子主导。被誉为「鸡尾酒之王」。

## 历史
起源众说纷纭，常见说法之一由 Jerry Thomas 于 1880 年代在加州 Martinez 镇创制，后演变为干型金酒版本。
""",
    },
    {
        "title": "尼格罗尼 Negroni",
        "base_spirit": "gin",
        "difficulty": "easy",
        "season": "autumn",
        "iba_category": "unforgettables",
        "technique": "build",
        "glassware": "古典杯",
        "ingredients": ["金酒", "金巴利", "味美思", "橙皮"],
        "history": "1919 年于意大利佛罗伦萨 Caffè Casoni，Count Camillo Negroni 要求将 Americano 中的苏打水换成金酒，调酒师 Fosco Scarselli 创制。",
        "content": """<!-- ingredients: 金酒|金巴利|味美思|橙皮 -->
# 尼格罗尼 Negroni

## 配方
- 金酒 30ml
- 金巴利 30ml
- 甜味美思 30ml
- 橙皮 1 片（装饰）

## 步骤
1. 古典杯加冰
2. 倒入金酒、金巴利、甜味美思
3. 搅拌 20 秒
4. 橙皮扭拧释放精油，装饰

## 风味
苦甜平衡、药草香、酒体饱满。等比经典。

## 历史
1919 年于意大利佛罗伦萨 Caffè Casoni，Count Camillo Negroni 要求将 Americano 中的苏打水换成金酒，调酒师 Fosco Scarselli 创制。
""",
    },
    {
        "title": "古典鸡尾酒 Old Fashioned",
        "base_spirit": "whiskey",
        "difficulty": "easy",
        "season": "winter",
        "iba_category": "unforgettables",
        "technique": "build",
        "glassware": "古典杯",
        "ingredients": ["威士忌", "糖浆", "苦精", "橙皮"],
        "history": "「古典」之名源于 19 世纪中叶调酒师对「老式」做法的回归——只用烈酒、糖、苦精、水。Pendennis Club 于 1880 年代使其复兴。",
        "content": """<!-- ingredients: 威士忌|糖浆|苦精|橙皮 -->
# 古典鸡尾酒 Old Fashioned

## 配方
- 波本威士忌 60ml
- 糖浆 5ml
- 苦精 2 滴
- 橙皮 1 片（装饰）

## 步骤
1. 古典杯加糖浆与苦精
2. 加冰块
3. 倒入威士忌
4. 搅拌 20 秒
5. 橙皮释放精油装饰

## 风味
醇厚、威士忌主导、微甜。最古老的经典配方之一。

## 历史
「古典」之名源于 19 世纪中叶调酒师对「老式」做法的回归——只用烈酒、糖、苦精、水。Pendennis Club 于 1880 年代使其复兴。
""",
    },
    {
        "title": "白色佳人 White Lady",
        "base_spirit": "gin",
        "difficulty": "medium",
        "season": "spring",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "君度", "柠檬汁"],
        "history": "1919 年由 Harry MacElhone 于伦敦 Ciro's Club 创制，初版用薄荷奶油，1929 年改为现今金酒+君度+柠檬汁的酸酒结构。",
        "content": """<!-- ingredients: 金酒|君度|柠檬汁 -->
# 白色佳人 White Lady

## 配方
- 金酒 40ml
- 君度 15ml
- 柠檬汁 20ml

## 步骤
1. 摇酒壶加冰
2. 倒入金酒、君度、柠檬汁
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
酸香优雅、杜松与橙香交织。酸酒变体经典。

## 历史
1919 年由 Harry MacElhone 于伦敦 Ciro's Club 创制，初版用薄荷奶油，1929 年改为现今金酒+君度+柠檬汁的酸酒结构。
""",
    },
    {
        "title": "亚历山大 Alexander",
        "base_spirit": "brandy",
        "difficulty": "easy",
        "season": "winter",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["白兰地", "可可力娇酒", "奶油"],
        "history": "一说由纽约 Rector's 餐厅调酒师 Troy Alexander 于 1915 年创制，纪念推销员 Phoebe Snow；一说源于 1920 年代禁酒令时期。",
        "content": """<!-- ingredients: 白兰地|可可力娇酒|奶油 -->
# 亚历山大 Alexander

## 配方
- 白兰地 30ml
- 可可力娇酒 30ml
- 奶油 30ml
- 肉豆蔻粉少许（装饰）

## 步骤
1. 摇酒壶加冰
2. 倒入白兰地、可可力娇酒、奶油
3. 充分摇匀 20 秒（乳化）
4. 滤冰倒入冰镇马天尼杯
5. 撒肉豆蔻粉装饰

## 风味
甜润丝滑、可可与白兰地交织、奶香浓郁。餐后经典。

## 历史
一说由纽约 Rector's 餐厅调酒师 Troy Alexander 于 1915 年创制，纪念推销员 Phoebe Snow；一说源于 1920 年代禁酒令时期。
""",
    },
    {
        "title": "美式 Americano",
        "base_spirit": "other",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "unforgettables",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["金巴利", "味美思", "苏打水", "橙皮"],
        "history": "1860 年代由 Gaspare Campari 在米兰 Caffè Camparino 创制，初名「Milano-Torino」，后因美国游客流行而改名 Americano。Negroni 的前身。",
        "content": """<!-- ingredients: 金巴利|味美思|苏打水|橙皮 -->
# 美式 Americano

## 配方
- 金巴利 30ml
- 甜味美思 30ml
- 苏打水 适量
- 橙皮 1 片（装饰）

## 步骤
1. 高球杯加冰
2. 倒入金巴利与甜味美思
3. 注入苏打水至八分满
4. 轻轻搅拌
5. 橙皮装饰

## 风味
苦甜清爽、气泡轻盈、低酒精度。夏日开胃经典。

## 历史
1860 年代由 Gaspare Campari 在米兰 Caffè Camparino 创制，初名「Milano-Torino」，后因美国游客流行而改名 Americano。Negroni 的前身。
""",
    },
    {
        "title": "飞行 Aviation",
        "base_spirit": "gin",
        "difficulty": "hard",
        "season": "spring",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "黑樱桃力娇酒", "柠檬汁", "紫罗兰力娇酒"],
        "history": "1916 年由 Hugo Ensslin 于纽约 Hotel Wallick 首创，配方载于其 1917 年《Recipes for Mixed Drinks》。紫罗兰力娇酒赋予天空淡紫色，故名「飞行」。",
        "content": """<!-- ingredients: 金酒|黑樱桃力娇酒|柠檬汁|紫罗兰力娇酒 -->
# 飞行 Aviation

## 配方
- 金酒 45ml
- 黑樱桃力娇酒 7.5ml
- 柠檬汁 15ml
- 紫罗兰力娇酒 7.5ml

## 步骤
1. 摇酒壶加冰
2. 倒入金酒、黑樱桃力娇酒、柠檬汁、紫罗兰力娇酒
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
花香酸甜、淡紫色泽、杜松基底。极具诗意。

## 历史
1916 年由 Hugo Ensslin 于纽约 Hotel Wallick 首创，配方载于其 1917 年《Recipes for Mixed Drinks》。紫罗兰力娇酒赋予天空淡紫色，故名「飞行」。
""",
    },
    {
        "title": "床第之间 Between the Sheets",
        "base_spirit": "rum",
        "difficulty": "medium",
        "season": "autumn",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["白朗姆酒", "干邑白兰地", "君度", "柠檬汁"],
        "history": "1920-30 年代禁酒令时期巴黎 Harry's New York Bar 创制，传闻由「鸡尾酒王子」 Frank Meier 调制。Sidecar 的双烈酒变体。",
        "content": """<!-- ingredients: 白朗姆酒|干邑白兰地|君度|柠檬汁 -->
# 床第之间 Between the Sheets

## 配方
- 白朗姆酒 20ml
- 干邑白兰地 20ml
- 君度 20ml
- 柠檬汁 20ml

## 步骤
1. 摇酒壶加冰
2. 倒入白朗姆酒、干邑白兰地、君度、柠檬汁
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
烈度较高、双烈酒交织、柑橘酸香平衡。Sidecar 升级版。

## 历史
1920-30 年代禁酒令时期巴黎 Harry's New York Bar 创制，传闻由「鸡尾酒王子」 Frank Meier 调制。Sidecar 的双烈酒变体。
""",
    },
    {
        "title": "林荫道 Boulevardier",
        "base_spirit": "whiskey",
        "difficulty": "easy",
        "season": "autumn",
        "iba_category": "unforgettables",
        "technique": "build",
        "glassware": "古典杯",
        "ingredients": ["波本威士忌", "金巴利", "味美思", "橙皮"],
        "history": "1927 年由 Erskine Gwynne 在巴黎创办的同名杂志《Boulevardier》期间创制，配方首发于 1929 年 McElhone《Barflies and Cocktails》。Negroni 的波本变体。",
        "content": """<!-- ingredients: 波本威士忌|金巴利|味美思|橙皮 -->
# 林荫道 Boulevardier

## 配方
- 波本威士忌 45ml
- 金巴利 30ml
- 甜味美思 30ml
- 橙皮 1 片（装饰）

## 步骤
1. 古典杯加冰
2. 倒入波本、金巴利、甜味美思
3. 搅拌 20 秒
4. 橙皮扭拧装饰

## 风味
苦甜醇厚、波本甜香、Negroni 的威士忌版。秋冬首选。

## 历史
1927 年由 Erskine Gwynne 在巴黎创办的同名杂志《Boulevardier》期间创制，配方首发于 1929 年 McElhone《Barflies and Cocktails》。Negroni 的波本变体。
""",
    },
    {
        "title": "三叶草俱乐部 Clover Club",
        "base_spirit": "gin",
        "difficulty": "medium",
        "season": "spring",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "柠檬汁", "红石榴糖浆", "蛋清"],
        "history": "费城三叶草俱乐部（Clover Club）于 1890-1900 年代间创制，该俱乐部汇集记者、律师、文人。禁酒令后失传，2000 年代纽约复兴。",
        "content": """<!-- ingredients: 金酒|柠檬汁|红石榴糖浆|蛋清 -->
# 三叶草俱乐部 Clover Club

## 配方
- 金酒 45ml
- 柠檬汁 15ml
- 红石榴糖浆 15ml
- 蛋清 1 个

## 步骤
1. 摇酒壶加冰
2. 倒入金酒、柠檬汁、红石榴糖浆、蛋清
3. 先干摇（无冰）10 秒乳化蛋清
4. 再加冰摇 15 秒
5. 双层滤冰倒入冰镇马天尼杯

## 风味
酸甜柔滑、粉红泡沫、杜松底蕴。维多利亚时代遗珠。

## 历史
费城三叶草俱乐部（Clover Club）于 1890-1900 年代间创制，该俱乐部汇集记者、律师、文人。禁酒令后失传，2000 年代纽约复兴。
""",
    },
    {
        "title": "戴基里 Daiquiri",
        "base_spirit": "rum",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["白朗姆酒", "柠檬汁", "糖浆"],
        "history": "1898 年由美国工程师 Jennings Cox 在古巴 Daiquirí 矿场创制，因琴酒断货用朗姆酒替代。海明威在哈瓦那 El Floridita 推广成名。",
        "content": """<!-- ingredients: 白朗姆酒|柠檬汁|糖浆 -->
# 戴基里 Daiquiri

## 配方
- 白朗姆酒 45ml
- 柠檬汁 20ml
- 糖浆 15ml

## 步骤
1. 摇酒壶加冰
2. 倒入白朗姆酒、柠檬汁、糖浆
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
酸甜清爽、朗姆甜香、纯粹平衡。酸酒典范。

## 历史
1898 年由美国工程师 Jennings Cox 在古巴 Daiquirí 矿场创制，因琴酒断货用朗姆酒替代。海明威在哈瓦那 El Floridita 推广成名。
""",
    },
    {
        "title": "金菲士 Gin Fizz",
        "base_spirit": "gin",
        "difficulty": "medium",
        "season": "summer",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "高球杯",
        "ingredients": ["金酒", "柠檬汁", "糖浆", "苏打水"],
        "history": "1888 年首次记录于 Harry Johnson《Bartenders' Manual》。新奥尔良 Ramos Gin Fizz（1888）为其变体，加入奶油与橙花水。",
        "content": """<!-- ingredients: 金酒|柠檬汁|糖浆|苏打水 -->
# 金菲士 Gin Fizz

## 配方
- 金酒 45ml
- 柠檬汁 20ml
- 糖浆 15ml
- 苏打水 适量

## 步骤
1. 摇酒壶加冰
2. 倒入金酒、柠檬汁、糖浆
3. 摇匀 15 秒
4. 滤冰倒入高球杯
5. 注入苏打水至满，轻轻搅拌

## 风味
酸甜气泡、杜松清香、轻盈爽口。午后经典长饮。

## 历史
1888 年首次记录于 Harry Johnson《Bartenders' Manual》。新奥尔良 Ramos Gin Fizz（1888）为其变体，加入奶油与橙花水。
""",
    },
    {
        "title": "汉基帕基 Hanky Panky",
        "base_spirit": "gin",
        "difficulty": "medium",
        "season": "autumn",
        "iba_category": "unforgettables",
        "technique": "stir",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "味美思", "菲奈特"],
        "history": "1925 年由伦敦 Savoy 酒店 Ada «Coley» Coleman 调制，为喜剧演员 Charles Hawtrey 创制。Hawtrey 喝后惊呼「By Jove! That is the real hanky-panky!»",
        "content": """<!-- ingredients: 金酒|味美思|菲奈特 -->
# 汉基帕基 Hanky Panky

## 配方
- 金酒 45ml
- 甜味美思 45ml
- 菲奈特 2 滴（dash）
- 橙皮 1 片（装饰）

## 步骤
1. 调酒杯加冰
2. 倒入金酒、甜味美思、菲奈特
3. 搅拌 20 秒
4. 滤冰倒入冰镇马天尼杯
5. 橙皮扭拧装饰

## 风味
苦甜复杂、药草深沉、Martinez 与苦精的合体。低女调酒师签名款。

## 历史
1925 年由伦敦 Savoy 酒店 Ada «Coley» Coleman 调制，为喜剧演员 Charles Hawtrey 创制。Hawtrey 喝后惊呼「By Jove! That is the real hanky-panky!」
""",
    },
    {
        "title": "约翰柯林斯 John Collins",
        "base_spirit": "whiskey",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "unforgettables",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["威士忌", "柠檬汁", "糖浆", "苏打水"],
        "history": "1800 年代伦敦 Limmer's Old House 头牌侍者 John Collins 创制，初用荷兰金酒。后威士忌版（Tom Collins）流行，二者常互换。",
        "content": """<!-- ingredients: 威士忌|柠檬汁|糖浆|苏打水 -->
# 约翰柯林斯 John Collins

## 配方
- 威士忌 45ml
- 柠檬汁 20ml
- 糖浆 15ml
- 苏打水 适量
- 樱桃 1 颗 + 柠檬片（装饰）

## 步骤
1. 高球杯加冰
2. 倒入威士忌、柠檬汁、糖浆
3. 搅拌均匀
4. 注入苏打水至满
5. 樱桃与柠檬片装饰

## 风味
酸甜气泡、威士忌温暖、清爽长饮。Collins 系列代表。

## 历史
1800 年代伦敦 Limmer's Old House 头牌侍者 John Collins 创制，初用荷兰金酒。后威士忌版（Tom Collins）流行，二者常互换。
""",
    },
    {
        "title": "最后一言 Last Word",
        "base_spirit": "gin",
        "difficulty": "medium",
        "season": "spring",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "樱桃力娇酒", "绿查特酒", "柠檬汁"],
        "history": "禁酒令前夕底特律 Athletic Club 调酒师 Frank Fogarty 创制，1916 年配方载于 Ted Saucier 1951 年《Bottoms Up》。2004 年西雅图 Murray Stenson 复兴。",
        "content": """<!-- ingredients: 金酒|樱桃力娇酒|绿查特酒|柠檬汁 -->
# 最后一言 Last Word

## 配方
- 金酒 22.5ml
- 樱桃力娇酒 22.5ml
- 绿查特酒 22.5ml
- 柠檬汁 22.5ml

## 步骤
1. 摇酒壶加冰
2. 倒入金酒、樱桃力娇酒、绿查特酒、柠檬汁
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
等比四味、草本复杂、酸甜平衡。禁酒令时代瑰宝。

## 历史
禁酒令前夕底特律 Athletic Club 调酒师 Frank Fogarty 创制，1916 年配方载于 Ted Saucier 1951 年《Bottoms Up》。2004 年西雅图 Murray Stenson 复兴。
""",
    },
    {
        "title": "曼哈顿 Manhattan",
        "base_spirit": "whiskey",
        "difficulty": "easy",
        "season": "autumn",
        "iba_category": "unforgettables",
        "technique": "stir",
        "glassware": "马天尼杯",
        "ingredients": ["黑麦威士忌", "味美思", "苦精", "樱桃"],
        "history": "1874 年纽约 Manhattan Club 为英国首相丘吉尔之母 Jennie Jerome 举办的宴会创制（一说为 Dr. Iain Marshall 调制）。被誉为「鸡尾酒之后」。",
        "content": """<!-- ingredients: 黑麦威士忌|味美思|苦精|樱桃 -->
# 曼哈顿 Manhattan

## 配方
- 黑麦威士忌 50ml
- 甜味美思 20ml
- 苦精 2 滴
- 樱桃 1 颗（装饰）

## 步骤
1. 调酒杯加冰
2. 倒入黑麦威士忌、甜味美思、苦精
3. 搅拌 20 秒
4. 滤冰倒入冰镇马天尼杯
5. 樱桃装饰

## 风味
醇厚甘甜、威士忌主导、味美思增香。Dry/Sweet/Perfect 三种变体。

## 历史
1874 年纽约 Manhattan Club 为英国首相丘吉尔之母 Jennie Jerome 举办的宴会创制（一说为 Dr. Iain Marshall 调制）。被誉为「鸡尾酒之后」。
""",
    },
    {
        "title": "马天尼内兹 Martinez",
        "base_spirit": "gin",
        "difficulty": "medium",
        "season": "autumn",
        "iba_category": "unforgettables",
        "technique": "stir",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "味美思", "黑樱桃力娇酒", "苦精"],
        "history": "由 Jerry Thomas 于 1880 年代在加州 Martinez 镇创制，载于其 1887 年《Bartender's Guide》。Martini 的前身，更甜更复杂。",
        "content": """<!-- ingredients: 金酒|味美思|黑樱桃力娇酒|苦精 -->
# 马天尼内兹 Martinez

## 配方
- 金酒 30ml
- 甜味美思 30ml
- 黑樱桃力娇酒 5ml
- 苦精 1 滴
- 柠檬皮 1 片（装饰）

## 步骤
1. 调酒杯加冰
2. 倒入金酒、甜味美思、黑樱桃力娇酒、苦精
3. 搅拌 20 秒
4. 滤冰倒入冰镇马天尼杯
5. 柠檬皮扭拧装饰

## 风味
甜润复杂、味美思主导、Maraschino 增香。Martini 的祖父。

## 历史
由 Jerry Thomas 于 1880 年代在加州 Martinez 镇创制，载于其 1887 年《Bartender's Guide》。Martini 的前身，更甜更复杂。
""",
    },
    {
        "title": "玛丽碧克馥 Mary Pickford",
        "base_spirit": "rum",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["白朗姆酒", "菠萝汁", "红石榴糖浆", "黑樱桃力娇酒"],
        "history": "1920 年代古巴哈瓦那 Hotel Nacional 调酒师 Eddie Woelke 为好莱坞女星 Mary Pickford 创制。粉红色泽与明星效应使其成为禁酒令时期热门。",
        "content": """<!-- ingredients: 白朗姆酒|菠萝汁|红石榴糖浆|黑樱桃力娇酒 -->
# 玛丽碧克馥 Mary Pickford

## 配方
- 白朗姆酒 45ml
- 菠萝汁 45ml
- 红石榴糖浆 5ml
- 黑樱桃力娇酒 5ml

## 步骤
1. 摇酒壶加冰
2. 倒入白朗姆酒、菠萝汁、红石榴糖浆、黑樱桃力娇酒
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
甜美热带、粉红色泽、菠萝主导。明星禁酒令时代名饮。

## 历史
1920 年代古巴哈瓦那 Hotel Nacional 调酒师 Eddie Woelke 为好莱坞女星 Mary Pickford 创制。粉红色泽与明星效应使其成为禁酒令时期热门。
""",
    },
    {
        "title": "种植者宾治 Planter's Punch",
        "base_spirit": "rum",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "高球杯",
        "ingredients": ["陈年朗姆酒", "柠檬汁", "橙汁", "红石榴糖浆", "糖浆", "苦精"],
        "history": "源自 19 世纪牙买加种植园主招待客人的传统配方，1908 年首载于《New York Times》。口诀「一份酸、二份甜、三份烈、四份弱」。",
        "content": """<!-- ingredients: 陈年朗姆酒|柠檬汁|橙汁|红石榴糖浆|糖浆|苦精 -->
# 种植者宾治 Planter's Punch

## 配方
- 陈年朗姆酒 45ml
- 橙汁 30ml
- 柠檬汁 15ml
- 红石榴糖浆 10ml
- 糖浆 10ml
- 苦精 2 滴

## 步骤
1. 摇酒壶加冰
2. 倒入陈年朗姆酒、橙汁、柠檬汁、红石榴糖浆、糖浆、苦精
3. 摇匀 15 秒
4. 滤冰倒入装满冰的高球杯
5. 橙片与樱桃装饰

## 风味
热带果香、酸甜平衡、朗姆甜润。加勒比经典。

## 历史
源自 19 世纪牙买加种植园主招待客人的传统配方，1908 年首载于《New York Times》。口诀「一份酸、二份甜、三份烈、四份弱」。
""",
    },
    {
        "title": "拉莫斯菲士 Ramos Gin Fizz",
        "base_spirit": "gin",
        "difficulty": "hard",
        "season": "spring",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "高球杯",
        "ingredients": ["金酒", "柠檬汁", "青柠汁", "糖浆", "奶油", "蛋清", "橙花水", "苏打水"],
        "history": "1888 年新奥尔良 Imperial Cabinet Saloon 的 Henry C. Ramos 创制，需摇 12 分钟以上起泡。曾雇佣 20+ 摇酒师专职制作，轰动一时。",
        "content": """<!-- ingredients: 金酒|柠檬汁|青柠汁|糖浆|奶油|蛋清|橙花水|苏打水 -->
# 拉莫斯菲士 Ramos Gin Fizz

## 配方
- 金酒 45ml
- 柠檬汁 10ml
- 青柠汁 10ml
- 糖浆 30ml
- 奶油 30ml
- 蛋清 1 个
- 橙花水 2 滴
- 苏打水 适量

## 步骤
1. 摇酒壶加冰与所有液体材料（除苏打水）
2. 干摇 30 秒乳化
3. 加冰摇 2 分钟以上（关键起泡）
4. 滤冰倒入高球杯
5. 注入少量苏打水

## 风味
绵密泡沫、花香奶甜、杜松底蕴。耗时极致的经典。

## 历史
1888 年新奥尔良 Imperial Cabinet Saloon 的 Henry C. Ramos 创制，需摇 12 分钟以上起泡。曾雇佣 20+ 摇酒师专职制作，轰动一时。
""",
    },
    {
        "title": "萨泽拉克 Sazerac",
        "base_spirit": "whiskey",
        "difficulty": "medium",
        "season": "winter",
        "iba_category": "unforgettables",
        "technique": "stir",
        "glassware": "古典杯",
        "ingredients": ["干邑白兰地", "苦精", "糖浆", "苦艾烈酒"],
        "history": "1838 年新奥尔良 Antoine Amedie Peychaud 调酒师创制，用 Sazerac de Forge et Fils 干邑。1890 年代改用黑麦威士忌。新奥尔良官方鸡尾酒。",
        "content": """<!-- ingredients: 干邑白兰地|苦精|糖浆|苦艾烈酒 -->
# 萨泽拉克 Sazerac

## 配方
- 干邑白兰地 50ml
- 苦精 3 滴
- 糖浆 5ml
- 苦艾烈酒 5ml（洗杯）

## 步骤
1. 古典杯加冰与苦艾烈酒，洗杯后倒掉
2. 调酒杯加冰
3. 倒入干邑、糖浆、苦精搅拌 20 秒
4. 滤冰倒入洗过苦艾酒的杯中
5. 柠檬皮扭拧装饰

## 风味
干邑醇香、苦艾回韵、Peychaud 苦精特有的红色果香。新奥尔良之魂。

## 历史
1838 年新奥尔良 Antoine Amedie Peychaud 调酒师创制，用 Sazerac de Forge et Fils 干邑。1890 年代改用黑麦威士忌。新奥尔良官方鸡尾酒。
""",
    },
    {
        "title": "边车 Sidecar",
        "base_spirit": "brandy",
        "difficulty": "medium",
        "season": "autumn",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["干邑白兰地", "君度", "柠檬汁"],
        "history": "一战末期巴黎 Harry's New York Bar 或伦敦 Buck's Club 创制（双方均自称）。名字源于一战边车摩托车军官。Margarita 的白兰地原型。",
        "content": """<!-- ingredients: 干邑白兰地|君度|柠檬汁 -->
# 边车 Sidecar

## 配方
- 干邑白兰地 50ml
- 君度 20ml
- 柠檬汁 20ml
- 糖边（可选）

## 步骤
1. 马天尼杯蘸糖边（可选）
2. 摇酒壶加冰
3. 倒入干邑、君度、柠檬汁
4. 摇匀 15 秒
5. 滤冰倒入杯中

## 风味
干邑果香、橙香酸度、平衡优雅。白兰地酸酒典范。

## 历史
一战末期巴黎 Harry's New York Bar 或伦敦 Buck's Club 创制（双方均自称）。名字源于一战边车摩托车军官。Margarita 的白兰地原型。
""",
    },
    {
        "title": "威士忌酸 Whiskey Sour",
        "base_spirit": "whiskey",
        "difficulty": "easy",
        "season": "spring",
        "iba_category": "unforgettables",
        "technique": "shake",
        "glassware": "古典杯",
        "ingredients": ["波本威士忌", "柠檬汁", "糖浆", "蛋清", "苦精"],
        "history": "1862 年 Jerry Thomas《Bartender's Guide》首载其原型。 sailors 中流传的「Grog」演化而来，是 Sour 系列的鼻祖。",
        "content": """<!-- ingredients: 波本威士忌|柠檬汁|糖浆|蛋清|苦精 -->
# 威士忌酸 Whiskey Sour

## 配方
- 波本威士忌 50ml
- 柠檬汁 25ml
- 糖浆 15ml
- 蛋清 1 个（可选）
- 苦精 2 滴
- 樱桃 + 橙片（装饰）

## 步骤
1. 摇酒壶加冰
2. 倒入波本、柠檬汁、糖浆、蛋清、苦精
3. 干摇 10 秒乳化蛋清
4. 加冰摇 15 秒
5. 滤冰倒入古典杯，樱桃与橙片装饰

## 风味
酸甜平衡、波本甜香、蛋白泡沫丝滑。Sour 系列鼻祖。

## 历史
1862 年 Jerry Thomas《Bartender's Guide》首载其原型。 sailors 中流传的「Grog」演化而来，是 Sour 系列的鼻祖。
""",
    },
    # ============================================================
    # Contemporary Classics 当代经典（24 款）
    # ============================================================
    {
        "title": "莫吉托 Mojito",
        "base_spirit": "rum",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "muddle",
        "glassware": "高球杯",
        "ingredients": ["白朗姆酒", "青柠汁", "糖浆", "薄荷叶", "苏打水"],
        "history": "源自 16 世纪古巴海盗 Francis Drake 的「El Draque」配方（用 aguardiente + 薄荷 + 青柠）。1860 年代改用朗姆酒，名字源自 mojo 调味料。",
        "content": """<!-- ingredients: 白朗姆酒|青柠汁|糖浆|薄荷叶|苏打水 -->
# 莫吉托 Mojito

## 配方
- 白朗姆酒 45ml
- 青柠汁 20ml
- 糖浆 15ml
- 薄荷叶 8-10 片
- 苏打水 适量

## 步骤
1. 薄荷叶与糖浆放入杯中轻轻捣压
2. 加入青柠汁与朗姆酒
3. 加碎冰至八分满
4. 注入苏打水至满
5. 搅拌提升，以薄荷枝装饰

## 风味
清新、薄荷凉爽、酸甜平衡。夏日经典长饮。

## 历史
源自 16 世纪古巴海盗 Francis Drake 的「El Draque」配方（用 aguardiente + 薄荷 + 青柠）。1860 年代改用朗姆酒，名字源自 mojo 调味料。
""",
    },
    {
        "title": "玛格丽特 Margarita",
        "base_spirit": "tequila",
        "difficulty": "medium",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["龙舌兰", "君度", "青柠汁", "柠檬片"],
        "history": "1948 年达拉斯社交名媛 Margarita Sames 在 Acapulco 别墅为客人创制。另一说 1938 年 Tijuana 调酒师 Carlos «Danny» Herrera 为过敏除龙舌兰外烈酒的舞女创制。",
        "content": """<!-- ingredients: 龙舌兰|君度|青柠汁|柠檬片 -->
# 玛格丽特 Margarita

## 配方
- 龙舌兰 50ml
- 君度 20ml
- 青柠汁 20ml
- 盐边 + 柠檬片装饰

## 步骤
1. 杯口蘸半圈盐边
2. 冰块加入摇酒壶
3. 倒入龙舌兰、君度、青柠汁
4. 摇匀 15 秒
5. 滤入盐边杯，柠檬片装饰

## 风味
酸甜咸三味平衡，龙舌兰植物香突出。墨西哥国饮。

## 历史
1948 年达拉斯社交名媛 Margarita Sames 在 Acapulco 别墅为客人创制。另一说 1938 年 Tijuana 调酒师 Carlos «Danny» Herrera 为过敏除龙舌兰外烈酒的舞女创制。
""",
    },
    {
        "title": "龙舌兰日出 Tequila Sunrise",
        "base_spirit": "tequila",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["龙舌兰", "橙汁", "红石榴糖浆"],
        "history": "1970 年代 Sausalito California 调酒师 Billy Rice 与 Bobby Lazoff 创制，灵感来自 1930 年代墨西哥版本（用 crème de cassis）。滚石乐队 1972 年巡演推波助澜。",
        "content": """<!-- ingredients: 龙舌兰|橙汁|红石榴糖浆 -->
# 龙舌兰日出 Tequila Sunrise

## 配方
- 龙舌兰 45ml
- 橙汁 90ml
- 红石榴糖浆 15ml

## 步骤
1. 高球杯加冰
2. 倒入龙舌兰与橙汁，搅拌
3. 沿杯壁缓缓倒入红石榴糖浆
4. 使其沉底形成日出渐层
5. 饮用前搅拌

## 风味
果香甜美、视觉渐层。日出色彩由此得名。

## 历史
1970 年代 Sausalito California 调酒师 Billy Rice 与 Bobby Lazoff 创制，灵感来自 1930 年代墨西哥版本（用 crème de cassis）。滚石乐队 1972 年巡演推波助澜。
""",
    },
    {
        "title": "贝里尼 Bellini",
        "base_spirit": "other",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["普罗塞克", "蜜桃泥"],
        "history": "1948 年威尼斯 Harry's Bar 老板 Giuseppe Cipriani 创制，以意大利画家 Giovanni Bellini 命名（其画作色彩与鸡尾酒粉色相同）。",
        "content": """<!-- ingredients: 普罗塞克|蜜桃泥 -->
# 贝里尼 Bellini

## 配方
- 普罗塞克 90ml
- 白蜜桃泥 30ml

## 步骤
1. 高球杯冷藏
2. 倒入白蜜桃泥
3. 缓缓注入冰镇普罗塞克
4. 轻轻搅拌

## 风味
果香细腻、气泡清新、低酒精优雅。Brunch 经典。

## 历史
1948 年威尼斯 Harry's Bar 老板 Giuseppe Cipriani 创制，以意大利画家 Giovanni Bellini 命名（其画作色彩与鸡尾酒粉色相同）。
""",
    },
    {
        "title": "黑色俄罗斯 Black Russian",
        "base_spirit": "vodka",
        "difficulty": "easy",
        "season": "winter",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "古典杯",
        "ingredients": ["伏特加", "咖啡力娇酒"],
        "history": "1949 年布鲁塞尔 Hotel Metropole 调酒师 Gustave Tops 为美国驻卢森堡大使 Perle Mesta 创制。黑色俄罗斯之名为冷战时期印记。",
        "content": """<!-- ingredients: 伏特加|咖啡力娇酒 -->
# 黑色俄罗斯 Black Russian

## 配方
- 伏特加 50ml
- 咖啡力娇酒 20ml

## 步骤
1. 古典杯加冰
2. 倒入伏特加与咖啡力娇酒
3. 轻轻搅拌

## 风味
咖啡甜香、伏特加纯净、酒体厚实。餐后经典。

## 历史
1949 年布鲁塞尔 Hotel Metropole 调酒师 Gustave Tops 为美国驻卢森堡大使 Perle Mesta 创制。黑色俄罗斯之名为冷战时期印记。
""",
    },
    {
        "title": "荆棘 Bramble",
        "base_spirit": "gin",
        "difficulty": "medium",
        "season": "spring",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "古典杯",
        "ingredients": ["金酒", "柠檬汁", "糖浆", "黑加仑力娇酒"],
        "history": "1984 年伦敦 Fred's Club 调酒师 Dick Bradsell 创制，灵感来自传统 crème de mure 调酒。英国现代调酒复兴代表作。",
        "content": """<!-- ingredients: 金酒|柠檬汁|糖浆|黑加仑力娇酒 -->
# 荆棘 Bramble

## 配方
- 金酒 50ml
- 柠檬汁 25ml
- 糖浆 15ml
- 黑加仑力娇酒 15ml
- 黑莓 + 柠檬皮（装饰）

## 步骤
1. 摇酒壶加冰
2. 倒入金酒、柠檬汁、糖浆
3. 摇匀 15 秒
4. 滤入装碎冰的古典杯
5. 沿吧匙缓缓倒入黑加仑力娇酒形成纹理
6. 黑莓与柠檬皮装饰

## 风味
莓果酸甜、杜松清香、视觉纹理。英式现代经典。

## 历史
1984 年伦敦 Fred's Club 调酒师 Dick Bradsell 创制，灵感来自传统 crème de mure 调酒。英国现代调酒复兴代表作。
""",
    },
    {
        "title": "卡布琳娜 Caipirinha",
        "base_spirit": "other",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "muddle",
        "glassware": "古典杯",
        "ingredients": ["卡沙萨", "青柠", "白糖"],
        "history": "巴西国饮，起源于 19 世纪圣保罗农场工人用 cachaça + 青柠 + 糖治感冒的偏方。名字源于葡萄牙语「caipira」（乡下人）。",
        "content": """<!-- ingredients: 卡沙萨|青柠|白糖 -->
# 卡布琳娜 Caipirinha

## 配方
- 卡沙萨 60ml
- 青柠 1 个（切角）
- 白糖 2 茶匙

## 步骤
1. 青柠角放入古典杯
2. 加白糖，用捣棍轻轻捣压释放果汁
3. 加碎冰至满
4. 倒入卡沙萨
5. 充分搅拌

## 风味
青柠酸香、卡沙萨草本、甜度可调。巴西国饮。

## 历史
巴西国饮，起源于 19 世纪圣保罗农场工人用 cachaça + 青柠 + 糖治感冒的偏方。名字源于葡萄牙语「caipira」（乡下人）。
""",
    },
    {
        "title": "复尸者2号 Corpse Reviver #2",
        "base_spirit": "gin",
        "difficulty": "hard",
        "season": "spring",
        "iba_category": "contemporary_classics",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "君度", "味美思", "柠檬汁", "苦艾烈酒"],
        "history": "1930 年 Harry Craddock《Savoy Cocktail Book》收录，属「宿醉醒酒」系列。原文称「四杯下肚，渐复生气」。",
        "content": """<!-- ingredients: 金酒|君度|味美思|柠檬汁|苦艾烈酒 -->
# 复尸者2号 Corpse Reviver #2

## 配方
- 金酒 22.5ml
- 君度 22.5ml
- 干味美思 22.5ml
- 柠檬汁 22.5ml
- 苦艾烈酒 1 滴（洗杯）

## 步骤
1. 摇酒壶加冰
2. 倒入金酒、君度、干味美思、柠檬汁
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯
5. 滴入苦艾烈酒洗杯

## 风味
等比四味、苦艾回韵、清新复杂。宿醉救星经典。

## 历史
1930 年 Harry Craddock《Savoy Cocktail Book》收录，属「宿醉醒酒」系列。原文称「四杯下肚，渐复生气」。
""",
    },
    {
        "title": "大都会 Cosmopolitan",
        "base_spirit": "vodka",
        "difficulty": "easy",
        "season": "autumn",
        "iba_category": "contemporary_classics",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["柑橘伏特加", "君度", "青柠汁", "蔓越莓汁"],
        "history": "1985 年迈阿密南滩 Odeon 调酒师 Cheryl Cook 创制。1987 年纽约 Toby Cecchini 改良为现今版本。《欲望都市》使其成为 1990 年代标志性饮品。",
        "content": """<!-- ingredients: 柑橘伏特加|君度|青柠汁|蔓越莓汁 -->
# 大都会 Cosmopolitan

## 配方
- 柑橘伏特加 40ml
- 君度 15ml
- 青柠汁 15ml
- 蔓越莓汁 30ml
- 橙皮 1 片（装饰）

## 步骤
1. 摇酒壶加冰
2. 倒入柑橘伏特加、君度、青柠汁、蔓越莓汁
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯
5. 橙皮扭拧装饰

## 风味
酸甜粉红、柑橘清香、伏特加基底。90 年代 NYC 名饮。

## 历史
1985 年迈阿密南滩 Odeon 调酒师 Cheryl Cook 创制。1987 年纽约 Toby Cecchini 改良为现今版本。《欲望都市》使其成为 1990 年代标志性饮品。
""",
    },
    {
        "title": "自由古巴 Cuba Libre",
        "base_spirit": "rum",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["白朗姆酒", "青柠汁", "可乐"],
        "history": "1900 年美西战争期间，美军在古巴将可口可乐与朗姆酒混合，举杯高喊「Por Cuba Libre」（为了自由的古巴），由此得名。",
        "content": """<!-- ingredients: 白朗姆酒|青柠汁|可乐 -->
# 自由古巴 Cuba Libre

## 配方
- 白朗姆酒 45ml
- 青柠汁 10ml
- 可乐 适量
- 青柠角 1 块（装饰）

## 步骤
1. 高球杯加冰
2. 挤入青柠汁，青柠角投入
3. 倒入白朗姆酒
4. 注入可乐至满
5. 轻轻搅拌

## 风味
可乐甜香、青柠清新、朗姆底蕴。极简经典。

## 历史
1900 年美西战争期间，美军在古巴将可口可乐与朗姆酒混合，举杯高喊「Por Cuba Libre」（为了自由的古巴），由此得名。
""",
    },
    {
        "title": "法兰西75 French 75",
        "base_spirit": "gin",
        "difficulty": "easy",
        "season": "spring",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["金酒", "柠檬汁", "糖浆", "香槟"],
        "history": "1915 年巴黎 Harry's New York Bar 由 Frank Meier 创制。名字源自一战法军 75mm 野战炮，因其「后劲猛烈如炮击」。",
        "content": """<!-- ingredients: 金酒|柠檬汁|糖浆|香槟 -->
# 法兰西75 French 75

## 配方
- 金酒 30ml
- 柠檬汁 15ml
- 糖浆 15ml
- 香槟 适量

## 步骤
1. 高球杯加冰
2. 倒入金酒、柠檬汁、糖浆
3. 搅拌均匀
4. 注入冰镇香槟至满
5. 柠檬皮扭拧装饰

## 风味
气泡优雅、杜松清香、香槟酸度。午间开场名饮。

## 历史
1915 年巴黎 Harry's New York Bar 由 Frank Meier 创制。名字源自一战法军 75mm 野战炮，因其「后劲猛烈如炮击」。
""",
    },
    {
        "title": "爱尔兰咖啡 Irish Coffee",
        "base_spirit": "whiskey",
        "difficulty": "medium",
        "season": "winter",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "热饮杯",
        "ingredients": ["爱尔兰威士忌", "咖啡", "糖浆", "奶油"],
        "history": "1943 年爱尔兰 Shannon 机场 Foynes 飞艇基地主厨 Joe Sheridan 创制，为受冻乘客取暖。1952 年旧金山 Buena Vista Cafe 引入美国，日售千杯成名。",
        "content": """<!-- ingredients: 爱尔兰威士忌|咖啡|糖浆|奶油 -->
# 爱尔兰咖啡 Irish Coffee

## 配方
- 爱尔兰威士忌 45ml
- 热咖啡 120ml
- 红糖糖浆 15ml
- 鲜奶油 30ml（轻微打发）

## 步骤
1. 热饮杯用热水预热
2. 倒入爱尔兰威士忌与糖浆
3. 注入热咖啡搅拌均匀
4. 用勺背缓缓倒入轻微打发的鲜奶油浮于表面
5. 不搅拌，透过奶油饮用

## 风味
咖啡苦香、威士忌温暖、奶油丝滑。冬夜经典。

## 历史
1943 年爱尔兰 Shannon 机场 Foynes 飞艇基地主厨 Joe Sheridan 创制，为受冻乘客取暖。1952 年旧金山 Buena Vista Cafe 引入美国，日售千杯成名。
""",
    },
    {
        "title": "主教 Kir",
        "base_spirit": "other",
        "difficulty": "easy",
        "season": "spring",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "葡萄酒杯",
        "ingredients": ["黑加仑力娇酒", "白葡萄酒"],
        "history": "勃艮第 Dijon 市长 Canon Félix Kir 推广，二战后用 cassis 利口酒为白葡萄酒增色，作为 Dijon 城市官方接待饮品。Royal 版用香槟替代。",
        "content": """<!-- ingredients: 黑加仑力娇酒|白葡萄酒 -->
# 主教 Kir

## 配方
- 黑加仑力娇酒 10ml
- 干白葡萄酒 90ml

## 步骤
1. 葡萄酒杯加冰（可选）
2. 倒入黑加仑力娇酒
3. 注入冰镇干白葡萄酒
4. 轻轻搅拌

## 风味
黑加仑甜香、白酒酸度、低酒精开胃。法式经典。

## 历史
勃艮第 Dijon 市长 Canon Félix Kir 推广，二战后用 cassis 利口酒为白葡萄酒增色，作为 Dijon 城市官方接待饮品。Royal 版用香槟替代。
""",
    },
    {
        "title": "长岛冰茶 Long Island Iced Tea",
        "base_spirit": "vodka",
        "difficulty": "medium",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["伏特加", "金酒", "白朗姆酒", "龙舌兰", "君度", "柠檬汁", "糖浆", "可乐"],
        "history": "1972 年长岛 Babylon 的 Oak Beach Inn 调酒师 Robert «Rosebud» Butt 创制。禁酒令期间另有「Old Man Bishop」版本，但现代版始于 Butt。",
        "content": """<!-- ingredients: 伏特加|金酒|白朗姆酒|龙舌兰|君度|柠檬汁|糖浆|可乐 -->
# 长岛冰茶 Long Island Iced Tea

## 配方
- 伏特加 15ml
- 金酒 15ml
- 白朗姆酒 15ml
- 龙舌兰 15ml
- 君度 15ml
- 柠檬汁 25ml
- 糖浆 15ml
- 可乐 适量

## 步骤
1. 高球杯加冰
2. 倒入五种烈酒与君度
3. 加入柠檬汁与糖浆
4. 注入可乐至满
5. 轻轻搅拌，柠檬片装饰

## 风味
五烈合一、酸甜掩盖、外观如冰茶。烈度极高。

## 历史
1972 年长岛 Babylon 的 Oak Beach Inn 调酒师 Robert «Rosebud» Butt 创制。禁酒令期间另有「Old Man Bishop」版本，但现代版始于 Butt。
""",
    },
    {
        "title": "迈泰 Mai Tai",
        "base_spirit": "rum",
        "difficulty": "medium",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "shake",
        "glassware": "古典杯",
        "ingredients": ["陈年朗姆酒", "白朗姆酒", "君度", "柑曼怡", "青柠汁", "红石榴糖浆", "薄荷叶"],
        "history": "1944 年奥克兰 Trader Vic's 餐厅主理人 Victor «Trader Vic» Bergeron 创制，名字来自塔希提语「Mai tai」（极好）。用 17 年 Jamaican 朗姆调制，递给塔希提朋友品尝得此赞叹。",
        "content": """<!-- ingredients: 陈年朗姆酒|白朗姆酒|君度|柑曼怡|青柠汁|红石榴糖浆|薄荷叶 -->
# 迈泰 Mai Tai

## 配方
- 陈年朗姆酒 30ml
- 白朗姆酒 30ml
- 君度 15ml
- 柑曼怡 5ml
- 青柠汁 15ml
- 红石榴糖浆 5ml
- 薄荷叶 1 枝（装饰）

## 步骤
1. 摇酒壶加冰
2. 倒入所有液体材料
3. 摇匀 15 秒
4. 滤入装碎冰的古典杯
5. 薄荷枝装饰

## 风味
热带果香、朗姆甜润、橙香复杂。Tiki 文化代表作。

## 历史
1944 年奥克兰 Trader Vic's 餐厅主理人 Victor «Trader Vic» Bergeron 创制，名字来自塔希提语「Mai tai」（极好）。用 17 年 Jamaican 朗姆调制，递给塔希提朋友品尝得此赞叹。
""",
    },
    {
        "title": "含羞草 Mimosa",
        "base_spirit": "other",
        "difficulty": "easy",
        "season": "spring",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["香槟", "橙汁"],
        "history": "1925 年巴黎 Ritz Hotel 调酒师 Frank Meier 创制。名字源自法国南部黄色花卉 mimosa，颜色相近。Buck's Fizz（1921 伦敦）为其前身。",
        "content": """<!-- ingredients: 香槟|橙汁 -->
# 含羞草 Mimosa

## 配方
- 香槟 75ml
- 橙汁 75ml

## 步骤
1. 高球杯冷藏
2. 倒入冰镇橙汁
3. 缓缓注入冰镇香槟
4. 轻轻搅拌

## 风味
气泡清新、橙香甜美、低酒精。Brunch 经典开场。

## 历史
1925 年巴黎 Ritz Hotel 调酒师 Frank Meier 创制。名字源自法国南部黄色花卉 mimosa，颜色相近。Buck's Fizz（1921 伦敦）为其前身。
""",
    },
    {
        "title": "薄荷茱莉普 Mint Julep",
        "base_spirit": "whiskey",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "muddle",
        "glassware": "茱莉普杯",
        "ingredients": ["波本威士忌", "薄荷叶", "糖浆"],
        "history": "18 世纪美国南部种植园传统饮品，源自阿拉伯语「julab」（玫瑰水）。肯塔基赛马会（Kentucky Derby）官方饮品，每年售出 12 万杯。",
        "content": """<!-- ingredients: 波本威士忌|薄荷叶|糖浆 -->
# 薄荷茱莉普 Mint Julep

## 配方
- 波本威士忌 60ml
- 薄荷叶 8-10 片
- 糖浆 10ml
- 碎冰适量

## 步骤
1. 茱莉普杯中放入薄荷叶与糖浆
2. 轻轻捣压释放薄荷香气
3. 加入波本威士忌
4. 装满碎冰，搅拌至杯壁结霜
5. 薄荷枝装饰

## 风味
薄荷清凉、波本甜香、冰镇爽快。南方夏夜经典。

## 历史
18 世纪美国南部种植园传统饮品，源自阿拉伯语「julab」（玫瑰水）。肯塔基赛马会（Kentucky Derby）官方饮品，每年售出 12 万杯。
""",
    },
    {
        "title": "莫斯科骡子 Moscow Mule",
        "base_spirit": "vodka",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "铜马克杯",
        "ingredients": ["伏特加", "姜啤", "青柠汁"],
        "history": "1941 年洛杉矶 Cock 'n' Bull 餐厅老板 Jack Morgan 与 Smirnoff 伏特加进口商 John Martin 合作推广，用铜马克杯造型营销成功打开美国伏特加市场。",
        "content": """<!-- ingredients: 伏特加|姜啤|青柠汁 -->
# 莫斯科骡子 Moscow Mule

## 配方
- 伏特加 45ml
- 姜啤 90ml
- 青柠汁 10ml
- 青柠角 1 块（装饰）

## 步骤
1. 铜马克杯加冰
2. 挤入青柠汁，青柠角投入
3. 倒入伏特加
4. 注入冰镇姜啤
5. 轻轻搅拌

## 风味
姜辣清爽、伏特加纯净、气泡刺激。铜杯标志性。

## 历史
1941 年洛杉矶 Cock 'n' Bull 餐厅老板 Jack Morgan 与 Smirnoff 伏特加进口商 John Martin 合作推广，用铜马克杯造型营销成功打开美国伏特加市场。
""",
    },
    {
        "title": "椰林飘香 Piña Colada",
        "base_spirit": "rum",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "blend",
        "glassware": "飓风杯",
        "ingredients": ["白朗姆酒", "椰奶油", "菠萝汁"],
        "history": "1954 年波多黎各圣胡安 Caribe Hilton 调酒师 Ramón «Monchito» Marrero 创制，研发三月余。1978 年成为波多黎各官方饮品。",
        "content": """<!-- ingredients: 白朗姆酒|椰奶油|菠萝汁 -->
# 椰林飘香 Piña Colada

## 配方
- 白朗姆酒 45ml
- 椰奶油 30ml
- 菠萝汁 60ml
- 菠萝角 + 樱桃（装饰）

## 步骤
1. 搅拌机加入白朗姆酒、椰奶油、菠萝汁与碎冰
2. 搅打至绵密顺滑
3. 倒入冰镇飓风杯
4. 菠萝角与樱桃装饰

## 风味
热带椰香、菠萝甜润、绵密冰爽。加勒比度假名饮。

## 历史
1954 年波多黎各圣胡安 Caribe Hilton 调酒师 Ramón «Monchito» Marrero 创制，研发三月余。1978 年成为波多黎各官方饮品。
""",
    },
    {
        "title": "皮斯科酸 Pisco Sour",
        "base_spirit": "other",
        "difficulty": "medium",
        "season": "spring",
        "iba_category": "contemporary_classics",
        "technique": "shake",
        "glassware": "古典杯",
        "ingredients": ["皮斯科", "柠檬汁", "糖浆", "蛋清", "苦精"],
        "history": "1920 年代利马 Morris' Bar 调酒师 Victor Vaughen Morris 创制。秘鲁与智利均宣称皮斯科发源地，秘鲁 2003 年宣布国家文化遗产。",
        "content": """<!-- ingredients: 皮斯科|柠檬汁|糖浆|蛋清|苦精 -->
# 皮斯科酸 Pisco Sour

## 配方
- 皮斯科 60ml
- 柠檬汁 20ml
- 糖浆 20ml
- 蛋清 1 个
- 苦精 3 滴（装饰）

## 步骤
1. 摇酒壶加冰
2. 倒入皮斯科、柠檬汁、糖浆、蛋清
3. 干摇 10 秒乳化
4. 加冰摇 15 秒
5. 滤冰倒入古典杯
6. 表面滴苦精装饰

## 风味
葡萄花香、酸甜柔滑、蛋白泡沫。秘鲁国饮。

## 历史
1920 年代利马 Morris' Bar 调酒师 Victor Vaughen Morris 创制。秘鲁与智利均宣称皮斯科发源地，秘鲁 2003 年宣布国家文化遗产。
""",
    },
    {
        "title": "螺丝刀 Screwdriver",
        "base_spirit": "vodka",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["伏特加", "橙汁"],
        "history": "1940 年代美国石油工人在中东用螺丝刀搅拌伏特加与橙汁得名。1949 年《Time》杂志首次书面记载。极简经典长饮。",
        "content": """<!-- ingredients: 伏特加|橙汁 -->
# 螺丝刀 Screwdriver

## 配方
- 伏特加 50ml
- 橙汁 100ml
- 橙片 1 片（装饰）

## 步骤
1. 高球杯加冰
2. 倒入伏特加
3. 注入冰镇橙汁
4. 轻轻搅拌
5. 橙片装饰

## 风味
橙香甜美、伏特加纯净、极简友好。早午餐经典。

## 历史
1940 年代美国石油工人在中东用螺丝刀搅拌伏特加与橙汁得名。1949 年《Time》杂志首次书面记载。极简经典长饮。
""",
    },
    {
        "title": "新加坡司令 Singapore Sling",
        "base_spirit": "gin",
        "difficulty": "hard",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "shake",
        "glassware": "高球杯",
        "ingredients": ["金酒", "樱桃力娇酒", "君度", "本笃力娇酒", "菠萝汁", "柠檬汁", "红石榴糖浆", "苦精", "苏打水"],
        "history": "1915 年新加坡 Raffles Hotel 长廊酒吧华人调酒师 Ngiam Tong Boon 创制，专为女士设计（当时女性不便在公共场合喝烈酒）。Raffles 至今保留原配方柜台。",
        "content": """<!-- ingredients: 金酒|樱桃力娇酒|君度|本笃力娇酒|菠萝汁|柠檬汁|红石榴糖浆|苦精|苏打水 -->
# 新加坡司令 Singapore Sling

## 配方
- 金酒 30ml
- 樱桃力娇酒 15ml
- 君度 7.5ml
- 本笃力娇酒 7.5ml
- 菠萝汁 60ml
- 柠檬汁 15ml
- 红石榴糖浆 10ml
- 苦精 2 滴
- 苏打水 适量

## 步骤
1. 摇酒壶加冰
2. 倒入所有液体材料（除苏打水）
3. 摇匀 20 秒
4. 滤入装满冰的高球杯
5. 注入苏打水至满
6. 菠萝角与樱桃装饰

## 风味
复杂果香、樱桃底蕴、气泡清爽。Raffles 百年名饮。

## 历史
1915 年新加坡 Raffles Hotel 长廊酒吧华人调酒师 Ngiam Tong Boon 创制，专为女士设计（当时女性不便在公共场合喝烈酒）。Raffles 至今保留原配方柜台。
""",
    },
    {
        "title": "邦德马天尼 Vesper",
        "base_spirit": "gin",
        "difficulty": "medium",
        "season": "autumn",
        "iba_category": "contemporary_classics",
        "technique": "stir",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "伏特加", "利莱白"],
        "history": "1953 年 Ian Fleming 小说《Casino Royale》中 James Bond 创制，以双面间谍 Vesper Lynd 命名。「Three measures of Gordon's, one of vodka, half a measure of Kina Lillet」。",
        "content": """<!-- ingredients: 金酒|伏特加|利莱白 -->
# 邦德马天尼 Vesper

## 配方
- 金酒 60ml
- 伏特加 15ml
- 利莱白 7.5ml
- 柠檬皮 1 片（装饰）

## 步骤
1. 调酒杯加冰
2. 倒入金酒、伏特加、利莱白
3. 搅拌 30 秒
4. 滤冰倒入冰镇马天尼杯
5. 柠檬皮扭拧装饰

## 风味
烈度极高、杜松主导、Lillet 增香。Bond 招牌。

## 历史
1953 年 Ian Fleming 小说《Casino Royale》中 James Bond 创制，以双面间谍 Vesper Lynd 命名。「Three measures of Gordon's, one of vodka, half a measure of Kina Lillet」。
""",
    },
    {
        "title": "僵尸 Zombie",
        "base_spirit": "rum",
        "difficulty": "hard",
        "season": "summer",
        "iba_category": "contemporary_classics",
        "technique": "shake",
        "glassware": "飓风杯",
        "ingredients": ["白朗姆酒", "黑朗姆酒", "陈年朗姆酒", "君度", "樱桃力娇酒", "青柠汁", "柠檬汁", "红石榴糖浆", "苦精"],
        "history": "1934 年好莱坞 Don the Beachcomber 餐厅主理人 Donn Beach 创制，原为帮宿醉商人恢复而调，结果客人喝完变「僵尸」。最初限制每人 2 杯。",
        "content": """<!-- ingredients: 白朗姆酒|黑朗姆酒|陈年朗姆酒|君度|樱桃力娇酒|青柠汁|柠檬汁|红石榴糖浆|苦精 -->
# 僵尸 Zombie

## 配方
- 白朗姆酒 20ml
- 黑朗姆酒 20ml
- 陈年朗姆酒 20ml
- 君度 15ml
- 樱桃力娇酒 7.5ml
- 青柠汁 15ml
- 柠檬汁 15ml
- 红石榴糖浆 7.5ml
- 苦精 2 滴

## 步骤
1. 摇酒壶加冰
2. 倒入所有材料
3. 充分摇匀 20 秒
4. 滤入装满碎冰的飓风杯
5. 薄荷枝装饰

## 风味
三朗姆合一、果香掩盖、烈度极高。Tiki 经典。

## 历史
1934 年好莱坞 Don the Beachcomber 餐厅主理人 Donn Beach 创制，原为帮宿醉商人恢复而调，结果客人喝完变「僵尸」。最初限制每人 2 杯。
""",
    },
    # ============================================================
    # New Era Drinks 新时代（10 款）
    # ============================================================
    {
        "title": "血腥玛丽 Bloody Mary",
        "base_spirit": "vodka",
        "difficulty": "easy",
        "season": "winter",
        "iba_category": "new_era_drinks",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["伏特加", "番茄汁", "柠檬汁", "苦精"],
        "history": "1920 年代巴黎 Harry's New York Bar 调酒师 Fernand Petiot 创制，名字源自英国女王玛丽一世。1934 年纽约 King Cole Bar 加入调味料定型。",
        "content": """<!-- ingredients: 伏特加|番茄汁|柠檬汁|苦精 -->
# 血腥玛丽 Bloody Mary

## 配方
- 伏特加 45ml
- 番茄汁 90ml
- 柠檬汁 15ml
- 苦精 2 滴
- 盐、黑胡椒、辣椒酱适量

## 步骤
1. 高球杯加冰
2. 倒入伏特加、番茄汁、柠檬汁
3. 加苦精与调味料
4. 搅拌均匀
5. 芹菜枝或柠檬片装饰

## 风味
咸鲜辛辣、番茄浓郁。宿醉救星传说。

## 历史
1920 年代巴黎 Harry's New York Bar 调酒师 Fernand Petiot 创制，名字源自英国女王玛丽一世。1934 年纽约 King Cole Bar 加入调味料定型。
""",
    },
    {
        "title": "梭鱼 Barracuda",
        "base_spirit": "rum",
        "difficulty": "medium",
        "season": "summer",
        "iba_category": "new_era_drinks",
        "technique": "shake",
        "glassware": "高球杯",
        "ingredients": ["陈年朗姆酒", "菠萝汁", "柠檬汁", "柠檬利口酒", "普罗塞克"],
        "history": "21 世纪初 IBA New Era Drinks 收录，源自加勒比海地区的鱼雷朗姆鸡尾酒变体，加入起泡酒与柠檬利口酒提升复杂度。",
        "content": """<!-- ingredients: 陈年朗姆酒|菠萝汁|柠檬汁|柠檬利口酒|普罗塞克 -->
# 梭鱼 Barracuda

## 配方
- 陈年朗姆酒 45ml
- 菠萝汁 60ml
- 柠檬汁 15ml
- 柠檬利口酒 10ml
- 普罗塞克 适量

## 步骤
1. 摇酒壶加冰
2. 倒入陈年朗姆酒、菠萝汁、柠檬汁、柠檬利口酒
3. 摇匀 15 秒
4. 滤入装冰高球杯
5. 注入冰镇普罗塞克至满
6. 柠檬皮装饰

## 风味
热带果香、起泡清爽、朗姆甜润。加勒比新经典。

## 历史
21 世纪初 IBA New Era Drinks 收录，源自加勒比海地区的鱼雷朗姆鸡尾酒变体，加入起泡酒与柠檬利口酒提升复杂度。
""",
    },
    {
        "title": "蜜蜂之吻 Bees Knees",
        "base_spirit": "gin",
        "difficulty": "easy",
        "season": "spring",
        "iba_category": "new_era_drinks",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "蜂蜜糖浆", "柠檬汁"],
        "history": "禁酒令时期美国巴黎调酒师 Frank Meier 创制，载于 1929 年《Cocktails de Paris Réunis》。「Bees Knees」是 1920 年代俚语「极好」之意，蜂蜜掩盖劣质金酒。",
        "content": """<!-- ingredients: 金酒|蜂蜜糖浆|柠檬汁 -->
# 蜜蜂之吻 Bees Knees

## 配方
- 金酒 50ml
- 蜂蜜糖浆 20ml
- 柠檬汁 15ml

## 步骤
1. 摇酒壶加冰
2. 倒入金酒、蜂蜜糖浆、柠檬汁
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
蜂蜜甜润、杜松清香、酸度平衡。禁酒令时代经典。

## 历史
禁酒令时期美国巴黎调酒师 Frank Meier 创制，载于 1929 年《Cocktails de Paris Réunis》。「Bees Knees」是 1920 年代俚语「极好」之意，蜂蜜掩盖劣质金酒。
""",
    },
    {
        "title": "黑风暴 Dark 'N' Stormy",
        "base_spirit": "rum",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "new_era_drinks",
        "technique": "build",
        "glassware": "高球杯",
        "ingredients": ["黑朗姆酒", "姜啤", "青柠汁"],
        "history": "1910 年代百慕大 Royal Naval Officer's Club 流行，用 Gosling's 黑朗姆 + Barritt's 姜啤。百慕大官方饮品，注册商标保护。",
        "content": """<!-- ingredients: 黑朗姆酒|姜啤|青柠汁 -->
# 黑风暴 Dark 'N' Stormy

## 配方
- 黑朗姆酒 60ml
- 姜啤 90ml
- 青柠汁 10ml
- 青柠角 1 块（装饰）

## 步骤
1. 高球杯加冰
2. 挤入青柠汁
3. 注入姜啤至八分满
4. 沿吧匙缓缓倒入黑朗姆酒形成渐层
5. 青柠角装饰

## 风味
姜辣清爽、朗姆甜润、视觉风暴云层。百慕大名饮。

## 历史
1910 年代百慕大 Royal Naval Officer's Club 流行，用 Gosling's 黑朗姆 + Barritt's 姜啤。百慕大官方饮品，注册商标保护。
""",
    },
    {
        "title": "脏马天尼 Dirty Martini",
        "base_spirit": "gin",
        "difficulty": "easy",
        "season": "autumn",
        "iba_category": "new_era_drinks",
        "technique": "stir",
        "glassware": "马天尼杯",
        "ingredients": ["金酒", "味美思", "橄榄", "橄榄汁"],
        "history": "1901 年纽约 Hoffman House 调酒师首次加入橄榄汁。Franklin D. Roosevelt 热爱并推广，使其成为白宫鸡尾酒会常客。",
        "content": """<!-- ingredients: 金酒|味美思|橄榄|橄榄汁 -->
# 脏马天尼 Dirty Martini

## 配方
- 金酒 60ml
- 干味美思 10ml
- 橄榄汁 15ml
- 橄榄 1-2 颗（装饰）

## 步骤
1. 调酒杯加冰
2. 倒入金酒、干味美思、橄榄汁
3. 搅拌 30 秒
4. 滤冰倒入冰镇马天尼杯
5. 橄榄装饰

## 风味
咸鲜橄榄、杜松主导、干爽微浑。马天尼咸鲜变体。

## 历史
1901 年纽约 Hoffman House 调酒师首次加入橄榄汁。Franklin D. Roosevelt 热爱并推广，使其成为白宫鸡尾酒会常客。
""",
    },
    {
        "title": "浓缩咖啡马天尼 Espresso Martini",
        "base_spirit": "vodka",
        "difficulty": "medium",
        "season": "autumn",
        "iba_category": "new_era_drinks",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["伏特加", "咖啡力娇酒", "浓缩咖啡", "糖浆"],
        "history": "1983 年伦敦 Soho Brasserie 调酒师 Dick Bradsell 应模特要求「让我清醒起来再醉倒」创制。原名 Vodka Espresso，后改名 Espresso Martini。",
        "content": """<!-- ingredients: 伏特加|咖啡力娇酒|浓缩咖啡|糖浆 -->
# 浓缩咖啡马天尼 Espresso Martini

## 配方
- 伏特加 50ml
- 咖啡力娇酒 15ml
- 浓缩咖啡 30ml（新鲜萃取）
- 糖浆 5ml
- 咖啡豆 3 颗（装饰）

## 步骤
1. 摇酒壶加冰
2. 倒入伏特加、咖啡力娇酒、浓缩咖啡、糖浆
3. 充分摇匀 20 秒起泡
4. 双层滤冰倒入冰镇马天尼杯
5. 表面浮 3 颗咖啡豆装饰

## 风味
咖啡苦香、伏特加纯净、绵密泡沫。餐后提神经典。

## 历史
1983 年伦敦 Soho Brasserie 调酒师 Dick Bradsell 应模特要求「让我清醒起来再醉倒」创制。原名 Vodka Espresso，后改名 Espresso Martini。
""",
    },
    {
        "title": "法式马天尼 French Martini",
        "base_spirit": "vodka",
        "difficulty": "easy",
        "season": "spring",
        "iba_category": "new_era_drinks",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["伏特加", "香波力娇酒", "菠萝汁", "柠檬汁"],
        "history": "1980 年代纽约调酒师 Allan Katz 创制，Chambord 黑莓利口酒+菠萝汁的搭配赋予法式优雅。无味美思，名为「Martini」纯属营销。",
        "content": """<!-- ingredients: 伏特加|香波力娇酒|菠萝汁|柠檬汁 -->
# 法式马天尼 French Martini

## 配方
- 伏特加 45ml
- 香波力娇酒 15ml
- 菠萝汁 30ml
- 柠檬汁 5ml

## 步骤
1. 摇酒壶加冰
2. 倒入伏特加、香波力娇酒、菠萝汁、柠檬汁
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
莓果甜香、菠萝果味、伏特加纯净。女性友好。

## 历史
1980 年代纽约调酒师 Allan Katz 创制，Chambord 黑莓利口酒+菠萝汁的搭配赋予法式优雅。无味美思，名为「Martini」纯属营销。
""",
    },
    {
        "title": "非法 Illegal",
        "base_spirit": "tequila",
        "difficulty": "medium",
        "season": "autumn",
        "iba_category": "new_era_drinks",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["龙舌兰", "绿查特酒", "柠檬汁", "苦艾烈酒"],
        "history": "2005 年伦敦 Milk & Honey 调酒师 Sam Ross 创制。名字源于禁酒令时期的非法调酒传统，灵感来自 Last Word 的龙舌兰变体。",
        "content": """<!-- ingredients: 龙舌兰|绿查特酒|柠檬汁|苦艾烈酒 -->
# 非法 Illegal

## 配方
- 龙舌兰 30ml
- 绿查特酒 15ml
- 柠檬汁 15ml
- 苦艾烈酒 1 滴（洗杯）

## 步骤
1. 摇酒壶加冰
2. 倒入龙舌兰、绿查特酒、柠檬汁
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯
5. 滴苦艾烈酒洗杯

## 风味
草本复杂、龙舌兰植物香、苦艾回韵。Last Word 龙舌兰版。

## 历史
2005 年伦敦 Milk & Honey 调酒师 Sam Ross 创制。名字源于禁酒令时期的非法调酒传统，灵感来自 Last Word 的龙舌兰变体。
""",
    },
    {
        "title": "汤米的玛格丽特 Tommy's Margarita",
        "base_spirit": "tequila",
        "difficulty": "easy",
        "season": "summer",
        "iba_category": "new_era_drinks",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["龙舌兰", "青柠汁", "龙舌兰糖浆"],
        "history": "1990 年代旧金山 Tommy's Restaurant 主理人 Julio Bermejo 创制，用龙舌兰糖浆替代橙味力娇酒。该餐厅龙舌兰收藏为世界之最。",
        "content": """<!-- ingredients: 龙舌兰|青柠汁|龙舌兰糖浆 -->
# 汤米的玛格丽特 Tommy's Margarita

## 配方
- 龙舌兰 50ml
- 青柠汁 25ml
- 龙舌兰糖浆 15ml

## 步骤
1. 摇酒壶加冰
2. 倒入龙舌兰、青柠汁、龙舌兰糖浆
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
龙舌兰植物香、酸甜纯粹、无橙味干扰。Margarita 简化版。

## 历史
1990 年代旧金山 Tommy's Restaurant 主理人 Julio Bermejo 创制，用龙舌兰糖浆替代橙味力娇酒。该餐厅龙舌兰收藏为世界之最。
""",
    },
    {
        "title": "黄鸟 Yellow Bird",
        "base_spirit": "rum",
        "difficulty": "medium",
        "season": "summer",
        "iba_category": "new_era_drinks",
        "technique": "shake",
        "glassware": "马天尼杯",
        "ingredients": ["白朗姆酒", "君度", "绿查特酒", "柠檬汁"],
        "history": "1960 年代牙买加 Trilogy 酒店创制，名字源自海地民歌「Yellow Bird」。配方载于 1985 年《Cocktail Companion》。",
        "content": """<!-- ingredients: 白朗姆酒|君度|绿查特酒|柠檬汁 -->
# 黄鸟 Yellow Bird

## 配方
- 白朗姆酒 30ml
- 君度 15ml
- 绿查特酒 15ml
- 柠檬汁 15ml

## 步骤
1. 摇酒壶加冰
2. 倒入白朗姆酒、君度、绿查特酒、柠檬汁
3. 摇匀 15 秒
4. 滤冰倒入冰镇马天尼杯

## 风味
草本果香、朗姆甜润、Chartreuse 复杂。加勒比经典。

## 历史
1960 年代牙买加 Trilogy 酒店创制，名字源自海地民歌「Yellow Bird」。配方载于 1985 年《Cocktail Companion》。
""",
    },
]
