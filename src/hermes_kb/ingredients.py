"""材料注册表 + 别名归一化。

类别：
- base_spirit 基酒（金酒/威士忌/朗姆/龙舌兰/白兰地/伏特加 等）
- modifier 辅料（味美思/苦精/糖浆/君度/利口酒/汤力水/苏打水 等）
- juice 果汁（柠檬汁/青柠汁/橙汁/蔓越莓汁/菠萝汁）
- wine 葡萄酒与起泡酒（香槟/普罗塞克/红葡萄酒/波特酒）
- garnish 装饰（橄榄/柠檬片/薄荷叶/樱桃/橙皮）

每条材料携带：
- canonical: 中文标准名
- aliases: 英文 + 中文同义词列表
- category: 上述分类之一
- abv: 酒精度小数（0.0-1.0），非酒精材料为 0.0
- brands: 常见品牌列表（可为空）
- tags: 风味标签列表（P2-A 新增，可为空）—— 用于风味查询与推荐
    e.g. ["juniper","botanical","herbal"] for gin
- origin: 产地（P2-A 新增，可为空字符串）—— 国家或地区
- abv_range: ABV 实际范围 [min, max]（P2-A 新增，可为 None）
    用于校准：实际产品可能在 abv 周围波动，abv 是典型值
"""
from __future__ import annotations

INGREDIENT_REGISTRY: dict[str, dict] = {
    # === 基酒 ===
    "gin": {
        "canonical": "金酒",
        "aliases": ["gin", "dry gin", "london dry", "杜松子酒", "gordon's", "gordon"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.37, 0.47],
        "brands": ["Gordon's", "Tanqueray", "Beefeater", "Bombay", "Hendrick's", "Aviation"],
        "tags": ["juniper", "botanical", "herbal", "dry"],
        "origin": "Netherlands/UK",
    },
    "whiskey": {
        "canonical": "威士忌",
        "aliases": ["whiskey", "whisky", "威士忌"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.40, 0.46],
        "brands": ["Johnnie Walker", "Glenfiddich", "Jim Beam", "Macallan"],
        "tags": ["malty", "oaky", "warm", "caramel"],
        "origin": "Scotland/USA/Ireland",
    },
    "rum": {
        "canonical": "朗姆酒",
        "aliases": ["rum", "朗姆", "朗姆酒"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.38, 0.43],
        "brands": ["Bacardi", "Havana Club", "Captain Morgan", "Mount Gay"],
        "tags": ["molasses", "sweet", "caramel", "tropical"],
        "origin": "Caribbean",
    },
    "tequila": {
        "canonical": "龙舌兰",
        "aliases": ["tequila", "龙舌兰"],
        "category": "base_spirit",
        "abv": 0.38,
        "abv_range": [0.35, 0.40],
        "brands": ["Patrón", "Jose Cuervo", "Don Julio", "Herradura", "Sauza"],
        "tags": ["agave", "earthy", "pepper", "herbal"],
        "origin": "Mexico",
    },
    "brandy": {
        "canonical": "白兰地",
        "aliases": ["brandy", "白兰地", "干邑"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.35, 0.45],
        "brands": ["Hennessy", "Rémy Martin", "Martell", "Courvoisier"],
        "tags": ["fruity", "oaky", "warm", "grape"],
        "origin": "France",
    },
    "vodka": {
        "canonical": "伏特加",
        "aliases": ["vodka", "伏特加"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.37, 0.50],
        "brands": ["Absolut", "Grey Goose", "Smirnoff", "Stolichnaya", "Belvedere", "Ketel One"],
        "tags": ["neutral", "clean", "smooth"],
        "origin": "Russia/Poland",
    },
    # === 辅料 ===
    "vermouth": {
        "canonical": "味美思",
        "aliases": ["vermouth", "dry vermouth", "sweet vermouth", "味美思", "苦艾酒"],
        "category": "modifier",
        "abv": 0.18,
        "abv_range": [0.15, 0.22],
        "brands": ["Martini", "Noilly Prat", "Cinzano", "Dolin", "Carpano Antica"],
        "tags": ["botanical", "aromatic", "herbal", "wine-fortified"],
        "origin": "Italy/France",
    },
    "campari": {
        "canonical": "金巴利",
        "aliases": ["campari", "金巴利"],
        "category": "modifier",
        "abv": 0.25,
        "abv_range": [0.21, 0.28],
        "brands": ["Campari"],
        "tags": ["bitter", "citrus", "herbal", "red"],
        "origin": "Italy",
    },
    "sugar_syrup": {
        "canonical": "糖浆",
        "aliases": ["sugar syrup", "simple syrup", "syrup", "糖浆", "糖水"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "cointreau": {
        "canonical": "君度",
        "aliases": ["cointreau", "橙味力娇酒", "君度"],
        "category": "modifier",
        "abv": 0.40,
        "abv_range": [0.40, 0.40],
        "brands": ["Cointreau"],
        "tags": ["orange", "citrus", "sweet", "peel"],
        "origin": "France",
    },
    "angostura": {
        "canonical": "苦精",
        "aliases": ["angostura", "bitters", "苦精", "安高天娜"],
        "category": "modifier",
        "abv": 0.44,
        "abv_range": [0.35, 0.45],
        "brands": ["Angostura", "Peychaud's", "Fee Brothers"],
        "tags": ["bitter", "aromatic", "spicy", "concentrated"],
        "origin": "Trinidad & Tobago",
    },
    "tonic": {
        "canonical": "汤力水",
        "aliases": ["tonic", "tonic water", "汤力水"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "soda": {
        "canonical": "苏打水",
        "aliases": ["soda", "soda water", "苏打水", "气泡水"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "cola": {
        "canonical": "可乐",
        "aliases": ["cola", "coke", "可乐"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "ginger_beer": {
        "canonical": "姜啤",
        "aliases": ["ginger beer", "姜啤", "姜汁啤酒"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
        "tags": ["ginger", "spicy", "bubbly"],
        "origin": "UK/Caribbean",
    },
    # === 果汁 ===
    "lemon_juice": {
        "canonical": "柠檬汁",
        "aliases": ["lemon juice", "柠檬汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "lime_juice": {
        "canonical": "青柠汁",
        "aliases": ["lime juice", "青柠汁", "莱姆汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "orange_juice": {
        "canonical": "橙汁",
        "aliases": ["orange juice", "橙汁", "橘子汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "cranberry_juice": {
        "canonical": "蔓越莓汁",
        "aliases": ["cranberry juice", "蔓越莓汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "pineapple_juice": {
        "canonical": "菠萝汁",
        "aliases": ["pineapple juice", "菠萝汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "tomato_juice": {
        "canonical": "番茄汁",
        "aliases": ["tomato juice", "番茄汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    # === 装饰 ===
    "olive": {
        "canonical": "橄榄",
        "aliases": ["olive", "橄榄"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "lemon_slice": {
        "canonical": "柠檬片",
        "aliases": ["lemon slice", "lemon", "柠檬片", "柠檬"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "mint": {
        "canonical": "薄荷叶",
        "aliases": ["mint", "mint leaves", "薄荷叶", "薄荷"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "cherry": {
        "canonical": "樱桃",
        "aliases": ["cherry", "maraschino cherry", "樱桃"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "orange_peel": {
        "canonical": "橙皮",
        "aliases": ["orange peel", "橙皮"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    # === 扩展：烈酒类 ===
    "absinthe": {
        "canonical": "苦艾烈酒",
        "aliases": ["absinthe", "绿魔", "苦艾烈酒"],
        "category": "base_spirit",
        "abv": 0.55,
        "abv_range": [0.45, 0.74],
        "brands": ["Pernod", "Lucid", "La Fée", "Absinthe Mansinthe"],
        "tags": ["anise", "herbal", "black-licorice", "strong"],
        "origin": "Switzerland/France",
    },
    "bourbon": {
        "canonical": "波本威士忌",
        "aliases": ["bourbon", "bourbon whiskey", "波本", "波本威士忌"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.40, 0.50],
        "brands": ["Jim Beam", "Maker's Mark", "Buffalo Trace", "Woodford Reserve", "Bulleit"],
        "tags": ["malty", "caramel", "vanilla", "oaky", "sweet"],
        "origin": "USA",
    },
    "cognac": {
        "canonical": "干邑白兰地",
        "aliases": ["cognac", "cognac brandy", "干邑白兰地", "法国白兰地"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.40, 0.43],
        "brands": ["Hennessy", "Rémy Martin", "Martell", "Courvoisier", "Camus"],
        "tags": ["fruity", "oaky", "grape", "warm"],
        "origin": "France",
    },
    "irish_whiskey": {
        "canonical": "爱尔兰威士忌",
        "aliases": ["irish whiskey", "爱尔兰威士忌"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.40, 0.43],
        "brands": ["Jameson", "Bushmills", "Tullamore D.E.W.", "Redbreast"],
        "tags": ["malty", "smooth", "light", "vanilla"],
        "origin": "Ireland",
    },
    "rye_whiskey": {
        "canonical": "黑麦威士忌",
        "aliases": ["rye", "rye whiskey", "rye whisky", "黑麦威士忌"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.40, 0.50],
        "brands": ["Bulleit Rye", "Rittenhouse", "Sazerac", "WhistlePig"],
        "tags": ["spicy", "peppery", "malty", "bold"],
        "origin": "USA/Canada",
    },
    "scotch": {
        "canonical": "苏格兰威士忌",
        "aliases": ["scotch", "scotch whisky", "scottish whisky", "苏格兰威士忌"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.40, 0.46],
        "brands": ["Johnnie Walker", "Glenfiddich", "Macallan", "Lagavulin", "Laphroaig"],
        "tags": ["malty", "smoky", "oaky", "peaty"],
        "origin": "Scotland",
    },
    "pisco": {
        "canonical": "皮斯科",
        "aliases": ["pisco", "皮斯科", "秘鲁烈酒"],
        "category": "base_spirit",
        "abv": 0.38,
        "abv_range": [0.38, 0.48],
        "brands": ["Pisco Portón", "Barsol", "Campo de Encanto", "La Diablada"],
        "tags": ["grape", "floral", "earthy", "fruity"],
        "origin": "Peru/Chile",
    },
    "aquavit": {
        "canonical": "阿夸维特",
        "aliases": ["aquavit", "akvavit", "阿夸维特"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.37, 0.45],
        "brands": ["Linie", "Aalborg", "O. F. Clausen"],
        "tags": ["caraway", "dill", "herbal", "savory"],
        "origin": "Scandinavia",
    },
    "dark_rum": {
        "canonical": "黑朗姆酒",
        "aliases": ["dark rum", "黑朗姆", "黑朗姆酒", "dark rum liqueur"],
        "category": "base_spirit",
        "abv": 0.43,
        "abv_range": [0.40, 0.50],
        "brands": ["Myers's", "Goslings", "Bacardi Black", "Kraken"],
        "tags": ["molasses", "caramel", "oaky", "sweet", "tropical"],
        "origin": "Caribbean",
    },
    "white_rum": {
        "canonical": "白朗姆酒",
        "aliases": ["white rum", "白朗姆", "白朗姆酒", "light rum"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.37, 0.43],
        "brands": ["Bacardi Superior", "Havana Club Añejo Blanco", "Mount Gay Eclipse Silver"],
        "tags": ["molasses", "light", "clean", "sweet"],
        "origin": "Caribbean",
    },
    "aged_rum": {
        "canonical": "陈年朗姆酒",
        "aliases": ["aged rum", "anejo rum", "陈年朗姆酒"],
        "category": "base_spirit",
        "abv": 0.43,
        "abv_range": [0.40, 0.45],
        "brands": ["Diplomático", "Zacapa", "Appleton Estate", "Plantation"],
        "tags": ["molasses", "oaky", "caramel", "vanilla", "tropical"],
        "origin": "Caribbean",
    },
    # === 扩展：利口酒类 ===
    "amaretto": {
        "canonical": "苦杏仁酒",
        "aliases": ["amaretto", "苦杏仁酒", "杏仁力娇酒"],
        "category": "modifier",
        "abv": 0.28,
        "abv_range": [0.24, 0.30],
        "brands": ["Disaronno", "Lazzaroni", "Hiram Walker"],
        "tags": ["almond", "nutty", "sweet", "apricot-pit"],
        "origin": "Italy",
    },
    "baileys": {
        "canonical": "百利甜酒",
        "aliases": ["baileys", "irish cream", "百利甜酒", "百利"],
        "category": "modifier",
        "abv": 0.17,
        "abv_range": [0.15, 0.20],
        "brands": ["Baileys", "Carolans", "Saint Brendan's"],
        "tags": ["cream", "chocolate", "coffee", "sweet", "dairy"],
        "origin": "Ireland",
    },
    "chambord": {
        "canonical": "香波力娇酒",
        "aliases": ["chambord", "香波力娇酒", "chambord liqueur"],
        "category": "modifier",
        "abv": 0.16,
        "abv_range": [0.16, 0.25],
        "brands": ["Chambord"],
        "tags": ["blackberry", "raspberry", "sweet", "berry"],
        "origin": "France",
    },
    "coffee_liqueur": {
        "canonical": "咖啡力娇酒",
        "aliases": ["coffee liqueur", "咖啡力娇酒", "咖啡酒"],
        "category": "modifier",
        "abv": 0.20,
        "abv_range": [0.20, 0.25],
        "brands": ["Kahlúa", "Tia Maria", "Patrón XO Cafe", "Mr. Black"],
        "tags": ["coffee", "roasted", "sweet", "dark"],
        "origin": "Mexico/Jamaica",
    },
    "grand_marnier": {
        "canonical": "柑曼怡",
        "aliases": ["grand marnier", "柑曼怡", "grand marnier liqueur"],
        "category": "modifier",
        "abv": 0.40,
        "abv_range": [0.40, 0.40],
        "brands": ["Grand Marnier"],
        "tags": ["orange", "cognac", "citrus", "sweet"],
        "origin": "France",
    },
    "galliano": {
        "canonical": "加利亚诺",
        "aliases": ["galliano", "加利亚诺", "galliano liqueur"],
        "category": "modifier",
        "abv": 0.30,
        "abv_range": [0.30, 0.42],
        "brands": ["Galliano L'Autentico"],
        "tags": ["vanilla", "anise", "herbal", "citrus"],
        "origin": "Italy",
    },
    "midori": {
        "canonical": "蜜瓜力娇酒",
        "aliases": ["midori", "蜜瓜力娇酒", "melon liqueur"],
        "category": "modifier",
        "abv": 0.20,
        "abv_range": [0.20, 0.25],
        "brands": ["Midori", "Bols Melon"],
        "tags": ["melon", "sweet", "green", "fruity"],
        "origin": "Japan",
    },
    "blue_curacao": {
        "canonical": "蓝柑香酒",
        "aliases": ["blue curacao", "blue curaçao", "蓝柑香酒", "蓝橙力娇酒"],
        "category": "modifier",
        "abv": 0.21,
        "abv_range": [0.15, 0.25],
        "brands": ["Bols Blue Curaçao", "De Kuyper Blue Curaçao"],
        "tags": ["orange", "citrus", "sweet", "blue-dye"],
        "origin": "Curaçao",
    },
    "creme_de_cacao": {
        "canonical": "可可力娇酒",
        "aliases": ["creme de cacao", "crème de cacao", "可可力娇酒", "可可甜酒"],
        "category": "modifier",
        "abv": 0.25,
        "abv_range": [0.20, 0.30],
        "brands": ["Marie Brizard", "Bols Crème de Cacao", "Tempus Fugit"],
        "tags": ["chocolate", "cocoa", "sweet", "dark"],
        "origin": "France",
    },
    "creme_de_cassis": {
        "canonical": "黑加仑力娇酒",
        "aliases": ["creme de cassis", "crème de cassis", "黑加仑力娇酒", "黑醋栗酒"],
        "category": "modifier",
        "abv": 0.20,
        "abv_range": [0.15, 0.25],
        "brands": ["Lejay Lagoute", "Gabriel Boudier", "Briottet"],
        "tags": ["blackcurrant", "berry", "sweet", "dark"],
        "origin": "France",
    },
    "creme_de_menthe": {
        "canonical": "薄荷力娇酒",
        "aliases": ["creme de menthe", "crème de menthe", "薄荷力娇酒", "薄荷甜酒"],
        "category": "modifier",
        "abv": 0.25,
        "abv_range": [0.20, 0.30],
        "brands": ["Marie Brizard", "Bols Crème de Menthe", "Giffard"],
        "tags": ["mint", "fresh", "sweet", "herbal"],
        "origin": "France",
    },
    "triple_sec": {
        "canonical": "白橙力娇酒",
        "aliases": ["triple sec", "triple sec liqueur", "白橙力娇酒", "三秒酒"],
        "category": "modifier",
        "abv": 0.30,
        "abv_range": [0.15, 0.40],
        "brands": ["Bols Triple Sec", "De Kuyper Triple Sec", "Cointreau"],
        "tags": ["orange", "citrus", "sweet", "peel"],
        "origin": "France",
    },
    "peach_schnapps": {
        "canonical": "蜜桃香甜酒",
        "aliases": ["peach schnapps", "蜜桃香甜酒", "peach liqueur"],
        "category": "modifier",
        "abv": 0.20,
        "abv_range": [0.15, 0.25],
        "brands": ["DeKuyper Peachtree", "Hiram Walker Peach Schnapps"],
        "tags": ["peach", "sweet", "fruity"],
        "origin": "USA",
    },
    "apricot_brandy": {
        "canonical": "杏子白兰地",
        "aliases": ["apricot brandy", "杏子白兰地", "apricot liqueur"],
        "category": "modifier",
        "abv": 0.30,
        "abv_range": [0.25, 0.35],
        "brands": ["Marie Brizard Apry", "Bols Apricot Brandy"],
        "tags": ["apricot", "stone-fruit", "sweet", "fruity"],
        "origin": "France",
    },
    "maraschino_liqueur": {
        "canonical": "樱桃力娇酒",
        "aliases": ["maraschino liqueur", "maraschino", "樱桃力娇酒"],
        "category": "modifier",
        "abv": 0.32,
        "abv_range": [0.28, 0.32],
        "brands": ["Luxardo", "Maraska", "Stock"],
        "tags": ["cherry", "marasca", "sweet", "nutty"],
        "origin": "Italy/Croatia",
    },
    # === 扩展：葡萄酒 / 起泡酒 ===
    "champagne": {
        "canonical": "香槟",
        "aliases": ["champagne", "香槟", "champagne wine"],
        "category": "wine",
        "abv": 0.12,
        "brands": [],
    },
    "prosecco": {
        "canonical": "普罗塞克",
        "aliases": ["prosecco", "普罗塞克", "起泡酒"],
        "category": "wine",
        "abv": 0.11,
        "brands": [],
    },
    "red_wine": {
        "canonical": "红葡萄酒",
        "aliases": ["red wine", "红葡萄酒", "红酒"],
        "category": "wine",
        "abv": 0.13,
        "brands": [],
    },
    "port_wine": {
        "canonical": "波特酒",
        "aliases": ["port wine", "port", "波特酒", "portwine"],
        "category": "wine",
        "abv": 0.20,
        "brands": [],
    },
    # === 扩展：其他辅料 ===
    "dry_vermouth": {
        "canonical": "干味美思",
        "aliases": ["extra dry vermouth", "干味美思"],
        "category": "modifier",
        "abv": 0.18,
        "brands": [],
    },
    "sweet_vermouth": {
        "canonical": "甜味美思",
        "aliases": ["sweet vermouth rouge", "甜味美思"],
        "category": "modifier",
        "abv": 0.20,
        "brands": [],
    },
    "orange_bitters": {
        "canonical": "橙味苦精",
        "aliases": ["orange bitters", "橙味苦精"],
        "category": "modifier",
        "abv": 0.28,
        "brands": [],
    },
    "egg_white": {
        "canonical": "蛋清",
        "aliases": ["egg white", "蛋清", "蛋白"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "cream": {
        "canonical": "奶油",
        "aliases": ["cream", "奶油", "鲜奶油"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "espresso": {
        "canonical": "浓缩咖啡",
        "aliases": ["espresso", "浓缩咖啡", "espresso coffee"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "grenadine": {
        "canonical": "红石榴糖浆",
        "aliases": ["grenadine", "红石榴糖浆", "石榴糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "honey_syrup": {
        "canonical": "蜂蜜糖浆",
        "aliases": ["honey syrup", "蜂蜜糖浆", "蜜糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "agave_syrup": {
        "canonical": "龙舌兰糖浆",
        "aliases": ["agave syrup", "agave nectar", "龙舌兰糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "coconut_cream": {
        "canonical": "椰奶油",
        "aliases": ["coconut cream", "椰奶油", "椰浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    # === 扩展 II：基酒 ===
    "mezcal": {
        "canonical": "梅斯卡尔",
        "aliases": ["mezcal", "梅斯卡尔"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.38, 0.50],
        "brands": ["Del Maguey Vida", "Ilegal", "Espadín", "Montelobos"],
        "tags": ["agave", "smoky", "earthy", "bold"],
        "origin": "Mexico",
    },
    "genever": {
        "canonical": "荷兰金酒",
        "aliases": ["genever", "jenever", "荷兰金酒", "杜松子威士忌"],
        "category": "base_spirit",
        "abv": 0.35,
        "abv_range": [0.30, 0.38],
        "brands": ["Bols Genever", "Bokma", "Hooghoudt"],
        "tags": ["juniper", "malty", "malty-sweet", "botanical"],
        "origin": "Netherlands",
    },
    "baijiu": {
        "canonical": "白酒",
        "aliases": ["baijiu", "白酒", "中国白酒"],
        "category": "base_spirit",
        "abv": 0.52,
        "abv_range": [0.38, 0.65],
        "brands": ["茅台", "五粮液", "剑南春", "泸州老窖", "汾酒"],
        "tags": ["complex", "fermented", "aromatic", "strong"],
        "origin": "China",
    },
    # === B: 中国白酒 10 大香型细分（与 IMA「酒博士」联检联动）===
    # 国家标准 GB/T 10781（浓/清/米）、GB/T 26760（酱）、GB/T 20823（特）、
    # GB/T 20824（芝麻）、GB/T 23547（兼）、GB/T 14867（凤）、
    # GB/T 20825（老白干）、GB/T 10781.3（米香）等
    "nongxiang_baijiu": {
        "canonical": "浓香型白酒",
        "aliases": ["浓香型白酒", "浓香白酒", "nongxiang baijiu", "浓香型", "浓香"],
        "category": "base_spirit",
        "abv": 0.52,
        "abv_range": [0.40, 0.55],
        "brands": ["泸州老窖", "五粮液", "剑南春", "洋河大曲", "古井贡酒"],
        "tags": ["aroma-heavy", "ester-rich", "fruity", "strong", "nongxiang"],
        "origin": "Sichuan/Jiangsu/Anhui",
    },
    "jiangxiang_baijiu": {
        "canonical": "酱香型白酒",
        "aliases": ["酱香型白酒", "酱香白酒", "jiangxiang baijiu", "酱香型", "酱香", "茅香型"],
        "category": "base_spirit",
        "abv": 0.53,
        "abv_range": [0.43, 0.55],
        "brands": ["茅台", "郎酒", "习酒", "国台", "珍酒"],
        "tags": ["soy-sauce", "complex", "long-finish", "strong", "jiangxiang"],
        "origin": "Guizhou/Sichuan",
    },
    "qingxiang_baijiu": {
        "canonical": "清香型白酒",
        "aliases": ["清香型白酒", "清香白酒", "qingxiang baijiu", "清香型", "清香"],
        "category": "base_spirit",
        "abv": 0.55,
        "abv_range": [0.40, 0.65],
        "brands": ["汾酒", "二锅头", "江小白", "宝丰酒"],
        "tags": ["light", "clean", "fresh", "pure", "qingxiang"],
        "origin": "Shanxi/Beijing",
    },
    "mixiang_baijiu": {
        "canonical": "米香型白酒",
        "aliases": ["米香型白酒", "米香白酒", "mixiang baijiu", "米香型", "米香"],
        "category": "base_spirit",
        "abv": 0.50,
        "abv_range": [0.38, 0.55],
        "brands": ["桂林三花酒", "全州湘山酒", "长乐烧"],
        "tags": ["rice", "honey", "light", "sweet", "mixiang"],
        "origin": "Guangxi/Guangdong",
    },
    "jianxiang_baijiu": {
        "canonical": "兼香型白酒",
        "aliases": ["兼香型白酒", "兼香白酒", "jianxiang baijiu", "兼香型", "兼香", "兼型"],
        "category": "base_spirit",
        "abv": 0.52,
        "abv_range": [0.40, 0.55],
        "brands": ["白云边", "口子窖", "白沙液"],
        "tags": ["blended", "complex", "nongxiang", "jiangxiang", "jianxiang"],
        "origin": "Hubei/Anhui",
    },
    "fengxiang_baijiu": {
        "canonical": "凤香型白酒",
        "aliases": ["凤香型白酒", "凤香白酒", "fengxiang baijiu", "凤香型", "凤香"],
        "category": "base_spirit",
        "abv": 0.55,
        "abv_range": [0.45, 0.55],
        "brands": ["西凤酒", "凤香型西凤"],
        "tags": ["complex", "fruit", "earthy", "fengxiang"],
        "origin": "Shaanxi",
    },
    "dongxiang_baijiu": {
        "canonical": "董香型白酒",
        "aliases": ["董香型白酒", "董香白酒", "dongxiang baijiu", "董香型", "董香", "药香型", "药香"],
        "category": "base_spirit",
        "abv": 0.54,
        "abv_range": [0.45, 0.55],
        "brands": ["董酒"],
        "tags": ["herbal", "medicinal", "complex", "dongxiang"],
        "origin": "Guizhou",
    },
    "chixiang_baijiu": {
        "canonical": "豉香型白酒",
        "aliases": ["豉香型白酒", "豉香白酒", "chixiang baijiu", "豉香型", "豉香"],
        "category": "base_spirit",
        "abv": 0.30,
        "abv_range": [0.28, 0.40],
        "brands": ["九江双蒸", "玉冰烧"],
        "tags": ["fermented-bean", "fat-ester", "light", "chixiang"],
        "origin": "Guangdong",
    },
    "texiang_baijiu": {
        "canonical": "特香型白酒",
        "aliases": ["特香型白酒", "特香白酒", "texiang baijiu", "特香型", "特香"],
        "category": "base_spirit",
        "abv": 0.52,
        "abv_range": [0.40, 0.55],
        "brands": ["四特酒"],
        "tags": ["rice", "complex", "round", "texiang"],
        "origin": "Jiangxi",
    },
    "zhimaxiang_baijiu": {
        "canonical": "芝麻香型白酒",
        "aliases": ["芝麻香型白酒", "芝麻香白酒", "zhimaxiang baijiu", "芝麻香型", "芝麻香"],
        "category": "base_spirit",
        "abv": 0.52,
        "abv_range": [0.40, 0.55],
        "brands": ["景芝白干", "扳倒井"],
        "tags": ["sesame", "roasted", "nutty", "zhimaxiang"],
        "origin": "Shandong",
    },
    "soju": {
        "canonical": "烧酒",
        "aliases": ["soju", "烧酒", "韩国烧酒"],
        "category": "base_spirit",
        "abv": 0.20,
        "abv_range": [0.17, 0.45],
        "brands": ["Jinro Chamisul", "Chum Churum", "Good Day"],
        "tags": ["neutral", "clean", "smooth", "light"],
        "origin": "Korea",
    },
    "shochu": {
        "canonical": "日本烧酎",
        "aliases": ["shochu", "日本烧酎", "烧酎"],
        "category": "base_spirit",
        "abv": 0.25,
        "abv_range": [0.20, 0.40],
        "brands": ["Iichiko", "Kuro Kirishima", "Satsuma Shochu"],
        "tags": ["neutral", "earthy", "smooth", "distilled"],
        "origin": "Japan",
    },
    "cachaca": {
        "canonical": "卡沙萨",
        "aliases": ["cachaca", "cachaça", "卡沙萨", "巴西甘蔗酒"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.38, 0.48],
        "brands": ["Leblon", "Ypióca", "Sagatiba", "Novo Fogo"],
        "tags": ["sugarcane", "grass", "earthy", "tropical"],
        "origin": "Brazil",
    },
    "calvados": {
        "canonical": "苹果白兰地",
        "aliases": ["calvados", "苹果白兰地", "apple brandy"],
        "category": "base_spirit",
        "abv": 0.42,
        "abv_range": [0.40, 0.45],
        "brands": ["Pierre Huet", "Boulard", "Christian Drouin"],
        "tags": ["apple", "fruity", "oaky", "warm"],
        "origin": "France",
    },
    "armagnac": {
        "canonical": "雅文邑",
        "aliases": ["armagnac", "雅文邑", "雅邑白兰地"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.40, 0.43],
        "brands": ["Château de Laubade", "Dartigalongue", "Marquis de Montesquiou"],
        "tags": ["fruity", "oaky", "grape", "prune"],
        "origin": "France",
    },
    "grappa": {
        "canonical": "格拉帕",
        "aliases": ["grappa", "格拉帕", "果渣白兰地"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.35, 0.50],
        "brands": ["Nonino", "Poli", "Nardini", "Berta"],
        "tags": ["grape", "pomace", "strong", "fiery"],
        "origin": "Italy",
    },
    "ouzo": {
        "canonical": "茴香酒",
        "aliases": ["ouzo", "茴香酒", "乌佐酒"],
        "category": "base_spirit",
        "abv": 0.38,
        "abv_range": [0.37, 0.50],
        "brands": ["Ouzo 12", "Plomari", "Tsantali"],
        "tags": ["anise", "black-licorice", "herbal", "aromatic"],
        "origin": "Greece",
    },
    "arak": {
        "canonical": "阿拉克酒",
        "aliases": ["arak", "arack", "阿拉克酒", "中东茴香酒"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.40, 0.63],
        "brands": ["Ksara", "Latifiya", "Kuban"],
        "tags": ["anise", "black-licorice", "herbal"],
        "origin": "Middle East",
    },
    "neutral_spirit": {
        "canonical": "中性酒精",
        "aliases": ["neutral spirit", "neutral alcohol", "中性酒精"],
        "category": "base_spirit",
        "abv": 0.95,
        "abv_range": [0.95, 0.96],
        "brands": ["Everclear", "Spirytus"],
        "tags": ["neutral", "strong", "pure"],
        "origin": "USA/Poland",
    },
    "overproof_rum": {
        "canonical": "高度朗姆酒",
        "aliases": ["overproof rum", "151 rum", "高度朗姆酒", "高酒精度朗姆"],
        "category": "base_spirit",
        "abv": 0.75,
        "abv_range": [0.57, 0.80],
        "brands": ["Bacardi 151", "Lemon Hart 151", "Wray & Nephew Overproof"],
        "tags": ["molasses", "strong", "tropical", "fiery"],
        "origin": "Caribbean/Jamaica",
    },
    "spiced_rum": {
        "canonical": "香料朗姆酒",
        "aliases": ["spiced rum", "香料朗姆酒", "调味朗姆酒"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.35, 0.45],
        "brands": ["Captain Morgan Spiced", "Kraken", "Sailor Jerry"],
        "tags": ["molasses", "spiced", "vanilla", "caramel"],
        "origin": "Caribbean",
    },
    "wheat_vodka": {
        "canonical": "小麦伏特加",
        "aliases": ["wheat vodka", "小麦伏特加"],
        "category": "base_spirit",
        "abv": 0.40,
        "abv_range": [0.37, 0.50],
        "brands": ["Absolut", "Stolichnaya", "Russian Standard"],
        "tags": ["neutral", "clean", "smooth", "wheat"],
        "origin": "Russia/Sweden",
    },
    # === 扩展 II：利口酒 ===
    "aperol": {
        "canonical": "阿佩罗",
        "aliases": ["aperol", "阿佩罗", "aperol apertif"],
        "category": "modifier",
        "abv": 0.11,
        "abv_range": [0.11, 0.15],
        "brands": ["Aperol", "Campari Aperol"],
        "tags": ["bitter", "orange", "sweet", "red"],
        "origin": "Italy",
    },
    "green_chartreuse": {
        "canonical": "绿查特酒",
        "aliases": ["green chartreuse", "chartreuse green", "绿查特酒", "查特绿", "查特绿酒", "绿色查特"],
        "category": "modifier",
        "abv": 0.55,
        "abv_range": [0.55, 0.55],
        "brands": ["Chartreuse V.E.P. Green", "Chartreuse Green"],
        "tags": ["herbal", "mint", "anise", "complex", "monastic"],
        "origin": "France",
    },
    "yellow_chartreuse": {
        "canonical": "黄查特酒",
        "aliases": ["yellow chartreuse", "chartreuse yellow", "黄查特酒", "查特黄"],
        "category": "modifier",
        "abv": 0.40,
        "abv_range": [0.40, 0.43],
        "brands": ["Chartreuse V.E.P. Yellow", "Chartreuse Yellow"],
        "tags": ["herbal", "honey", "sweet", "monastic"],
        "origin": "France",
    },
    "drambuie": {
        "canonical": "杜林标",
        "aliases": ["drambuie", "杜林标", "威士忌力娇酒"],
        "category": "modifier",
        "abv": 0.40,
        "abv_range": [0.40, 0.40],
        "brands": ["Drambuie"],
        "tags": ["whisky-base", "honey", "herbal", "sweet"],
        "origin": "Scotland",
    },
    "frangelico": {
        "canonical": "榛子力娇酒",
        "aliases": ["frangelico", "榛子力娇酒", "榛果力娇酒"],
        "category": "modifier",
        "abv": 0.20,
        "abv_range": [0.20, 0.24],
        "brands": ["Frangelico"],
        "tags": ["hazelnut", "nutty", "sweet", "cocoa"],
        "origin": "Italy",
    },
    "malibu": {
        "canonical": "马利宝",
        "aliases": ["malibu", "马利宝", "椰子朗姆酒", "malibu rum"],
        "category": "modifier",
        "abv": 0.21,
        "abv_range": [0.21, 0.24],
        "brands": ["Malibu Original", "Malibu Black"],
        "tags": ["coconut", "rum-base", "sweet", "tropical"],
        "origin": "Caribbean",
    },
    "sambuca": {
        "canonical": "桑布卡",
        "aliases": ["sambuca", "桑布卡", "意大利茴香力娇酒"],
        "category": "modifier",
        "abv": 0.38,
        "abv_range": [0.38, 0.42],
        "brands": ["Galliano Sambuca", "Romana Sambuca", "Molinari"],
        "tags": ["anise", "black-licorice", "sweet", "herbal"],
        "origin": "Italy",
    },
    "st_germain": {
        "canonical": "接骨木花力娇酒",
        "aliases": ["st germain", "st. germain", "elderflower liqueur", "接骨木花力娇酒"],
        "category": "modifier",
        "abv": 0.20,
        "abv_range": [0.20, 0.25],
        "brands": ["St-Germain", "Bols Elderflower", "Giffard Fleur de Sureau"],
        "tags": ["elderflower", "floral", "sweet", "lychee"],
        "origin": "France",
    },
    "tia_maria": {
        "canonical": "蒂亚玛丽亚",
        "aliases": ["tia maria", "蒂亚玛丽亚", "牙买加咖啡力娇酒"],
        "category": "modifier",
        "abv": 0.20,
        "abv_range": [0.20, 0.26],
        "brands": ["Tia Maria"],
        "tags": ["coffee", "rum-base", "sweet", "vanilla"],
        "origin": "Jamaica",
    },
    "pimms": {
        "canonical": "皮姆酒",
        "aliases": ["pimm's", "pimms", "pimm's no.1", "皮姆酒", "皮姆一号"],
        "category": "modifier",
        "abv": 0.25,
        "abv_range": [0.25, 0.25],
        "brands": ["Pimm's No. 1"],
        "tags": ["gin-base", "fruit", "spice", "herbal"],
        "origin": "UK",
    },
    "fernet": {
        "canonical": "菲奈特",
        "aliases": ["fernet", "fernet branca", "菲奈特", "菲奈特布兰卡"],
        "category": "modifier",
        "abv": 0.39,
        "abv_range": [0.39, 0.45],
        "brands": ["Fernet-Branca", "Fernet Vallet", "Luxardo Fernet"],
        "tags": ["bitter", "mint", "herbal", "medicinal", "dark"],
        "origin": "Italy",
    },
    "cynar": {
        "canonical": "朝鲜蓟力娇酒",
        "aliases": ["cynar", "朝鲜蓟力娇酒", "洋蓟力娇酒"],
        "category": "modifier",
        "abv": 0.165,
        "abv_range": [0.165, 0.165],
        "brands": ["Cynar", "Cynar 70"],
        "tags": ["bitter", "artichoke", "herbal", "earthy"],
        "origin": "Italy",
    },
    "suze": {
        "canonical": "龙胆草力娇酒",
        "aliases": ["suze", "龙胆草力娇酒", "苏兹"],
        "category": "modifier",
        "abv": 0.15,
        "abv_range": [0.15, 0.20],
        "brands": ["Suze"],
        "tags": ["bitter", "gentian", "herbal", "floral"],
        "origin": "France",
    },
    "lillet_blanc": {
        "canonical": "利莱白",
        "aliases": ["lillet blanc", "lillet", "利莱白", "里雷白"],
        "category": "modifier",
        "abv": 0.17,
        "abv_range": [0.17, 0.17],
        "brands": ["Lillet Blanc"],
        "tags": ["wine-fortified", "citrus", "floral", "honey"],
        "origin": "France",
    },
    "lillet_rouge": {
        "canonical": "利莱红",
        "aliases": ["lillet rouge", "利莱红", "里雷红"],
        "category": "modifier",
        "abv": 0.17,
        "abv_range": [0.17, 0.17],
        "brands": ["Lillet Rouge"],
        "tags": ["wine-fortified", "berry", "citrus", "oaky"],
        "origin": "France",
    },
    "dubonnet": {
        "canonical": "杜本内",
        "aliases": ["dubonnet", "dubonnet rouge", "杜本内", "杜本内红"],
        "category": "modifier",
        "abv": 0.15,
        "abv_range": [0.15, 0.15],
        "brands": ["Dubonnet Rouge"],
        "tags": ["wine-fortified", "quinine", "herbal", "sweet"],
        "origin": "France",
    },
    "sloe_gin": {
        "canonical": "黑刺李金酒",
        "aliases": ["sloe gin", "黑刺李金酒", "野梅金酒"],
        "category": "modifier",
        "abv": 0.26,
        "abv_range": [0.26, 0.30],
        "brands": ["Plymouth Sloe Gin", "Sipsam Sloe Gin", "Hayman's Sloe Gin"],
        "tags": ["sloe", "berry", "tart", "gin-base"],
        "origin": "UK",
    },
    "domaine_de_canton": {
        "canonical": "姜汁力娇酒",
        "aliases": ["domaine de canton", "canton", "姜汁力娇酒", "canton ginger"],
        "category": "modifier",
        "abv": 0.28,
        "abv_range": [0.28, 0.28],
        "brands": ["Domaine de Canton"],
        "tags": ["ginger", "spicy", "sweet", "cognac-base"],
        "origin": "France",
    },
    "benedictine": {
        "canonical": "本笃力娇酒",
        "aliases": ["benedictine", "bénédictine", "本笃力娇酒", "本尼狄克汀"],
        "category": "modifier",
        "abv": 0.40,
        "abv_range": [0.40, 0.40],
        "brands": ["Bénédictine D.O.M.", "B&B Bénédictine"],
        "tags": ["herbal", "honey", "spice", "monastic", "complex"],
        "origin": "France",
    },
    "irish_mist": {
        "canonical": "爱尔兰蜜糖力娇酒",
        "aliases": ["irish mist", "爱尔兰蜜糖力娇酒"],
        "category": "modifier",
        "abv": 0.35,
        "abv_range": [0.35, 0.35],
        "brands": ["Irish Mist"],
        "tags": ["whiskey-base", "honey", "herbal", "sweet"],
        "origin": "Ireland",
    },
    "southern_comfort": {
        "canonical": "南方安逸",
        "aliases": ["southern comfort", "南方安逸", "南方舒适"],
        "category": "modifier",
        "abv": 0.35,
        "abv_range": [0.30, 0.50],
        "brands": ["Southern Comfort"],
        "tags": ["whiskey-base", "peach", "sweet", "fruit"],
        "origin": "USA",
    },
    "yukon_jack": {
        "canonical": "育空杰克",
        "aliases": ["yukon jack", "育空杰克"],
        "category": "modifier",
        "abv": 0.50,
        "abv_range": [0.50, 0.50],
        "brands": ["Yukon Jack"],
        "tags": ["whiskey-base", "citrus", "sweet", "strong"],
        "origin": "Canada",
    },
    "fireball": {
        "canonical": "火球肉桂威士忌",
        "aliases": ["fireball", "fireball cinnamon whisky", "火球肉桂威士忌"],
        "category": "modifier",
        "abv": 0.33,
        "abv_range": [0.33, 0.33],
        "brands": ["Fireball Cinnamon Whisky"],
        "tags": ["whiskey-base", "cinnamon", "spicy", "sweet"],
        "origin": "USA/Canada",
    },
    "jagermeister": {
        "canonical": "野格",
        "aliases": ["jagermeister", "jägermeister", "野格", "猎师"],
        "category": "modifier",
        "abv": 0.35,
        "abv_range": [0.35, 0.35],
        "brands": ["Jägermeister"],
        "tags": ["herbal", "anise", "complex", "digestif", "dark"],
        "origin": "Germany",
    },
    "goldschlager": {
        "canonical": "金箔肉桂酒",
        "aliases": ["goldschlager", "goldschläger", "金箔肉桂酒"],
        "category": "modifier",
        "abv": 0.435,
        "abv_range": [0.435, 0.435],
        "brands": ["Goldschläger"],
        "tags": ["cinnamon", "spicy", "sweet", "gold-flake"],
        "origin": "Switzerland",
    },
    "rumplemintz": {
        "canonical": "薄荷伏特加",
        "aliases": ["rumplemintz", "rumple minze", "薄荷伏特加"],
        "category": "modifier",
        "abv": 0.50,
        "abv_range": [0.50, 0.50],
        "brands": ["Rumple Minze"],
        "tags": ["mint", "fresh", "strong", "vodka-base"],
        "origin": "Germany",
    },
    "vanilla_vodka": {
        "canonical": "香草伏特加",
        "aliases": ["vanilla vodka", "香草伏特加"],
        "category": "modifier",
        "abv": 0.35,
        "brands": [],
    },
    "raspberry_vodka": {
        "canonical": "覆盆子伏特加",
        "aliases": ["raspberry vodka", "覆盆子伏特加"],
        "category": "modifier",
        "abv": 0.35,
        "brands": [],
    },
    "citrus_vodka": {
        "canonical": "柑橘伏特加",
        "aliases": ["citrus vodka", "lemon vodka", "柑橘伏特加", "柠檬伏特加"],
        "category": "modifier",
        "abv": 0.35,
        "brands": [],
    },
    "watermelon_liqueur": {
        "canonical": "西瓜力娇酒",
        "aliases": ["watermelon liqueur", "watermelon pucker", "西瓜力娇酒"],
        "category": "modifier",
        "abv": 0.15,
        "brands": [],
    },
    "sour_apple_pucker": {
        "canonical": "酸苹果力娇酒",
        "aliases": ["sour apple pucker", "apple pucker", "酸苹果力娇酒", "苹果力娇酒"],
        "category": "modifier",
        "abv": 0.15,
        "brands": [],
    },
    # === 扩展 II：果汁 ===
    "grapefruit_juice": {
        "canonical": "西柚汁",
        "aliases": ["grapefruit juice", "西柚汁", "葡萄柚汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "apple_juice": {
        "canonical": "苹果汁",
        "aliases": ["apple juice", "苹果汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "peach_juice": {
        "canonical": "蜜桃汁",
        "aliases": ["peach juice", "蜜桃汁", "桃汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "passion_fruit_juice": {
        "canonical": "百香果汁",
        "aliases": ["passion fruit juice", "passionfruit juice", "百香果汁", "热情果汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "guava_juice": {
        "canonical": "番石榴汁",
        "aliases": ["guava juice", "番石榴汁", "芭乐汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "mango_juice": {
        "canonical": "芒果汁",
        "aliases": ["mango juice", "芒果汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "pomegranate_juice": {
        "canonical": "石榴汁",
        "aliases": ["pomegranate juice", "石榴汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "raspberry_juice": {
        "canonical": "覆盆子汁",
        "aliases": ["raspberry juice", "覆盆子汁", "山莓汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "strawberry_juice": {
        "canonical": "草莓汁",
        "aliases": ["strawberry juice", "草莓汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "watermelon_juice": {
        "canonical": "西瓜汁",
        "aliases": ["watermelon juice", "西瓜汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "kiwi_juice": {
        "canonical": "猕猴桃汁",
        "aliases": ["kiwi juice", "猕猴桃汁", "奇异果汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "lychee_juice": {
        "canonical": "荔枝汁",
        "aliases": ["lychee juice", "litchi juice", "荔枝汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "grape_juice": {
        "canonical": "葡萄汁",
        "aliases": ["grape juice", "葡萄汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "carrot_juice": {
        "canonical": "胡萝卜汁",
        "aliases": ["carrot juice", "胡萝卜汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "beet_juice": {
        "canonical": "甜菜汁",
        "aliases": ["beet juice", "beetroot juice", "甜菜汁", "甜菜根汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "celery_juice": {
        "canonical": "芹菜汁",
        "aliases": ["celery juice", "芹菜汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "cucumber_juice": {
        "canonical": "黄瓜汁",
        "aliases": ["cucumber juice", "黄瓜汁"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    "lime_cordial": {
        "canonical": "青柠糖浆",
        "aliases": ["lime cordial", "roses lime cordial", "rose's lime", "青柠糖浆", "青柠浓浆"],
        "category": "juice",
        "abv": 0.0,
        "brands": [],
    },
    # === 扩展 II：糖浆 ===
    "vanilla_syrup": {
        "canonical": "香草糖浆",
        "aliases": ["vanilla syrup", "香草糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "raspberry_syrup": {
        "canonical": "覆盆子糖浆",
        "aliases": ["raspberry syrup", "覆盆子糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "ginger_syrup": {
        "canonical": "姜糖浆",
        "aliases": ["ginger syrup", "姜糖浆", "生姜糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "cinnamon_syrup": {
        "canonical": "肉桂糖浆",
        "aliases": ["cinnamon syrup", "肉桂糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "orgeat_syrup": {
        "canonical": "杏仁糖浆",
        "aliases": ["orgeat syrup", "orgeat", "杏仁糖浆", "奥吉糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "falernum": {
        "canonical": "法勒纳姆",
        "aliases": ["falernum", "法勒纳姆", "法勒南"],
        "category": "modifier",
        "abv": 0.11,
        "brands": [],
    },
    "demerara_syrup": {
        "canonical": "蔗糖糖浆",
        "aliases": ["demerara syrup", "demerara sugar syrup", "蔗糖糖浆", "德梅拉拉糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "maple_syrup": {
        "canonical": "枫糖浆",
        "aliases": ["maple syrup", "枫糖浆", "枫树糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "coconut_syrup": {
        "canonical": "椰子糖浆",
        "aliases": ["coconut syrup", "椰子糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "passion_fruit_syrup": {
        "canonical": "百香果糖浆",
        "aliases": ["passion fruit syrup", "passionfruit syrup", "百香果糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "mango_syrup": {
        "canonical": "芒果糖浆",
        "aliases": ["mango syrup", "芒果糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "strawberry_syrup": {
        "canonical": "草莓糖浆",
        "aliases": ["strawberry syrup", "草莓糖浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    # === 扩展 II：苦精 ===
    "peychauds_bitters": {
        "canonical": "佩肖苦精",
        "aliases": ["peychaud's bitters", "peychauds", "佩肖苦精", "佩查德苦精"],
        "category": "modifier",
        "abv": 0.30,
        "brands": [],
    },
    "celery_bitters": {
        "canonical": "芹菜苦精",
        "aliases": ["celery bitters", "芹菜苦精"],
        "category": "modifier",
        "abv": 0.28,
        "brands": [],
    },
    "grapefruit_bitters": {
        "canonical": "西柚苦精",
        "aliases": ["grapefruit bitters", "西柚苦精"],
        "category": "modifier",
        "abv": 0.28,
        "brands": [],
    },
    "mole_bitters": {
        "canonical": "摩卡苦精",
        "aliases": ["mole bitters", "摩卡苦精"],
        "category": "modifier",
        "abv": 0.28,
        "brands": [],
    },
    "lavender_bitters": {
        "canonical": "薰衣草苦精",
        "aliases": ["lavender bitters", "薰衣草苦精"],
        "category": "modifier",
        "abv": 0.28,
        "brands": [],
    },
    "cardamom_bitters": {
        "canonical": "豆蔻苦精",
        "aliases": ["cardamom bitters", "豆蔻苦精"],
        "category": "modifier",
        "abv": 0.28,
        "brands": [],
    },
    # === 扩展 II：葡萄酒 / 起泡酒 ===
    "white_wine": {
        "canonical": "白葡萄酒",
        "aliases": ["white wine", "白葡萄酒"],
        "category": "wine",
        "abv": 0.12,
        "brands": [],
    },
    "rose_wine": {
        "canonical": "桃红葡萄酒",
        "aliases": ["rose wine", "rosé wine", "桃红葡萄酒", "玫瑰红葡萄酒"],
        "category": "wine",
        "abv": 0.12,
        "brands": [],
    },
    "sherry": {
        "canonical": "雪莉酒",
        "aliases": ["sherry", "雪莉酒", "雪利酒"],
        "category": "wine",
        "abv": 0.17,
        "brands": [],
    },
    "madeira": {
        "canonical": "马德拉",
        "aliases": ["madeira", "madeira wine", "马德拉", "马德拉酒"],
        "category": "wine",
        "abv": 0.18,
        "brands": [],
    },
    "marsala": {
        "canonical": "马沙拉",
        "aliases": ["marsala", "marsala wine", "马沙拉", "马沙拉酒"],
        "category": "wine",
        "abv": 0.17,
        "brands": [],
    },
    "sake": {
        "canonical": "清酒",
        "aliases": ["sake", "清酒", "日本清酒"],
        "category": "wine",
        "abv": 0.15,
        "brands": [],
    },
    "mirin": {
        "canonical": "味醂",
        "aliases": ["mirin", "味醂", "甜味淋"],
        "category": "wine",
        "abv": 0.14,
        "brands": [],
    },
    # === 扩展 II：苏打 / 碳酸饮料 ===
    "club_soda": {
        "canonical": "俱乐部苏打",
        "aliases": ["club soda", "俱乐部苏打"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "ginger_ale": {
        "canonical": "姜汁汽水",
        "aliases": ["ginger ale", "姜汁汽水"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "lemon_lime_soda": {
        "canonical": "柠檬青柠汽水",
        "aliases": ["lemon lime soda", "lemon-lime soda", "7-up", "7up", "sprite", "柠檬青柠汽水", "雪碧", "七喜"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "energy_drink": {
        "canonical": "能量饮料",
        "aliases": ["energy drink", "red bull", "redbull", "能量饮料", "红牛"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "coconut_water": {
        "canonical": "椰子水",
        "aliases": ["coconut water", "椰子水"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "root_beer": {
        "canonical": "根汁啤酒",
        "aliases": ["root beer", "根汁啤酒", "根啤"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "cream_soda": {
        "canonical": "奶油苏打",
        "aliases": ["cream soda", "奶油苏打"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "seltzer": {
        "canonical": "气泡水",
        "aliases": ["seltzer", "seltzer water", "气泡水"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "apple_cider": {
        "canonical": "苹果汽酒",
        "aliases": ["apple cider", "cider", "苹果汽酒", "苹果酒"],
        "category": "modifier",
        "abv": 0.05,
        "brands": [],
    },
    "beer": {
        "canonical": "啤酒",
        "aliases": ["beer", "lager", "ale", "啤酒", "淡啤酒"],
        "category": "modifier",
        "abv": 0.05,
        "brands": [],
    },
    # === 扩展 II：乳制品 ===
    "milk": {
        "canonical": "牛奶",
        "aliases": ["milk", "whole milk", "牛奶", "全脂牛奶"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "half_and_half": {
        "canonical": "半奶半奶油",
        "aliases": ["half and half", "半奶半奶油"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "evaporated_milk": {
        "canonical": "淡奶",
        "aliases": ["evaporated milk", "淡奶", "脱水牛奶"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "condensed_milk": {
        "canonical": "炼乳",
        "aliases": ["condensed milk", "sweetened condensed milk", "炼乳", "甜炼乳"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "coconut_milk": {
        "canonical": "椰奶",
        "aliases": ["coconut milk", "椰奶"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "soy_milk": {
        "canonical": "豆奶",
        "aliases": ["soy milk", "soymilk", "豆奶", "豆浆"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "yogurt": {
        "canonical": "酸奶",
        "aliases": ["yogurt", "yoghurt", "酸奶", "酸乳"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    # === 扩展 II：装饰 ===
    "lime_wedge": {
        "canonical": "青柠角",
        "aliases": ["lime wedge", "青柠角", "莱姆角"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "orange_slice": {
        "canonical": "橙片",
        "aliases": ["orange slice", "orange", "橙片", "橙角"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "lime_wheel": {
        "canonical": "青柠轮",
        "aliases": ["lime wheel", "青柠轮", "莱姆轮片"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "lemon_wheel": {
        "canonical": "柠檬轮",
        "aliases": ["lemon wheel", "柠檬轮", "柠檬轮片"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "mint_sprig": {
        "canonical": "薄荷枝",
        "aliases": ["mint sprig", "薄荷枝", "薄荷尖"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "basil": {
        "canonical": "罗勒",
        "aliases": ["basil", "basil leaves", "罗勒", "九层塔"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "rosemary": {
        "canonical": "迷迭香",
        "aliases": ["rosemary", "rosemary sprig", "迷迭香"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "thyme": {
        "canonical": "百里香",
        "aliases": ["thyme", "thyme sprig", "百里香"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "cinnamon_stick": {
        "canonical": "肉桂棒",
        "aliases": ["cinnamon stick", "cinnamon", "肉桂棒", "桂皮"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "star_anise": {
        "canonical": "八角",
        "aliases": ["star anise", "八角", "大茴香"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "nutmeg": {
        "canonical": "肉豆蔻",
        "aliases": ["nutmeg", "肉豆蔻", "豆蔻粉"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "sugar_rim": {
        "canonical": "糖边",
        "aliases": ["sugar rim", "糖边", "糖圈"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "salt_rim": {
        "canonical": "盐边",
        "aliases": ["salt rim", "盐边", "盐圈"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "cucumber": {
        "canonical": "黄瓜",
        "aliases": ["cucumber", "cucumber slice", "黄瓜", "黄瓜片"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "celery_stalk": {
        "canonical": "芹菜梗",
        "aliases": ["celery stalk", "celery", "芹菜梗", "芹菜"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "jalapeno": {
        "canonical": "墨西哥辣椒",
        "aliases": ["jalapeno", "jalapeño", "墨西哥辣椒", "墨西哥青辣椒"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "edible_flower": {
        "canonical": "食用花",
        "aliases": ["edible flower", "edible flowers", "食用花", "可食用花"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    "coffee_beans": {
        "canonical": "咖啡豆",
        "aliases": ["coffee beans", "coffee bean", "咖啡豆"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
    },
    # === 扩展 II：调味 / 其他 ===
    "white_sugar": {
        "canonical": "白糖",
        "aliases": ["white sugar", "granulated sugar", "白糖", "白砂糖", "糖"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
        "tags": ["sweet", "neutral"],
    },
    "brown_sugar": {
        "canonical": "红糖",
        "aliases": ["brown sugar", "红糖", "棕糖", "黑糖"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "powdered_sugar": {
        "canonical": "糖粉",
        "aliases": ["powdered sugar", "icing sugar", "糖粉", "糖霜"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "salt": {
        "canonical": "盐",
        "aliases": ["salt", "sea salt", "盐", "食盐", "海盐"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "black_pepper": {
        "canonical": "黑胡椒",
        "aliases": ["black pepper", "pepper", "黑胡椒", "胡椒"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "tabasco": {
        "canonical": "塔巴斯科",
        "aliases": ["tabasco", "tabasco sauce", "塔巴斯科", "辣椒仔"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "worcestershire_sauce": {
        "canonical": "伍斯特酱",
        "aliases": ["worcestershire sauce", "worcestershire", "伍斯特酱", "辣酱油"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "soy_sauce": {
        "canonical": "酱油",
        "aliases": ["soy sauce", "酱油", "生抽"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "vanilla_extract": {
        "canonical": "香草精",
        "aliases": ["vanilla extract", "vanilla essence", "香草精", "香草提取物"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "hot_sauce": {
        "canonical": "辣酱",
        "aliases": ["hot sauce", "辣酱", "辣椒酱"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    # === 扩展 II：果泥 / 果肉 ===
    "raspberry_puree": {
        "canonical": "覆盆子泥",
        "aliases": ["raspberry puree", "覆盆子泥", "山莓泥"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "mango_puree": {
        "canonical": "芒果泥",
        "aliases": ["mango puree", "芒果泥"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "passion_fruit_puree": {
        "canonical": "百香果泥",
        "aliases": ["passion fruit puree", "passionfruit puree", "百香果泥"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "strawberry_puree": {
        "canonical": "草莓泥",
        "aliases": ["strawberry puree", "草莓泥"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "peach_puree": {
        "canonical": "蜜桃泥",
        "aliases": ["peach puree", "蜜桃泥", "桃泥"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    "banana": {
        "canonical": "香蕉",
        "aliases": ["banana", "banana puree", "香蕉", "香蕉泥"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
    },
    # === 阶段 A：IBA 种子配方补充材料 ===
    "coffee": {
        "canonical": "咖啡",
        "aliases": ["coffee", "hot coffee", "brewed coffee", "咖啡", "热咖啡"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
        "tags": ["coffee", "roasted", "bitter", "warm"],
        "origin": "",
    },
    "lemon_liqueur": {
        "canonical": "柠檬利口酒",
        "aliases": ["lemon liqueur", "limoncello", "柠檬利口酒", "柠檬力娇酒"],
        "category": "modifier",
        "abv": 0.30,
        "abv_range": [0.25, 0.32],
        "brands": ["Limoncello", "Caravella", "Pallini", "Luxardo Limoncello"],
        "tags": ["lemon", "citrus", "sweet", "zesty"],
        "origin": "Italy",
    },
    "olive_juice": {
        "canonical": "橄榄汁",
        "aliases": ["olive juice", "olive brine", "橄榄汁", "橄榄盐水"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
        "tags": ["briny", "savory", "salty"],
        "origin": "",
    },
    "orange_flower_water": {
        "canonical": "橙花水",
        "aliases": ["orange flower water", "orange blossom water", "橙花水", "橙花纯露"],
        "category": "modifier",
        "abv": 0.0,
        "brands": [],
        "tags": ["floral", "orange-blossom", "aromatic"],
        "origin": "France/Middle East",
    },
    "violet_liqueur": {
        "canonical": "紫罗兰力娇酒",
        "aliases": ["violet liqueur", "crème de violette", "creme de violette", "紫罗兰力娇酒", "紫罗兰利口酒"],
        "category": "modifier",
        "abv": 0.20,
        "abv_range": [0.16, 0.25],
        "brands": ["Rothman & Winter Crème de Violette", "The Bitter Truth Violet Liqueur"],
        "tags": ["floral", "violet", "sweet", "perfumed"],
        "origin": "France/Austria",
    },
    "lime": {
        "canonical": "青柠",
        "aliases": ["lime", "lime fruit", "fresh lime", "青柠", "新鲜青柠"],
        "category": "garnish",
        "abv": 0.0,
        "brands": [],
        "tags": ["citrus", "lime", "fresh", "sour"],
        "origin": "",
    },
    "cherry_liqueur_heering": {
        "canonical": "黑樱桃力娇酒",
        "aliases": ["cherry liqueur", "black cherry liqueur", "heering", "peter heering", "黑樱桃力娇酒", "黑樱桃酒"],
        "category": "modifier",
        "abv": 0.24,
        "abv_range": [0.20, 0.30],
        "brands": ["Peter Heering Cherry Liqueur", "Bols Cherry Brandy", "De Kuyper Cherry"],
        "tags": ["cherry", "dark-fruit", "sweet", "stone-fruit"],
        "origin": "Denmark/Netherlands",
    },
}

# 反向索引：alias(小写) → canonical
_ALIAS_INDEX: dict[str, str] = {}
for _key, _info in INGREDIENT_REGISTRY.items():
    _canon = _info["canonical"]
    # 标准名本身也加入索引
    _ALIAS_INDEX[_canon.lower()] = _canon
    for _alias in _info["aliases"]:
        _ALIAS_INDEX[_alias.lower()] = _canon


def canonicalize(name: str) -> str:
    """将别名归一化为标准名。未知材料返回原值。"""
    if not name:
        return name
    return _ALIAS_INDEX.get(name.strip().lower(), name.strip())


def get_category(canonical: str) -> str | None:
    """根据标准名获取分类。"""
    for _info in INGREDIENT_REGISTRY.values():
        if _info["canonical"] == canonical:
            return _info["category"]
    return None


def list_by_category(category: str) -> list[str]:
    """列出某分类下所有材料标准名。"""
    return [
        info["canonical"]
        for info in INGREDIENT_REGISTRY.values()
        if info["category"] == category
    ]


def all_canonical() -> list[str]:
    """列出所有材料标准名。"""
    return [info["canonical"] for info in INGREDIENT_REGISTRY.values()]


def get_abv(canonical: str) -> float:
    """根据标准名获取 ABV（0.0-1.0）。未知材料返回 0.0。"""
    for _info in INGREDIENT_REGISTRY.values():
        if _info["canonical"] == canonical:
            return _info.get("abv", 0.0)
    return 0.0


def get_brands(canonical: str) -> list[str]:
    """根据标准名获取常见品牌列表。未知材料返回空列表。"""
    for _info in INGREDIENT_REGISTRY.values():
        if _info["canonical"] == canonical:
            return list(_info.get("brands", []))
    return []


# === P2-A: 新增字段查询函数（向后兼容：字段缺失返回默认值） ===
def get_tags(canonical: str) -> list[str]:
    """根据标准名获取风味标签列表。未知或无标签材料返回空列表。

    用于风味查询与推荐（如"柑橘调"材料、"smoky"威士忌）。
    """
    for _info in INGREDIENT_REGISTRY.values():
        if _info["canonical"] == canonical:
            return list(_info.get("tags", []))
    return []


def get_origin(canonical: str) -> str:
    """根据标准名获取产地。未知或无产地返回空字符串。"""
    for _info in INGREDIENT_REGISTRY.values():
        if _info["canonical"] == canonical:
            return str(_info.get("origin", ""))
    return ""


def get_abv_range(canonical: str) -> tuple[float, float] | None:
    """根据标准名获取 ABV 实际范围 (min, max)。未知或无范围返回 None。

    abv 是典型值，abv_range 是实际产品的波动范围，
    用于校准估算（如伏特加 0.37-0.50，而 0.40 是常见值）。
    """
    for _info in INGREDIENT_REGISTRY.values():
        if _info["canonical"] == canonical:
            rng = _info.get("abv_range")
            if isinstance(rng, list) and len(rng) == 2:
                return float(rng[0]), float(rng[1])
            return None
    return None


def find_by_tags(tags: list[str], match_all: bool = False) -> list[str]:
    """按风味标签查询材料标准名。

    Args:
        tags: 标签列表（如 ["citrus", "sweet"]）
        match_all: True=AND（必须全部命中），False=OR（任一命中）

    Returns:
        匹配材料的 canonical 列表（按注册表顺序）
    """
    if not tags:
        return []
    tag_set = {t.lower() for t in tags}
    result: list[str] = []
    for _info in INGREDIENT_REGISTRY.values():
        item_tags = {t.lower() for t in _info.get("tags", [])}
        if not item_tags:
            continue
        if match_all:
            if tag_set.issubset(item_tags):
                result.append(_info["canonical"])
        else:
            if tag_set & item_tags:
                result.append(_info["canonical"])
    return result


def find_by_origin(origin_keyword: str) -> list[str]:
    """按产地关键词查询材料标准名（模糊匹配，大小写不敏感）。

    Args:
        origin_keyword: 产地关键词（如 "France"、"China"、"Italy"）

    Returns:
        匹配材料的 canonical 列表
    """
    if not origin_keyword:
        return []
    kw = origin_keyword.lower()
    result: list[str] = []
    for _info in INGREDIENT_REGISTRY.values():
        origin = str(_info.get("origin", "")).lower()
        if not origin:
            continue
        if kw in origin:
            result.append(_info["canonical"])
    return result


def all_tags() -> list[str]:
    """列出注册表中所有出现过的风味标签（去重 + 排序）。

    用于前端展示标签筛选器。
    """
    tag_set: set[str] = set()
    for _info in INGREDIENT_REGISTRY.values():
        for t in _info.get("tags", []):
            tag_set.add(t.lower())
    return sorted(tag_set)


def all_origins() -> list[str]:
    """列出注册表中所有出现过的产地（去重 + 排序）。

    用于前端展示产地筛选器。
    """
    origin_set: set[str] = set()
    for _info in INGREDIENT_REGISTRY.values():
        origin = str(_info.get("origin", "")).strip()
        if origin:
            # 拆分多产地字符串（如 "Netherlands/UK" → ["Netherlands", "UK"]）
            for part in origin.split("/"):
                part = part.strip()
                if part:
                    origin_set.add(part)
    return sorted(origin_set)
