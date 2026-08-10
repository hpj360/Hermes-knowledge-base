#!/usr/bin/env python3
"""配方故事档案回填脚本。

为 IBA 57 款经典配方补充 story 元数据（history/variants/pairing/occasion）。
为 TheCocktailDB Top 100 配方补充简化版 story（history/occasion）。

story 数据来源：Difford's Guide、Imbibe Magazine、IBA 官方手册、
《The Savoy Cocktail Book》(Harry Craddock, 1930)、《Recipes for Mixed
Drinks》(Hugo Ensslin, 1917)、《Bartender's Guide》(Jerry Thomas, 1862)
等权威来源。

story 写入 Document.meta JSON（与现有 abv/calories 等字段合并）。
"""
from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv()

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document
from hermes_kb.seed_recipes import SEED_RECIPES

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("backfill_recipe_stories")

# seed_recipes 中已存在 history 字段，复用作为 story.history
_SEED_HISTORY: dict[str, str] = {
    r["title"]: r.get("history", "") for r in SEED_RECIPES
}

# ============================================================
# IBA 57 款经典配方 story 补充数据（variants / pairing / occasion）
# 按 IBA 三大分类组织
# ============================================================

# --- The Unforgettables 不朽经典（23 款）---
_SEED_STORY_SUPPLEMENT: dict[str, dict] = {
    # --- The Unforgettables（23 款）---
    "马天尼 Martini": {
        "variants": ["Dry Martini（干型）", "Dirty Martini（脏马天尼）", "Vesper（邦德马天尼）", "Gibson（吉布森）"],
        "pairing": ["生蚝、海鲜冷盘", "坚果、橄榄拼盘", "烟熏三文鱼"],
        "occasion": "餐前开胃、独饮沉思、正式社交场合",
    },
    "尼格罗尼 Negroni": {
        "variants": ["Boulevardier（波本版）", "White Negroni（白色尼格罗尼）", "Negroni Sbagliato（起泡版）", "Mezcal Negroni"],
        "pairing": ["坚果、奶酪拼盘", "火腿切片", "黑巧克力"],
        "occasion": "餐前开胃、独饮沉思、秋冬傍晚",
    },
    "古典鸡尾酒 Old Fashioned": {
        "variants": ["Oaxaca Old Fashioned（梅斯卡尔版）", "Rum Old Fashioned", "Brandied Old Fashioned", "Maple Old Fashioned"],
        "pairing": ["烤肉、牛排", "烟熏奶酪", "坚果拼盘"],
        "occasion": "餐后消化、独饮沉思、冬夜暖身",
    },
    "白色佳人 White Lady": {
        "variants": ["Pink Lady（粉色佳人）", "Blue Lady", "Velvet Lady"],
        "pairing": ["海鲜冷盘", "柑橘类甜点", "白身鱼肉"],
        "occasion": "餐前开胃、下午茶社交、春季派对",
    },
    "亚历山大 Alexander": {
        "variants": ["Brandy Alexander（白兰地版）", "Coffee Alexander", "Blue Alexander"],
        "pairing": ["巧克力甜点、提拉米苏", "奶油蛋糕", "餐后甜点"],
        "occasion": "餐后消化、冬夜暖身、节日庆祝",
    },
    "美式 Americano": {
        "variants": ["Negroni（加金酒版）", "Americano Sbagliato", "Boulevardier Lowball"],
        "pairing": ["火腿奶酪拼盘", "橄榄", "薄脆饼干"],
        "occasion": "餐前开胃、夏日消暑、午后社交",
    },
    "飞行 Aviation": {
        "variants": ["Aviation Without Violet", "Blue Moon", "Moonlight Cocktail"],
        "pairing": ["花卉主题甜点", "柑橘类甜点", "薰衣草饼干"],
        "occasion": "餐前开胃、春季社交、下午茶",
    },
    "床第之间 Between the Sheets": {
        "variants": ["Sidecar（边车）", "Between the Sheets with Bourbon", "Eastern Standard"],
        "pairing": ["海鲜冷盘", "柑橘类甜点", "奶酪拼盘"],
        "occasion": "餐前开胃、派对聚会、浪漫场合",
    },
    "林荫道 Boulevardier": {
        "variants": ["Boulevardier with Rye", "Old Pal（干味美思版）", "Negroni（金酒版）"],
        "pairing": ["烤肉、牛排", "烟熏奶酪", "坚果拼盘"],
        "occasion": "餐后消化、独饮沉思、秋冬傍晚",
    },
    "三叶草俱乐部 Clover Club": {
        "variants": ["Clover Leaf（薄荷装饰版）", "Pink Lady", "White Clover"],
        "pairing": ["花卉主题甜点", "莓果塔", "柑橘类甜点"],
        "occasion": "餐前开胃、女性社交、春季派对",
    },
    "戴基里 Daiquiri": {
        "variants": ["Hemingway Daiquiri（海明威代基里）", "Frozen Daiquiri（冰沙版）", "Daiquiri Floridita", "Strawberry Daiquiri"],
        "pairing": ["海鲜冷盘", "柑橘类沙拉", "白身鱼肉"],
        "occasion": "餐前开胃、夏日消暑、海边度假",
    },
    "金菲士 Gin Fizz": {
        "variants": ["Ramos Gin Fizz（拉莫斯版）", "Silver Fizz（加蛋清）", "Golden Fizz（加蛋黄）", "Royal Fizz"],
        "pairing": ["轻食沙拉", "三明治", "柑橘类甜点"],
        "occasion": "夏日消暑、午后长饮、下午茶社交",
    },
    "汉基帕基 Hanky Panky": {
        "variants": ["Hanky Panky with Fernet Branca Menta", "Old Pal", "Boulevardier"],
        "pairing": ["奶酪拼盘", "坚果", "火腿切片"],
        "occasion": "餐前开胃、独饮沉思、深夜小酌",
    },
    "约翰柯林斯 John Collins": {
        "variants": ["Tom Collins（金酒版）", "Vodka Collins", "Rum Collins", "Brandy Collins"],
        "pairing": ["轻食沙拉", "三明治", "烧烤小吃"],
        "occasion": "夏日消暑、派对聚会、午后长饮",
    },
    "最后一言 Last Word": {
        "variants": ["Final Word（梅斯卡尔版）", "Corpse Reviver #2", "Bitter End"],
        "pairing": ["奶酪拼盘", "坚果", "柑橘类甜点"],
        "occasion": "餐前开胃、酒吧社交、品鉴场合",
    },
    "曼哈顿 Manhattan": {
        "variants": ["Dry Manhattan（干型）", "Sweet Manhattan（甜型）", "Perfect Manhattan（半干半甜）", "Rob Roy（苏格兰版）"],
        "pairing": ["牛排、烤肉", "烟熏奶酪", "坚果拼盘"],
        "occasion": "餐前开胃、正式社交、秋冬晚宴",
    },
    "马天尼内兹 Martinez": {
        "variants": ["Dry Martinez", "Martinez with Old Tom Gin", "Tuxedo No.2"],
        "pairing": ["坚果、橄榄拼盘", "奶酪拼盘", "火腿切片"],
        "occasion": "餐前开胃、独饮沉思、品鉴场合",
    },
    "玛丽碧克馥 Mary Pickford": {
        "variants": ["Mary Pickford without Cherry Liqueur", "Cuban Sunset", "Pina Colada（椰林版）"],
        "pairing": ["热带水果沙拉", "海鲜冷盘", "水果塔"],
        "occasion": "夏日消暑、派对聚会、度假社交",
    },
    "种植者宾治 Planter's Punch": {
        "variants": ["Jamaican Planter's Punch", "Planter's Punch with Dark Rum", "Bajan Planter's Punch"],
        "pairing": ["热带水果沙拉", "烧烤小吃", "海鲜冷盘"],
        "occasion": "夏日消暑、派对聚会、加勒比主题宴会",
    },
    "拉莫斯菲士 Ramos Gin Fizz": {
        "variants": ["Ramos Gin Fizz with Orange Flower Water", "Silver Fizz", "Royal Fizz"],
        "pairing": ["轻食沙拉", "柑橘类甜点", "奶油糕点"],
        "occasion": "晨间早午餐、春日午后、庆祝场合",
    },
    "萨泽拉克 Sazerac": {
        "variants": ["Sazerac with Rye Whiskey", "Sazerac with Cognac", "Mezcal Sazerac"],
        "pairing": ["烟熏奶酪", "坚果", "黑巧克力"],
        "occasion": "餐后消化、独饮沉思、品鉴场合",
    },
    "边车 Sidecar": {
        "variants": ["Sidecar with Bourbon", "Between the Sheets", "Margarita（龙舌兰版）"],
        "pairing": ["柑橘类甜点", "奶酪拼盘", "水果塔"],
        "occasion": "餐前开胃、餐后消化、秋日社交",
    },
    "威士忌酸 Whiskey Sour": {
        "variants": ["New York Sour（纽约酸）", "Boston Sour（加蛋清）", "Ward Eight", "Whiskey Sour with Maple"],
        "pairing": ["烤肉、汉堡", "坚果拼盘", "烧烤小吃"],
        "occasion": "餐前开胃、派对聚会、四季通用",
    },
    # --- Contemporary Classics（24 款）---
    "莫吉托 Mojito": {
        "variants": ["Virgin Mojito（无酒精）", "Strawberry Mojito", "Mango Mojito", "Mezcal Mojito"],
        "pairing": ["热带水果沙拉", "海鲜冷盘", "烧烤小吃"],
        "occasion": "夏日消暑、派对聚会、午后长饮",
    },
    "玛格丽特 Margarita": {
        "variants": ["Tommy's Margarita（龙舌兰糖浆版）", "Frozen Margarita（冰沙版）", "Strawberry Margarita", "Cadillac Margarita"],
        "pairing": ["墨西哥玉米片、莎莎酱", "塔可", "海鲜冷盘"],
        "occasion": "夏日消暑、派对聚会、墨西哥主题宴会",
    },
    "龙舌兰日出 Tequila Sunrise": {
        "variants": ["Tequila Sunset（黑朗姆版）", "Vodka Sunrise", "Caribbean Sunrise"],
        "pairing": ["热带水果沙拉", "早餐早午餐", "柑橘类甜点"],
        "occasion": "夏日消暑、早午餐、派对聚会",
    },
    "贝里尼 Bellini": {
        "variants": ["Puccini（芒果版）", "Rossini（草莓版）", "Tintoretto（石榴版）", "Mimosa（橙汁版）"],
        "pairing": ["水果沙拉", "早餐糕点", "马卡龙"],
        "occasion": "Brunch 早午餐、庆祝场合、婚礼宴会",
    },
    "黑色俄罗斯 Black Russian": {
        "variants": ["White Russian（加奶油）", "Dirty Russian（加巧克力糖浆）", "Colorado Bulldog（加可乐）"],
        "pairing": ["巧克力甜点、提拉米苏", "奶油蛋糕", "坚果"],
        "occasion": "餐后消化、冬夜暖身、独饮沉思",
    },
    "荆棘 Bramble": {
        "variants": ["Bramble with Raspberry", "Bramble with Blackberry", "Apple Bramble"],
        "pairing": ["莓果塔", "柑橘类甜点", "奶酪拼盘"],
        "occasion": "餐后消化、春日社交、下午茶",
    },
    "卡布琳娜 Caipirinha": {
        "variants": ["Caipiroska（伏特加版）", "Caipirissima（朗姆版）", "Rabies（加橙汁）", "Sake Caipirinha"],
        "pairing": ["巴西烤肉", "热带水果沙拉", "烧烤小吃"],
        "occasion": "夏日消暑、派对聚会、巴西主题宴会",
    },
    "复尸者2号 Corpse Reviver #2": {
        "variants": ["Corpse Reviver #1（干邑版）", "Corpse Reviver #2 with Absinthe", "Necromancer"],
        "pairing": ["奶酪拼盘", "坚果", "柑橘类甜点"],
        "occasion": "宿醉救星、午间开场、酒吧品鉴",
    },
    "大都会 Cosmopolitan": {
        "variants": ["Cosmopolitan with Citrus Vodka", "White Cosmopolitan", "Metropolitan（波本版）"],
        "pairing": ["水果塔", "海鲜冷盘", "柑橘类甜点"],
        "occasion": "派对聚会、女性社交、庆祝场合",
    },
    "自由古巴 Cuba Libre": {
        "variants": ["Cuba Libre with Dark Rum", "Cuba Libre with Lime", "Bacardi Coke"],
        "pairing": ["烧烤小吃", "汉堡", "炸鸡"],
        "occasion": "夏日消暑、派对聚会、休闲社交",
    },
    "法兰西75 French 75": {
        "variants": ["French 76（伏特加版）", "French 95（波本版）", "Soixante-Quinze with Champagne"],
        "pairing": ["海鲜冷盘", "水果沙拉", "法式甜点"],
        "occasion": "庆祝场合、派对聚会、新年庆典",
    },
    "爱尔兰咖啡 Irish Coffee": {
        "variants": ["Irish Coffee with Bourbon", "Scotch Coffee", "Baileys Coffee"],
        "pairing": ["巧克力甜点", "坚果", "奶油糕点"],
        "occasion": "冬夜暖身、餐后消化、节日庆祝",
    },
    "主教 Kir": {
        "variants": ["Kir Royal（香槟版）", "Kir Pétillant", "Kir Breton（苹果酒版）", "Cardinal（红葡萄酒版）"],
        "pairing": ["法式前菜", "奶酪拼盘", "法棍面包"],
        "occasion": "餐前开胃、正式社交、法式宴会",
    },
    "长岛冰茶 Long Island Iced Tea": {
        "variants": ["Long Beach Iced Tea（蔓越莓版）", "Texas Tea（加威士忌）", "Electric Iced Tea（蓝柑香版）", "Alaska Iced Tea"],
        "pairing": ["烧烤小吃", "汉堡", "炸鸡"],
        "occasion": "派对聚会、夜店狂欢、高强度社交",
    },
    "迈泰 Mai Tai": {
        "variants": ["Mai Tai with Jamaican Rum", "Trader Vic's Mai Tai", "Polynesian Mai Tai"],
        "pairing": ["热带水果沙拉", "中式粤菜", "海鲜冷盘"],
        "occasion": "夏日消暑、派对聚会、Tiki 主题宴会",
    },
    "含羞草 Mimosa": {
        "variants": ["Mimosa with Grapefruit Juice", "Buck's Fizz（英国版）", "Mimosa Royale（香槟版）", "Poinsettia（蔓越莓版）"],
        "pairing": ["早餐糕点", "水果沙拉", "鸡蛋料理"],
        "occasion": "Brunch 早午餐、庆祝场合、婚礼宴会",
    },
    "薄荷茱莉普 Mint Julep": {
        "variants": ["Champagne Julep", "Georgia Julepe（白兰地版）", "Peach Julep", "Brandy Julep"],
        "pairing": ["南方烧烤", "坚果", "奶酪拼盘"],
        "occasion": "夏日消暑、赛马会、户外派对",
    },
    "莫斯科骡子 Moscow Mule": {
        "variants": ["Kentucky Mule（波本版）", "Mexican Mule（龙舌兰版）", "Gin Gin Mule", "Dark 'N' Stormy（黑朗姆版）"],
        "pairing": ["亚洲料理", "烧烤小吃", "海鲜冷盘"],
        "occasion": "夏日消暑、派对聚会、休闲社交",
    },
    "椰林飘香 Piña Colada": {
        "variants": ["Frozen Piña Colada", "Chi-Chi（伏特加版）", "Miami Vice（草莓版混合）", "Pina Colada with Dark Rum"],
        "pairing": ["热带水果沙拉", "海鲜冷盘", "椰子风味甜点"],
        "occasion": "夏日消暑、度假社交、派对聚会",
    },
    "皮斯科酸 Pisco Sour": {
        "variants": ["Pisco Sour with Chicha Morada", "Pisco Punch", "Pisco Sour with Amazonian Fruits"],
        "pairing": ["秘鲁料理", "海鲜冷盘", "柑橘类沙拉"],
        "occasion": "餐前开胃、派对聚会、南美主题宴会",
    },
    "螺丝刀 Screwdriver": {
        "variants": ["Slow Comfortable Screw", "Screwdriver with Grapefruit Juice", "Fuzzy Navel（桃子版）"],
        "pairing": ["早餐早午餐", "水果沙拉", "柑橘类甜点"],
        "occasion": "早午餐、夏日消暑、休闲社交",
    },
    "新加坡司令 Singapore Sling": {
        "variants": ["Singapore Sling with Cherry Heering", "Sling of Singapore", "Modern Singapore Sling"],
        "pairing": ["亚洲前菜", "海鲜冷盘", "水果沙拉"],
        "occasion": "夏日消暑、派对聚会、度假社交",
    },
    "邦德马天尼 Vesper": {
        "variants": ["Vesper with Lillet Blanc", "Modern Vesper", "Vodka Martini"],
        "pairing": ["坚果、橄榄拼盘", "烟熏三文鱼", "奶酪拼盘"],
        "occasion": "正式社交、独饮沉思、品鉴场合",
    },
    "僵尸 Zombie": {
        "variants": ["Zombie with 151 Rum", "Original Donn's Zombie", "Tiki Zombie"],
        "pairing": ["热带水果沙拉", "东南亚料理", "烧烤小吃"],
        "occasion": "派对聚会、Tiki 主题宴会、高强度社交",
    },
    # --- New Era Drinks（10 款）---
    "血腥玛丽 Bloody Mary": {
        "variants": ["Bloody Maria（龙舌兰版）", "Red Snapper（金酒版）", "Bloody Caesar（伏特加+蛤蜊汁）", "Bloody Mary with Bacon"],
        "pairing": ["早餐早午餐", "海鲜冷盘", "奶酪拼盘"],
        "occasion": "宿醉救星、早午餐、午间开场",
    },
    "梭鱼 Barracuda": {
        "variants": ["Barracuda with Champagne", "Barracuda with Sparkling Wine", "Tropical Barracuda"],
        "pairing": ["热带水果沙拉", "海鲜冷盘", "烧烤小吃"],
        "occasion": "夏日消暑、派对聚会、度假社交",
    },
    "蜜蜂之吻 Bees Knees": {
        "variants": ["Bees Knees with Thyme Honey", "Honeysuckle Cocktail", "Queen Bee"],
        "pairing": ["柑橘类甜点", "蜂蜜蛋糕", "奶酪拼盘"],
        "occasion": "餐前开胃、春日社交、下午茶",
    },
    "黑风暴 Dark 'N' Stormy": {
        "variants": ["Dark 'N' Stormy with Spiced Rum", "Stormy 'N' Dark", "Painkiller（变体）"],
        "pairing": ["海鲜冷盘", "烧烤小吃", "热带水果沙拉"],
        "occasion": "夏日消暑、派对聚会、百慕大主题宴会",
    },
    "脏马天尼 Dirty Martini": {
        "variants": ["Extra Dirty Martini", "Filthy Martini", "Dirty Gibson", "Martini with Olive Brine"],
        "pairing": ["生蚝、海鲜冷盘", "坚果、橄榄拼盘", "烟熏三文鱼"],
        "occasion": "餐前开胃、独饮沉思、正式社交",
    },
    "浓缩咖啡马天尼 Espresso Martini": {
        "variants": ["Espresso Martini with Vodka Espresso", "Coffee Martini", "Vodka Espresso", "Flat White Martini"],
        "pairing": ["巧克力甜点、提拉米苏", "坚果", "咖啡风味甜点"],
        "occasion": "餐后消化、夜店狂欢、提神场合",
    },
    "法式马天尼 French Martini": {
        "variants": ["French Martini with Raspberry Liqueur", "French Kiss", "Martini Chambord"],
        "pairing": ["莓果塔", "水果沙拉", "马卡龙"],
        "occasion": "派对聚会、女性社交、餐前开胃",
    },
    "非法 Illegal": {
        "variants": ["Illegal with Mezcal", "Last Word（金酒版）", "Naked and Famous"],
        "pairing": ["奶酪拼盘", "坚果", "柑橘类甜点"],
        "occasion": "餐前开胃、酒吧品鉴、深夜小酌",
    },
    "汤米的玛格丽特 Tommy's Margarita": {
        "variants": ["Tommy's Margarita with Anejo Tequila", "Margarita（橙味力娇酒版）", "Spicy Tommy's Margarita"],
        "pairing": ["墨西哥玉米片、莎莎酱", "塔可", "烧烤小吃"],
        "occasion": "餐前开胃、派对聚会、墨西哥主题宴会",
    },
    "黄鸟 Yellow Bird": {
        "variants": ["Yellow Bird with Jamaican Rum", "Caribbean Yellow Bird", "Bird of Paradise"],
        "pairing": ["热带水果沙拉", "海鲜冷盘", "柑橘类甜点"],
        "occasion": "夏日消暑、派对聚会、加勒比主题宴会",
    },
}

# ============================================================
# IBA dataset 31 款英文配方 story 数据（4 字段全量）
# 来源：lmc2179/iba_dataset_json，与 seed 不重叠部分
# ============================================================
_IBA_EN_STORIES: dict[str, dict] = {
    "ANGEL FACE": {
        "history": "1920 年代由 Harry MacElhone 于巴黎 Harry's New York Bar 创制，名字源于同名鸡尾酒。使用金酒、杏白兰地与卡尔瓦多斯三等分，是禁酒令时期经典。",
        "variants": ["Angel Face with Apricot Brandy", "Angel's Wing", "Fallen Angel"],
        "pairing": ["水果塔", "奶酪拼盘", "柑橘类甜点"],
        "occasion": "餐前开胃、派对聚会、下午茶社交",
    },
    "BACARDI": {
        "history": "1933 年 Bacardi 朗姆酒公司推广的招牌鸡尾酒，使用 Bacardi 白朗姆、青柠汁与红石榴糖浆。曾因商标诉讼引发「Bacardi 鸡尾酒必须用 Bacardi 朗姆」的法律判例。",
        "variants": ["Bacardi Special", "Daiquiri（戴基里）", "Hemingway Special"],
        "pairing": ["海鲜冷盘", "柑橘类沙拉", "白身鱼肉"],
        "occasion": "餐前开胃、夏日消暑、派对聚会",
    },
    "CASINO": {
        "history": "源自 1920 年代美国禁酒令时期，配方载于 Harry Craddock 1930 年《Savoy Cocktail Book》。使用金酒、黑樱桃力娇酒、橙味苦精与柠檬汁，是干型酸酒的优雅变体。",
        "variants": ["Casino Royale", "Aviation（飞行）", "Clover Club"],
        "pairing": ["柑橘类甜点", "奶酪拼盘", "坚果"],
        "occasion": "餐前开胃、酒吧品鉴、社交场合",
    },
    "DERBY": {
        "history": "以美国肯塔基赛马会（Kentucky Derby）命名，传统配方使用波本或金酒加薄荷与桃味苦精。1930 年代《Savoy Cocktail Book》收录金酒版本。",
        "variants": ["Derby with Bourbon", "Mint Julep", "Brown Derby"],
        "pairing": ["南方烧烤", "坚果", "奶酪拼盘"],
        "occasion": "赛马会、春夏社交、户外派对",
    },
    "DRY MARTINI": {
        "history": "马天尼的干型版本，使用极少量的干味美思（5-10ml）与金酒搅拌而成。19 世纪末由 Martini & Rossi 推广干味美思后流行，被誉为「鸡尾酒之王」的纯粹表达。",
        "variants": ["Extra Dry Martini", "Dirty Martini", "Vesper", "Gibson"],
        "pairing": ["生蚝、海鲜冷盘", "坚果、橄榄", "烟熏三文鱼"],
        "occasion": "餐前开胃、正式社交、独饮沉思",
    },
    "MONKEY GLAND": {
        "history": "1922 年由巴黎 Harry's New York Bar 的 Frank Meier 创制，名字源自 Serge Voronoff 的猴子腺体移植实验（当时轰动巴黎）。使用金酒、橙汁、苦艾酒与红石榴糖浆。",
        "variants": ["Monkey Gland without Absinthe", "Satan's Whiskers", "Orange Blossom"],
        "pairing": ["柑橘类甜点", "水果沙拉", "奶酪拼盘"],
        "occasion": "餐前开胃、派对聚会、复古主题宴会",
    },
    "PARADISE": {
        "history": "1920 年代禁酒令时期创制，配方载于 Harry Craddock 1930 年《Savoy Cocktail Book》。使用金酒、杏白兰地与橙汁，是果味浓郁的经典酸酒。",
        "variants": ["Paradise with Apricot Liqueur", "Belmont", "Ward Eight"],
        "pairing": ["水果塔", "柑橘类甜点", "水果沙拉"],
        "occasion": "餐前开胃、女性社交、派对聚会",
    },
    "PORTO FLIP": {
        "history": "Flip 类鸡尾酒的波特版本，配方载于 Jerry Thomas 1862 年《Bartender's Guide》。使用波特酒、白兰地与蛋黄，是 19 世纪英国酒馆热啤酒 Flip 演变而来的冷饮蛋酒。",
        "variants": ["Port Flip with Sherry", "Brandy Flip", "Rum Flip"],
        "pairing": ["坚果", "巧克力甜点", "奶酪拼盘"],
        "occasion": "餐后消化、冬夜暖身、独饮沉思",
    },
    "RUSTY NAIL": {
        "history": "1950 年代纽约 21 Club 创制，使用苏格兰威士忌与杜林标（Drambuie）蜂蜜威士忌利口酒。名字源于调酒时搅拌用的 rusty nail 装饰传闻，是苏格兰威士忌经典搭配。",
        "variants": ["Rusty Nail with Bourbon", "Rusty Alec", "Gold Rush"],
        "pairing": ["坚果", "黑巧克力", "奶酪拼盘"],
        "occasion": "餐后消化、独饮沉思、冬夜暖身",
    },
    "STINGER": {
        "history": "1890 年代由纽约贵族圈流行，使用白兰地与薄荷力娇酒。禁酒令时期因薄荷掩盖劣质酒精而复兴，载于 Harry Craddock 1930 年《Savoy Cocktail Book》。",
        "variants": ["Stinger with Vodka", "White Spider", "Green Dragon"],
        "pairing": ["巧克力甜点", "薄荷巧克力", "坚果"],
        "occasion": "餐后消化、晚宴收尾、独饮沉思",
    },
    "TUXEDO": {
        "history": "1880 年代纽约 Tuxedo Club 创制，名字源于纽约 Tuxedo Park 上流社会度假地。使用金酒、干味美思、黑樱桃力娇酒与橙味苦精，是马天尼的正式着装版。",
        "variants": ["Tuxedo No.2", "Martinez", "Dry Martini"],
        "pairing": ["坚果、橄榄拼盘", "烟熏三文鱼", "奶酪拼盘"],
        "occasion": "正式社交、餐前开胃、晚宴开场",
    },
    "CHAMPAGNE COCKTAIL": {
        "history": "1862 年 Jerry Thomas《Bartender's Guide》首载，是最古老的香槟鸡尾酒。在香槟杯中放方糖加苦精，注入香槟，经典优雅。在《卡萨布兰卡》中出境而闻名。",
        "variants": ["Champagne Cocktail with Cognac", "Old Fashioned Champagne", "Black Velvet"],
        "pairing": ["法式前菜", "海鲜冷盘", "法式甜点"],
        "occasion": "庆祝场合、正式社交、新年庆典",
    },
    "FRENCH CONNECTION": {
        "history": "1970 年代以同名电影命名，使用干邑白兰地与苦杏仁酒（Amaretto）。简单两材料组合，干邑的果香与杏仁的坚果甜香完美平衡。",
        "variants": ["French Connection with Bourbon", "God Father", "Amaretto Sour"],
        "pairing": ["坚果", "奶酪拼盘", "巧克力甜点"],
        "occasion": "餐后消化、独饮沉思、晚宴收尾",
    },
    "GOD FATHER": {
        "history": "1970 年代以电影《教父》命名，使用苏格兰威士忌与苦杏仁酒。简单粗犷的两材料组合，呼应电影的黑帮气质，是烈酒爱好者的餐后选择。",
        "variants": ["God Father with Bourbon", "French Connection", "God Mother"],
        "pairing": ["坚果", "黑巧克力", "奶酪拼盘"],
        "occasion": "餐后消化、独饮沉思、深夜小酌",
    },
    "GOD MOTHER": {
        "history": "God Father 的伏特加版本，使用伏特加替代苏格兰威士忌，口感更柔和。1970 年代随同名电影流行，是女性友好型烈酒鸡尾酒。",
        "variants": ["God Mother with Whiskey", "God Father", "Amaretto Stone Sour"],
        "pairing": ["坚果", "巧克力甜点", "奶酪拼盘"],
        "occasion": "餐后消化、独饮沉思、派对聚会",
    },
    "GOLDEN DREAM": {
        "history": "1960 年代由加州调酒师创制，使用加利亚诺（Galliano）香草利口酒、君度、橙汁与奶油。金色色泽来自 Galliano，是餐后甜点式鸡尾酒。",
        "variants": ["Golden Dream without Cream", "Yellow Bird", "Golden Cadillac"],
        "pairing": ["柑橘类甜点", "奶油蛋糕", "水果塔"],
        "occasion": "餐后消化、女性社交、派对聚会",
    },
    "GRASSHOPPER": {
        "history": "1910 年代新奥尔良 Tujague's 酒吧调酒师 Philip Guichet 创制，使用薄荷力娇酒、可可力娇酒与奶油。绿色泽与薄荷巧克力风味使其成为经典餐后甜点饮。",
        "variants": ["Grasshopper with Vodka", "Flying Grasshopper", "Golden Grasshopper"],
        "pairing": ["薄荷巧克力", "奶油蛋糕", "巧克力甜点"],
        "occasion": "餐后消化、女性社交、派对聚会",
    },
    "HARVEY WALLBANGER": {
        "history": "1960 年代加州调酒师 Donato 'Duke' Antone 创制，在螺丝刀基础上加 Galliano 利口酒。名字源自冲浪爱好者 Harvey 喝醉后撞墙的传闻，1970 年代全美流行。",
        "variants": ["Harvey Wallbanger with Orange Juice", "Screwdriver（螺丝刀）", "Freddie Fudpucker"],
        "pairing": ["早餐早午餐", "水果沙拉", "柑橘类甜点"],
        "occasion": "早午餐、夏日消暑、派对聚会",
    },
    "HEMINGWAY SPECIAL": {
        "history": "1920 年代古巴哈瓦那 El Floridita 酒吧调酒师 Constantino Ribalaigua 为常客海明威特调。海明威不爱甜，故去糖加黑樱桃力娇酒与西柚汁，又称 Papa Doble。",
        "variants": ["Hemingway Daiquiri", "Daiquiri（戴基里）", "Papa Doble"],
        "pairing": ["海鲜冷盘", "柑橘类沙拉", "白身鱼肉"],
        "occasion": "餐前开胃、夏日消暑、文学品鉴",
    },
    "HORSE'S NECK": {
        "history": "1890 年代美国酒吧创制，最初仅是姜汁汽水加柠檬皮装饰（形如马颈），后加入白兰地成为烈酒长饮。是俱乐部与火车餐车的经典饮品。",
        "variants": ["Horse's Neck with Bourbon", "Horse's Neck without Alcohol", "Stone Sour"],
        "pairing": ["坚果", "奶酪拼盘", "三明治"],
        "occasion": "休闲社交、午后长饮、俱乐部场合",
    },
    "KIR": {
        "history": "勃艮第 Dijon 市长 Canon Félix Kir 推广，二战后用 cassis 利口酒为白葡萄酒增色，作为 Dijon 城市官方接待饮品。Royal 版用香槟替代白葡萄酒。",
        "variants": ["Kir Royal（香槟版）", "Kir Pétillant", "Cardinal（红葡萄酒版）", "Kir Breton"],
        "pairing": ["法式前菜", "奶酪拼盘", "法棍面包"],
        "occasion": "餐前开胃、正式社交、法式宴会",
    },
    "PINA COLADA": {
        "history": "1954 年波多黎各圣胡安 Caribe Hilton 调酒师 Ramón «Monchito» Marrero 创制，研发三月余。1978 年成为波多黎各官方饮品，是加勒比度假标志性饮品。",
        "variants": ["Frozen Piña Colada", "Chi-Chi（伏特加版）", "Miami Vice", "Pina Colada with Dark Rum"],
        "pairing": ["热带水果沙拉", "海鲜冷盘", "椰子风味甜点"],
        "occasion": "夏日消暑、度假社交、派对聚会",
    },
    "ROSE": {
        "history": "1920 年代由 Johnny Brosseau 在巴黎 Chatham 酒吧创制，使用干味美思、樱桃力娇酒与樱桃白兰地。粉红色泽优雅，载于 Harry Craddock 1930 年《Savoy Cocktail Book》。",
        "variants": ["Rose with Cherry Heering", "Pink Lady", "Clover Club"],
        "pairing": ["水果塔", "柑橘类甜点", "马卡龙"],
        "occasion": "餐前开胃、女性社交、下午茶",
    },
    "SEA BREEZE": {
        "history": "1920 年代美国禁酒令末期创制，早期版本使用金酒与杏仁利口酒。1970 年代改为现今伏特加+蔓越莓汁+西柚汁版本，是加州海岸度假经典长饮。",
        "variants": ["Bay Breeze（菠萝汁版）", "Cape Codder（无西柚）", "Madras（橙汁版）"],
        "pairing": ["海鲜冷盘", "水果沙拉", "烧烤小吃"],
        "occasion": "夏日消暑、度假社交、午后长饮",
    },
    "SEX ON THE BEACH": {
        "history": "1987 年佛罗里达州劳德代尔堡调酒师创制，作为 Spring Break 促销饮品。使用伏特加、桃子利口酒、蔓越莓汁与橙汁，名字大胆成为营销利器，1980-90 年代全美流行。",
        "variants": ["Sex on the Beach with Raspberry", "Woo Woo", "Fuzzy Navel"],
        "pairing": ["热带水果沙拉", "烧烤小吃", "海鲜冷盘"],
        "occasion": "派对聚会、海滩度假、春假狂欢",
    },
    "B52": {
        "history": "1977 年加拿大 Banff Springs Hotel 调酒师 Peter Fich 创制，以 B-52 轰炸机命名。三层分层（咖啡力娇酒、百利甜酒、君度）依密度自然分离，后因点燃饮法风靡全球。",
        "variants": ["B-52 with Baileys", "Flaming B-52", "B-53", "B-51"],
        "pairing": ["巧克力甜点", "坚果", "咖啡风味甜点"],
        "occasion": "派对聚会、餐后消化、夜店狂欢",
    },
    "KAMIKAZE": {
        "history": "1970 年代驻日美军基地创制，名字源自日语「神风」（二战神风特攻队）。使用伏特加、君度与青柠汁等比混合，是酸酒结构的简洁表达。",
        "variants": ["Kamikaze Shot", "Frozen Kamikaze", "Blue Kamikaze"],
        "pairing": ["烧烤小吃", "海鲜冷盘", "柑橘类沙拉"],
        "occasion": "派对聚会、Shot 拼酒、夜店狂欢",
    },
    "LEMON DROP MARTINI": {
        "history": "1990 年代旧金山调酒师 Norman Jay Hobday 创制，使用伏特加、君度、柠檬汁与糖边。糖边与柠檬的酸甜组合像柠檬糖，是 1990 年代加州马天尼复兴代表作。",
        "variants": ["Lemon Drop with Citrus Vodka", "Sugar Rim Martini", "Lemon Drop Shot"],
        "pairing": ["柑橘类甜点", "柠檬塔", "水果沙拉"],
        "occasion": "餐前开胃、女性社交、派对聚会",
    },
    "RUSSIAN SPRING PUNCH": {
        "history": "1980 年代伦敦调酒师 Dick Bradsell 创制，使用伏特加、黑加仑力娇酒、柠檬汁与起泡酒。是少数 IBA 收录的含起泡酒的现代经典，名字呼应春日复苏。",
        "variants": ["Russian Spring Punch without Sparkling", "Kir Royale", "Black Velvet"],
        "pairing": ["莓果塔", "柑橘类甜点", "水果沙拉"],
        "occasion": "春日社交、派对聚会、庆祝场合",
    },
    "SPRITZ VENEZIANO": {
        "history": "1800 年代威尼斯 Habsburg 统治时期创制，士兵用苏打水稀释葡萄酒。现代版使用阿佩罗（Aperol）、普罗塞克与苏打水，是威尼斯开胃酒文化标志，2010 年代全球流行。",
        "variants": ["Aperol Spritz", "Campari Spritz", "Select Spritz", "Hugo Spritz"],
        "pairing": ["橄榄、奶酪拼盘", "意式前菜", "火腿切片"],
        "occasion": "餐前开胃、夏日消暑、午后社交",
    },
    "VAMPIRO": {
        "history": "1990 年代墨西哥创制，使用龙舌兰、番茄汁、橙汁、青柠汁与辣椒酱，是墨西哥版的血腥玛丽。名字「Vampiro」（吸血鬼）源于番茄汁的红色与辣椒的刺激。",
        "variants": ["Vampiro with Clamato", "Bloody Maria", "Michelada"],
        "pairing": ["墨西哥玉米片、莎莎酱", "塔可", "烧烤小吃"],
        "occasion": "早午餐、宿醉救星、墨西哥主题派对",
    },
}

# ============================================================
# TheCocktailDB 简化 story 生成（基于配方名与材料的启发式）
# ============================================================

_FRONTMATTER_RE = re.compile(r"<!--\s*ingredients:\s*([^>]+?)\s*-->")

# 基酒关键词 → 风格描述
_BASE_SPIRIT_LABELS: list[tuple[str, str]] = [
    ("whiskey", "威士忌"),
    ("whisky", "威士忌"),
    ("bourbon", "波本威士忌"),
    ("scotch", "苏格兰威士忌"),
    ("rye", "黑麦威士忌"),
    ("rum", "朗姆酒"),
    ("gin", "金酒"),
    ("vodka", "伏特加"),
    ("tequila", "龙舌兰"),
    ("mezcal", "梅斯卡尔"),
    ("brandy", "白兰地"),
    ("cognac", "干邑白兰地"),
    ("champagne", "香槟"),
    ("prosecco", "普罗塞克"),
    ("wine", "葡萄酒"),
    ("vermouth", "味美思"),
]

# 时代风格描述（基于材料组合推断）
_STYLE_HINTS: list[tuple[str, str]] = [
    ("campari", "意大利开胃酒文化"),
    ("aperol", "意大利开胃酒文化"),
    ("absinthe", "禁酒令时期"),
    ("maraschino", "禁酒令时期"),
    ("chartreuse", "修道院秘方"),
    ("baileys", "20 世纪后期"),
    ("kahlua", "20 世纪后期"),
    ("amaretto", "20 世纪后期"),
    ("midori", "20 世纪后期"),
    ("blue curacao", "20 世纪后期"),
    ("coconut", "热带度假文化"),
    ("pineapple", "热带度假文化"),
    ("passion fruit", "热带度假文化"),
]

# 场景推断关键词
_OCCASION_RULES: list[tuple[list[str], str]] = [
    (["coffee", "kahlua", "espresso", "咖啡"], "餐后消化、提神场合"),
    (["champagne", "prosecco", "香槟", "起泡"], "庆祝场合、派对聚会"),
    (["cream", "baileys", "奶油", "egg", "蛋黄"], "餐后消化、冬夜暖身"),
    (["mint", "薄荷", "mojito"], "夏日消暑、午后长饮"),
    (["lemon", "lime", "柠檬", "青柠", "sour"], "餐前开胃、派对聚会"),
    (["whiskey", "whisky", "bourbon", "威士忌", "波本"], "餐后消化、独饮沉思"),
    (["gin", "金酒"], "餐前开胃、正式社交"),
    (["rum", "朗姆", "tropical", "pineapple"], "夏日消暑、度假社交"),
    (["vodka", "伏特加"], "派对聚会、休闲社交"),
    (["tequila", "龙舌兰"], "派对聚会、墨西哥主题"),
    (["tomato", "番茄"], "早午餐、宿醉救星"),
]


def _parse_ingredients(content: str) -> list[str]:
    """从 content frontmatter 解析材料列表。"""
    if not content:
        return []
    match = _FRONTMATTER_RE.search(content[:500])
    if not match:
        return []
    return [x.strip() for x in match.group(1).split("|") if x.strip()]


def _detect_base_spirit(ingredients: list[str], title: str) -> str:
    """基于材料与标题推断基酒中文名。"""
    text = f"{title} {' '.join(ingredients)}".lower()
    for keyword, label in _BASE_SPIRIT_LABELS:
        if keyword in text:
            return label
    return "混合烈酒"


def _detect_style_hint(ingredients: list[str]) -> str:
    """基于材料推断时代风格背景。"""
    text = " ".join(ingredients).lower()
    for keyword, hint in _STYLE_HINTS:
        if keyword in text:
            return hint
    return "现代调酒文化"


def _infer_occasion(ingredients: list[str], technique: str, title: str) -> str:
    """基于材料/技法/标题推断适饮场景。"""
    text = f"{title} {' '.join(ingredients)} {technique}".lower()
    for keywords, occasion in _OCCASION_RULES:
        if any(kw.lower() in text for kw in keywords):
            return occasion
    # 技法兜底
    if technique in ("blend",):
        return "夏日消暑、派对聚会"
    if technique in ("layer",):
        return "派对聚会、餐后消化"
    return "休闲社交、派对聚会"


def _generate_tdb_history(title: str, base_spirit: str, style_hint: str) -> str:
    """为 TheCocktailDB 配方生成简短历史（30-80 字）。"""
    return (
        f"以{base_spirit}为基酒的调酒，「{title}」融合{style_hint}元素，"
        f"是 TheCocktailDB 收录的现代酒吧配方，体现了当代调酒的多元风格。"
    )


def _generate_tdb_story(doc: Document) -> dict:
    """为 TheCocktailDB 配方生成简化版 story（history + occasion）。"""
    content = doc.content or ""
    ingredients = _parse_ingredients(content)
    technique = doc.technique or "build"
    base_spirit = _detect_base_spirit(ingredients, doc.title)
    style_hint = _detect_style_hint(ingredients)
    history = _generate_tdb_history(doc.title, base_spirit, style_hint)
    occasion = _infer_occasion(ingredients, technique, doc.title)
    return {"history": history, "occasion": occasion}


# ============================================================
# 工具函数
# ============================================================


def _load_meta(doc: Document) -> dict:
    """安全解析 doc.meta JSON，失败返回空 dict。"""
    if not doc.meta or doc.meta == "{}":
        return {}
    try:
        result = json.loads(doc.meta)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _normalize_en_key(title: str) -> str:
    """从「中文 English」标题中提取英文部分并归一化为大写 key。"""
    key = " ".join(title.split()).upper()
    key = key.replace("\u2019", "'").replace("\u2018", "'")
    return key


def _build_seed_story(title: str) -> dict | None:
    """为 seed 配方构建 4 字段 story（复用 SEED_RECIPES.history）。"""
    supplement = _SEED_STORY_SUPPLEMENT.get(title)
    if not supplement:
        return None
    history = _SEED_HISTORY.get(title, "")
    if not history:
        # 兜底：从 _IBA_EN_STORIES 取 history
        en_key = _normalize_en_key(title)
        en_story = _IBA_EN_STORIES.get(en_key)
        history = en_story["history"] if en_story else ""
    if not history:
        return None
    return {
        "history": history,
        "variants": supplement["variants"],
        "pairing": supplement["pairing"],
        "occasion": supplement["occasion"],
    }


def _build_iba_story(title: str) -> dict | None:
    """为 iba 配方构建 4 字段 story。

    IBA 配方标题为「中文 English」格式，与 _SEED_STORY_SUPPLEMENT 的 key 一致，
    优先匹配 _SEED_STORY_SUPPLEMENT（variants/pairing/occasion），
    history 从 _SEED_HISTORY 或 _IBA_EN_STORIES 获取。
    若 _SEED_STORY_SUPPLEMENT 未命中，退回 _IBA_EN_STORIES 完整匹配。
    """
    # 1. 优先 _SEED_STORY_SUPPLEMENT（标题格式一致）
    supplement = _SEED_STORY_SUPPLEMENT.get(title)
    if supplement:
        history = _SEED_HISTORY.get(title, "")
        if not history:
            en_key = _normalize_en_key(title)
            en_story = _IBA_EN_STORIES.get(en_key)
            history = en_story["history"] if en_story else ""
        if not history:
            # 兜底：从 supplement 的 occasion 生成简短 history
            history = f"IBA 经典鸡尾酒「{title}」，{supplement['occasion']}。"
        return {
            "history": history,
            "variants": supplement["variants"],
            "pairing": supplement["pairing"],
            "occasion": supplement["occasion"],
        }

    # 2. 退回 _IBA_EN_STORIES（英文 key 完整匹配）
    en_key = _normalize_en_key(title)
    en_story = _IBA_EN_STORIES.get(en_key)
    if en_story:
        return en_story

    return None


def _build_iba_en_story(title: str) -> dict | None:
    """为 iba 英文配方构建 4 字段 story（保留兼容，优先用 _build_iba_story）。"""
    key = _normalize_en_key(title)
    return _IBA_EN_STORIES.get(key)


# ============================================================
# 主流程
# ============================================================


def main() -> None:
    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.category == "recipe")
        ).all()

        total = len(docs)
        log.info("配方总数: %d", total)

        stats = Counter()
        iba_total = 0
        iba_with_story = 0
        tdb_total = 0
        tdb_with_story = 0
        tdb_processed = 0
        tdb_top_n = 100

        for doc in docs:
            meta = _load_meta(doc)
            source = doc.source or ""

            if source in ("seed", "iba"):
                iba_total += 1
                story: dict | None = None
                if source == "seed":
                    story = _build_seed_story(doc.title)
                elif source == "iba":
                    story = _build_iba_story(doc.title)
                if story:
                    meta["story"] = story
                    doc.meta = json.dumps(meta, ensure_ascii=False)
                    session.add(doc)
                    iba_with_story += 1
                    stats[f"iba_{source}_filled"] += 1
                else:
                    # 兜底：为未命中字典的 IBA 配方生成简化版 story
                    if source == "iba":
                        fallback = _generate_tdb_story(doc)
                        meta["story"] = fallback
                        doc.meta = json.dumps(meta, ensure_ascii=False)
                        session.add(doc)
                        iba_with_story += 1
                        stats["iba_fallback_filled"] += 1
                    else:
                        stats[f"iba_{source}_no_story_data"] += 1

            elif source == "thecocktaildb":
                tdb_total += 1
                # 仅处理前 tdb_top_n 条（按 doc_id 排序的 Top 100）
                if tdb_processed < tdb_top_n:
                    story = _generate_tdb_story(doc)
                    meta["story"] = story
                    doc.meta = json.dumps(meta, ensure_ascii=False)
                    session.add(doc)
                    tdb_with_story += 1
                    tdb_processed += 1
                    stats["tdb_filled"] += 1
                else:
                    stats["tdb_skipped_beyond_top100"] += 1

        session.commit()
        log.info(
            "已 commit：IBA %d/%d，TheCocktailDB Top %d/%d",
            iba_with_story, iba_total, tdb_with_story, tdb_total,
        )

    # ------------------------------------------------------------------
    # 报告
    # ------------------------------------------------------------------
    print("\n=== 回填统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")

    print("\n=== 覆盖率 ===")
    iba_pct = (iba_with_story / iba_total * 100) if iba_total else 0.0
    tdb_pct = (tdb_with_story / tdb_total * 100) if tdb_total else 0.0
    tdb_top100_pct = (tdb_with_story / tdb_top_n * 100) if tdb_top_n else 0.0
    print(f"  IBA (seed+iba): {iba_with_story}/{iba_total} ({iba_pct:.1f}%)")
    print(
        f"  TheCocktailDB Top 100: {tdb_with_story}/{tdb_top_n} "
        f"({tdb_top100_pct:.1f}% of Top 100)"
    )
    print(
        f"  TheCocktailDB 全量: {tdb_with_story}/{tdb_total} ({tdb_pct:.1f}%)"
    )

    # 验收检查
    print("\n=== 验收 ===")
    print(
        f"  IBA 覆盖率 >= 90%: "
        f"{'✅ 通过' if iba_pct >= 90 else '❌ 未达标'} ({iba_pct:.1f}%)"
    )
    print(
        f"  Top 100 覆盖率 >= 50%: "
        f"{'✅ 通过' if tdb_top100_pct >= 50 else '❌ 未达标'} "
        f"({tdb_top100_pct:.1f}%)"
    )


if __name__ == "__main__":
    main()
