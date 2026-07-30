#!/usr/bin/env python3
"""IMA 文档内容富化脚本。

问题：IMA 同步的文档内容仅含标题 + 元数据，无实质可检索文本，
导致 RAG 检索（尤其 hash embedding）几乎无法命中。

方案：按标题模式分类（葡萄品种 / 产区 / 葡萄酒类型 / 果酒 / 其他），
生成与标题相关的描述性中文内容，保留原始 metadata 头部，附加富化描述。

幂等：检测 content 是否已含「<!-- enriched -->」标记，已富化则跳过。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document

_ENRICHED_MARKER = "<!-- enriched -->"

# 葡萄品种知识库（精选 34 个 IMA 葡萄品种）
_GRAPE_PROFILES: dict[str, str] = {
    "赤霞珠葡萄": "赤霞珠（Cabernet Sauvignon）是全球种植最广的红葡萄品种，原产法国波尔多。果皮厚，单宁强劲，带有黑加仑、雪松、青椒香气，常用于酿造可陈年的干红葡萄酒。",
    "黑皮诺葡萄": "黑皮诺（Pinot Noir）原产法国勃艮第，是娇贵的红葡萄品种。果皮薄，单宁柔和，带樱桃、覆盆子、土壤香气，对气候敏感，优质产区有勃艮第、俄勒冈、新西兰。",
    "雷司令葡萄": "雷司令（Riesling）是德国代表性白葡萄品种，芳香型，带青苹果、柑橘、花香和矿物感。酸度明亮，可酿造从干型到甜型的多种风格，优质产区有摩泽尔、莱茵高、阿尔萨斯。",
    "霞多丽葡萄": "霞多丽（Chardonnay）是全球种植最广的白葡萄品种之一，原产法国勃艮第。风格多变，可酿造清爽的夏布利或丰腴的过桶霞多丽，带青苹果、柑橘、黄油、香草香气。",
    "长相思葡萄": "长相思（Sauvignon Blanc）是芳香型白葡萄品种，原产法国波尔多。带青草、百香果、醋栗香气，酸度高，新西兰马尔堡和法国桑塞尔是经典产区。",
    "梅洛葡萄": "梅洛（Merlot）原产法国波尔多，是波尔多右岸的主力品种。果皮中等，单宁柔和，带李子、黑莓、巧克力香气，口感圆润饱满，常与赤霞珠混酿。",
    "西拉葡萄": "西拉（Syrah/Shiraz）原产法国罗讷河谷，澳大利亚称 Shiraz。果皮厚，单宁强，带黑莓、黑胡椒、烟熏香气，北罗讷的赫米塔希和澳大利亚巴罗萨是经典产区。",
    "莫斯卡托葡萄": "莫斯卡托（Moscato）是麝香葡萄家族，芳香型，带玫瑰、水蜜桃、柑橘香气。常用于酿造甜型起泡酒 Moscato d'Asti，意大利皮埃蒙特产区著名。",
    "丹魄葡萄": "丹魄（Tempranillo）是西班牙代表性红葡萄品种，里奥哈产区主力。果皮中等，单宁柔和，带草莓、皮革、香草香气，常经橡木桶陈年。",
    "佳美娜葡萄": "佳美娜（Carménère）原产法国波尔多，现以智利为最大产区。带黑莓、青椒、香料香气，单宁柔和，智利中央山谷是经典产区。",
    "佳美葡萄": "佳美（Gamay）原产法国博若莱。果皮薄，单宁低，带草莓、覆盆子、香蕉香气，博若莱新酒以二氧化碳浸渍法酿造，果香鲜明。",
    "内比奥罗葡萄": "内比奥罗（Nebbiolo）是意大利皮埃蒙特代表性红葡萄品种。单宁强，酸度高，带玫瑰、焦油、樱桃香气，巴罗洛和巴巴莱斯科是经典产区。",
    "塔娜葡萄": "塔娜（Tannat）原产法国西南部，现以乌拉圭为最大产区。单宁极强，带黑莓、香料、烟草香气，适合陈年。",
    "多姿桃葡萄": "多姿桃（Dolcetto）原产意大利皮埃蒙特。单宁柔和，酸度低，带黑樱桃、杏仁、甘草香气，适合早饮。",
    "小维多葡萄": "小维多（Petit Verdot）原产法国波尔多，常作混酿调味品种。单宁强，色深，带紫罗兰、香料、黑莓香气。",
    "巴贝拉葡萄": "巴贝拉（Barbera）原产意大利皮埃蒙特。酸度高，单宁低，带樱桃、李子、香料香气，巴贝拉 d'Alba 是经典产区。",
    "慕合怀特葡萄": "慕合怀特（Mourvèdre/Monastrell）原产西班牙，法国南罗讷和邦多勒常用。单宁强，带黑莓、肉类、香料香气。",
    "桑娇维塞葡萄": "桑娇维塞（Sangiovese）是意大利托斯卡纳代表性红葡萄品种。酸度高，单宁强，带樱桃、土壤、香料香气，基安蒂和布鲁内罗是经典产区。",
    "歌海娜葡萄": "歌海娜（Grenache/Garnacha）原产西班牙，法国南罗讷主力。糖分高，酒精度高，带草莓、香料、白胡椒香气。",
    "灰皮诺葡萄": "灰皮诺（Pinot Grigio/Pinot Gris）原产法国，意大利东北部广泛种植。带梨、柑橘、蜂蜜香气，意大利风格清爽，阿尔萨斯风格丰腴。",
    "特浓情葡萄": "特浓情（Torrontés）是阿根廷代表性白葡萄品种。芳香型，带玫瑰、茉莉、柑橘香气，适合早饮。",
    "琼瑶浆葡萄": "琼瑶浆（Gewürztraminer）原产阿尔萨斯。芳香型，带荔枝、玫瑰、香料香气，酒精度高，酸度低。",
    "白诗南葡萄": "白诗南（Chenin Blanc）原产法国卢瓦尔河谷。酸度高，风格多变，从干型到甜型均有，带苹果、蜂蜜、杏仁香气。",
    "维欧尼葡萄": "维欧尼（Viognier）原产法国北罗讷 Condrieu。芳香型，带杏、桃、花香，酒精度高，酸度低。",
    "维蒙蒂诺葡萄": "维蒙蒂诺（Vermentino）原产意大利撒丁岛和利古里亚。带柑橘、青苹果、杏仁香气，酸度清爽。",
    "绿维特利纳葡萄": "绿维特利纳（Grüner Veltliner）是奥地利代表性白葡萄品种。带白胡椒、柑橘、矿物感，酸度明亮。",
    "蛇龙珠葡萄": "蛇龙珠（Cabernet Gernischt）是中国山东烟台产区主力红葡萄品种，带黑莓、青椒、香料香气，张裕等酒庄常用。",
    "赛美蓉葡萄": "赛美蓉（Sémillon）原产法国波尔多，常与长相思混酿。带无花果、蜂蜜、蜡质香气，苏玳贵腐甜酒主力品种。",
    "金粉黛葡萄": "金粉黛（Zinfandel）是美国加州特色红葡萄品种。带黑莓、覆盆子、香料香气，酒精度高，口感丰腴。",
    "阿尔巴利诺葡萄": "阿尔巴利诺（Albariño）原产西班牙加利西亚 Rías Baixas 产区。带柑橘、桃、矿物感，酸度高，适合配海鲜。",
    "马尔贝克葡萄": "马尔贝克（Malbec）原产法国卡奥尔，现以阿根廷门多萨为最大产区。色深，单宁中等，带黑莓、紫罗兰、可可香气。",
    "马瑟兰葡萄": "马瑟兰（Marselan）是法国培育的赤霞珠 × 歌海娜杂交品种，中国宁夏产区广泛种植。带黑莓、香料、薄荷香气。",
    "佳丽酿葡萄": "佳丽酿（Carignan/Cariñena/Mazuelo）原产西班牙阿拉贡，法国朗格多克也曾广泛种植。单宁强，酸度高，带黑莓、香料、甘草香气。老藤佳丽酿品质优异，普里奥拉托常与歌海娜混酿。",
}

# 产区知识库（精选 26 个 IMA 产区）
_REGION_PROFILES: dict[str, str] = {
    "波尔多产区": "波尔多（Bordeaux）是法国最著名的葡萄酒产区，位于西南部。以赤霞珠、梅洛、品丽珠混酿的红葡萄酒和赛美蓉、长相思混酿的白葡萄酒闻名。左岸以赤霞珠为主（梅多克、波亚克），右岸以梅洛为主（圣埃美隆、波美侯），苏玳产贵腐甜酒。1855 年分级体系确立五大一级庄。",
    "勃艮第产区": "勃艮第（Burgundy/Bourgogne）是法国东部产区，以单一品种葡萄酒闻名。红葡萄用黑皮诺，白葡萄用霞多丽。核心产区包括夜丘、博讷丘、夏布利。风土分级严格：大区、村庄级、一级园、特级园。罗曼尼·康帝、拉塔什等特级园是世界最贵的葡萄酒之一。",
    "香槟产区": "香槟（Champagne）是法国最北的葡萄酒产区，位于巴黎以东。仅允许霞多丽、黑皮诺、莫尼耶三品种酿造起泡酒。传统法二次发酵，带酵母陈年至少 15 个月。著名酒庄有酩悦、库克、波林格、水晶香槟。",
    "里奥哈产区": "里奥哈（Rioja）是西班牙最著名的葡萄酒产区，以丹魄葡萄酿造的红葡萄酒闻名。按陈年时长分级：佳酿、陈酿、特级陈酿、 gran reserva。美国橡木桶陈年赋予香草、椰子气息。",
    "托斯卡纳产区": "托斯卡纳（Tuscany）是意大利中部产区，以桑娇维塞葡萄酿造的基安蒂、布鲁内罗 di 蒙塔尔奇诺闻名。超级托斯卡纳（如西施佳雅、天娜）使用赤霞珠等国际品种，突破 DOC 法规。",
    "纳帕产区": "纳帕谷（Napa Valley）是美国加州最著名的葡萄酒产区，以赤霞珠、霞多丽闻名。1976 年巴黎审判让纳帕酒一举成名。作品一号、鹰啸、钻石溪谷是顶级酒庄。",
    "中央海岸产区": "中央海岸（Central Coast）是美国加州产区，涵盖蒙特雷、圣路易斯奥比斯波、圣巴巴拉。以黑皮诺、霞多丽、西拉闻名，气候凉爽适合芳香品种。",
    "华盛顿产区": "华盛顿州（Washington）是美国第二大葡萄酒产区，以赤霞珠、梅洛、西拉闻名。哥伦比亚谷是核心产区，气候干燥需灌溉，昼夜温差大。",
    "卢瓦尔河谷产区": "卢瓦尔河谷（Loire Valley）是法国最长葡萄酒产区，从大西洋延伸至中央高原。白诗南、长相思、密斯卡黛是主要白品种，品丽珠是红品种主力。桑塞尔、武弗雷、希农是子产区。",
    "威尼托产区": "威尼托（Veneto）是意大利东北部产区，以阿玛罗尼、普罗塞克、索阿维闻名。科维纳、卡尔卡耐、格雷拉是主要品种。瓦波利切拉和阿斯蒂是核心子产区。",
    "宁夏产区": "宁夏是中国最重要的葡萄酒产区，位于贺兰山东麓。以赤霞珠、马瑟兰、霞多丽闻名。气候干燥，昼夜温差大，需埋藤越冬。贺兰晴雪、迦南美地、银色高地是知名酒庄。",
    "巴罗萨产区": "巴罗萨（Barossa Valley）是澳大利亚最著名的葡萄酒产区，以西拉（Shiraz）闻名。设拉子酒体饱满，带黑莓、巧克力、香料香气。奔富 Grange、Henschke Hill of Grace 是顶级酒款。",
    "托卡伊产区": "托卡伊（Tokaj）是匈牙利著名甜酒产区，以贵腐甜酒 Aszú 闻名。富尔民特、Hárslevelű 是主要品种。按篓数分级（3-6 Puttonyos），6 篓最甜。",
    "摩泽尔产区": "摩泽尔（Mosel）是德国最著名的雷司令产区，位于摩泽尔河沿岸。板岩土壤，坡度陡峭，气候凉爽。雷司令酒体轻盈，酸度明亮，带青苹果、矿物感。Wehlener Sonnenuhr、Bernkasteler Doctor 是顶级园。",
    "斯泰伦博斯产区": "斯泰伦博斯（Stellenbosch）是南非最著名的葡萄酒产区，以赤霞珠、皮诺塔吉闻名。皮诺塔吉是南非特色品种，黑皮诺 × 神索杂交。气候温和，受海洋影响。",
    "普里奥拉托产区": "普里奥拉托（Priorat）是西班牙两大 DOCa 之一，位于加泰罗尼亚。老藤歌海娜、佳丽酿种植在板岩土壤，产量低，酒体浓郁。",
    "杜罗产区": "杜罗（Douro）是葡萄牙波特酒产区，也是干红葡萄酒产区。国产弗兰卡、Touriga Nacional 是主要品种。波特酒加强酒分ruby、tawny、vintage 等风格。",
    "猎人谷产区": "猎人谷（Hunter Valley）是澳大利亚新南威尔士州产区，以赛美蓉闻名。无橡木桶赛美蓉陈年后带蜡质、蜂蜜香气，是该产区特色。西拉也产出独特胡椒风格。",
    "皮埃蒙特产区": "皮埃蒙特（Piedmont）是意大利西北部产区，以内比奥罗酿造的巴罗洛、巴巴莱斯科闻名。巴贝拉、多姿桃也是当地特色。白松露产区，美食美酒文化深厚。",
    "索诺玛产区": "索诺玛（Sonoma）是美国加州产区，毗邻纳帕。气候更凉爽，适合黑皮诺、霞多丽。俄罗斯河谷、干溪谷、索诺玛海岸是子产区。",
    "罗讷河谷产区": "罗讷河谷（Rhône Valley）是法国东南部产区。北罗讷以西拉为主（赫米塔希、罗第丘），南罗讷以歌海娜为主（教皇新堡）。Châteauneuf-du-Pape 允许 13 个品种混酿。",
    "西西里产区": "西西里（Sicily）是意大利南部岛屿产区，以黑珍珠（Nero d'Avola）红葡萄酒和格里洛白葡萄酒闻名。埃特纳火山产区以高海拔火山土壤葡萄酒著名。",
    "门多萨产区": "门多萨（Mendoza）是阿根廷最重要的葡萄酒产区，以马尔贝克闻名。安第斯山雪水灌溉，高海拔种植，昼夜温差大，色泽深邃。",
    "阿尔萨斯产区": "阿尔萨斯（Alsace）是法国东北部产区，毗邻德国。以芳香型白葡萄酒闻名：雷司令、灰皮诺、琼瑶浆、密斯卡黛。主要酿造单一品种干白，Grand Cru 分级。",
    "阿连特茹产区": "阿连特茹（Alentejo）是葡萄牙南部产区，以红葡萄混酿闻名。国产弗兰卡、Aragonez 是主要品种。酒体饱满，性价比高。",
    "马尔堡产区": "马尔堡（Marlborough）是新西兰最重要的葡萄酒产区，位于南岛北端。以长相思白葡萄酒闻名，带强烈的百香果、青草香气，云湾、Oyster Bay 是代表酒庄。",
}

# 葡萄酒类型
_WINE_TYPE_PROFILES: dict[str, str] = {
    "红葡萄酒": "红葡萄酒（Red Wine）是用红葡萄品种带皮发酵酿造的葡萄酒。果皮中的花青素赋予红色，单宁带来涩感。常见品种有赤霞珠、梅洛、黑皮诺、西拉。适饮温度 16-18°C，适合搭配红肉、奶酪。",
    "白葡萄酒": "白葡萄酒（White Wine）是用白葡萄品种或红葡萄去皮发酵酿造的葡萄酒。无单宁或单宁极低，酸度明显。常见品种有霞多丽、长相思、雷司令。适饮温度 8-12°C，适合搭配海鲜、白肉。",
    "桃红葡萄酒": "桃红葡萄酒（Rosé）是带短暂皮浸的红葡萄酿造，颜色介于红白之间。普罗旺斯、塔维勒是经典产区。带草莓、西瓜、柑橘香气，适饮温度 8-10°C，夏季流行。",
    "橙葡萄酒": "橙葡萄酒（Orange Wine）是白葡萄带皮浸渍发酵而成，颜色偏橙。单宁较白葡萄酒强，风格自然。格鲁吉亚、斯洛文尼亚是传统产区，带杏、坚果、氧化香气。",
    "起泡葡萄酒混酿": "起泡葡萄酒（Sparkling Wine）含二氧化碳气泡。传统法（香槟法）、查马法（普罗塞克）、转移法等多种工艺。香槟、卡瓦、普罗塞克、塞克特是著名类型。",
    "甜型葡萄酒": "甜型葡萄酒（Sweet Wine）含残留糖分，可通过延迟采收、贵腐、冰酒、风干、加强等方式酿造。苏玳贵腐、托卡伊 Aszú、德国冰酒、波特酒是经典类型。",
    "葡萄酒酿造工艺": "葡萄酒酿造工艺包括采摘、破皮、压榨、发酵、陈年、装瓶等步骤。红葡萄酒带皮发酵提取色素单宁，白葡萄去皮发酵。橡木桶陈年赋予香草、椰子气息。苹果酸-乳酸发酵降低酸度。",
    "葡萄酒评论与资讯": "葡萄酒评论与资讯涵盖酒评家评分、葡萄酒杂志、葡萄酒比赛、市场行情等。Robert Parker、Jancis Robinson 是权威酒评家。Wine Spectator、Decanter 是主流杂志。",
    "Wine Folly 葡萄酒学习指南": "Wine Folly 是著名葡萄酒教育平台，以图表化、视觉化方式讲解葡萄酒知识。涵盖葡萄品种、产区、品鉴、配餐等内容，是葡萄酒入门的经典学习资源。",
}

# 果酒
_FRUIT_WINE_PROFILES: dict[str, str] = {
    "山楂果酒": "山楂果酒是以山楂为原料发酵或浸泡而成的果酒，呈深红色，酸甜适口，带山楂特有的果香。山楂富含有机酸、维生素C，有一定助消化作用。",
    "李子果酒": "李子果酒以李子为原料发酵酿造，呈宝石红色，带李子、樱桃香气，酸甜平衡。欧美常用欧洲李，亚洲常用日本李。",
    "杨梅果酒": "杨梅果酒以杨梅为原料，是中国特色果酒。呈深红色，带杨梅特有的酸甜果香，江浙闽为主要产区。杨梅季节短，果酒可延长赏味期。",
    "桃子果酒": "桃子果酒以桃子为原料发酵，呈淡黄色或粉红色，带水蜜桃、花蜜香气，口感甜美。可单酿或与其他水果混酿。",
    "桑葚果酒": "桑葚果酒以桑葚为原料，呈深紫黑色，富含花青素。带桑葚特有的甜香，酸甜平衡，有一定抗氧化功效。",
    "梨子果酒": "梨子果酒以梨子为原料发酵，呈淡黄色，带梨、蜂蜜香气，口感清爽。常见品种有巴梨、亚洲梨。",
    "樱桃果酒": "樱桃果酒以樱桃为原料，呈红宝石色，带樱桃、杏仁香气，酸甜适口。北欧常见，可作餐后酒。",
    "荔枝果酒": "荔枝果酒以荔枝为原料，是中国南方特色果酒。带荔枝特有的甜香、花香，口感清新。广东、福建为主要产区。",
    "莓果果酒": "莓果果酒以草莓、蓝莓、覆盆子等莓果为原料发酵，呈红色或紫红色，带浓郁莓果香气，富含花青素和维生素 C。",
    "金桔果酒": "金桔果酒以金桔为原料，呈淡黄色，带柑橘类清香，酸甜微苦。金桔富含维生素 C 和挥发油，有润喉作用。",
}

# 其他
_OTHER_PROFILES: dict[str, str] = {
    "桂花酒": "桂花酒是以桂花为原料浸泡或发酵而成的花酒，呈淡黄色，带桂花特有的甜香。中国传统酒品，常在秋季酿造，象征团圆。",
    "苹果 cider": "苹果酒（Cider/Hard Cider）是以苹果汁发酵而成的果酒，酒精度 4-8%。英国、法国诺曼底、西班牙阿斯图里亚斯是传统产区。风格从干型到甜型，从静酒到起泡酒均有。",
    "蜂蜜酒": "蜂蜜酒（Mead）是以蜂蜜为原料发酵酿造的古老酒种，酒精度 8-20%。可加香料、水果、啤酒花调味。中欧、东欧有悠久传统，波兰、立陶宛是代表产区。",
}


def _enrich_content(title: str, original_content: str) -> str | None:
    """根据标题匹配知识库，返回富化后的内容；无匹配返回 None。"""
    profile = None
    if title in _GRAPE_PROFILES:
        profile = _GRAPE_PROFILES[title]
        category_label = "葡萄品种"
    elif title in _REGION_PROFILES:
        profile = _REGION_PROFILES[title]
        category_label = "葡萄酒产区"
    elif title in _WINE_TYPE_PROFILES:
        profile = _WINE_TYPE_PROFILES[title]
        category_label = "葡萄酒类型"
    elif title in _FRUIT_WINE_PROFILES:
        profile = _FRUIT_WINE_PROFILES[title]
        category_label = "果酒"
    elif title in _OTHER_PROFILES:
        profile = _OTHER_PROFILES[title]
        category_label = "特色酒"
    else:
        # 通用富化：基于标题关键词构造可检索文本
        return _generic_enrich(title, original_content)

    # 保留原始 metadata 头部，附加富化描述
    # 提取原始 # 标题行和来源类型行
    lines = original_content.split("\n")
    header_lines: list[str] = []
    for line in lines:
        if line.startswith(("> 来源类型", "# ")):
            header_lines.append(line)

    parts = [f"# {title}\n"]
    parts.append(profile)
    parts.append("")
    if header_lines:
        for h in header_lines:
            if h.startswith(">"):
                parts.append(h)
    parts.append(f"\n类别：{category_label}")
    parts.append(_ENRICHED_MARKER)
    return "\n".join(parts)


# 酒类关键词描述（用于通用富化时附加相关上下文）
_ALCOHOL_KEYWORDS: dict[str, str] = {
    "朗姆酒": "朗姆酒（Rum）是以甘蔗糖蜜或甘蔗汁为原料发酵蒸馏而成的烈酒，主要产自加勒比海地区，风格分白朗姆、金朗姆、黑朗姆。",
    "金酒": "金酒（Gin）是以谷物为基酒，用杜松子等植物香料调味的烈酒，带杜松、柑橘、草本香气，是马天尼、金汤力等经典鸡尾酒的基酒。",
    "伏特加": "伏特加（Vodka）是以谷物或马铃薯为原料发酵蒸馏的高纯度烈酒，酒精度通常 40%，口感纯净，是血腥玛丽、莫斯科骡子等鸡尾酒的基酒。",
    "龙舌兰": "龙舌兰（Tequila）是墨西哥特色烈酒，以蓝色龙舌兰为原料，分 Blanco、Reposado、Añejo 等风格，是玛格丽特的基酒。",
    "威士忌": "威士忌（Whisky/Whiskey）是以谷物为原料发酵蒸馏并经橡木桶陈年的烈酒，分苏格兰、爱尔兰、美国波本、日本等风格。",
    "白兰地": "白兰地（Brandy）是以葡萄酒或其他水果酒为基酒蒸馏而成，干邑（Cognac）和雅文邑（Armagnac）是法国两大知名产区。",
    "白酒": "白酒是中国传统蒸馏酒，以谷物为原料固态发酵，按香型分浓香、酱香、清香、米香等，茅台、五粮液、汾酒是代表品牌。",
    "啤酒": "啤酒（Beer）是以麦芽、啤酒花、酵母和水为原料酿造的低酒精度饮料，分艾尔（Ale）和拉格（Lager）两大类。",
    "葡萄酒": "葡萄酒（Wine）是以葡萄为原料发酵酿造的酒，按颜色分红、白、桃红，按含糖量分干、半干、半甜、甜型。",
    "清酒": "清酒（Sake）是日本传统米酒，以米、米麹、水为原料发酵，按精米步合分纯米酒、本酿造、吟酿、大吟酿等等级。",
    "梅酒": "梅酒（Umeshu）是以青梅浸泡在蒸馏酒中加糖制成的果酒，日本传统酒品，酸甜适口。",
    "米酒": "米酒是以糯米为原料发酵而成的低酒精度饮料，中国传统酒品，各地有不同风味。",
    "黄酒": "黄酒是中国传统发酵酒，以稻米为原料，绍兴酒是代表，按含糖量分元红、加饭、善酿、香雪。",
    "鸡尾酒": "鸡尾酒（Cocktail）是以烈酒为基酒，辅以利口酒、果汁、糖浆等调制而成的混合饮料，IBA 分类含不朽经典、当代经典、新时代饮品。",
    "利口酒": "利口酒（Liqueur）是以烈酒为基酒，加入水果、草本、香料等调味并加糖的甜味烈酒，君度、卡帕诺、金巴利是常见品牌。",
    "香槟": "香槟（Champagne）是法国香槟产区用传统法酿造的起泡酒，仅允许霞多丽、黑皮诺、莫尼耶三品种，二次发酵产生气泡。",
    "味美思": "味美思（Vermouth）是以葡萄酒为基酒，加入草本植物浸泡的加强酒，分干味美思和甜味美思，是马天尼、曼哈顿的辅料。",
    "梅斯卡尔": "梅斯卡尔（Mezcal）是墨西哥烈酒，以龙舌兰为原料，带烟熏风味，与龙舌兰 Tequila 不同。",
}


def _generic_enrich(title: str, original_content: str) -> str:
    """通用富化：清理标题 + 检测酒类关键词 + 构造可检索文本。

    对于不在专项知识库中的文档（如酒博士知识体系、行业报告、方法论等），
    从标题中提取酒类关键词并附加相关描述，提升 RAG 检索召回率。
    """
    # 清理标题：去除 · 分隔符的多段标题，提取核心部分
    import re as _re

    clean_title = title
    # "酒博士·酒博士MAS·知识·XXX·通用端" → "XXX"
    if "·" in clean_title:
        parts = [p.strip() for p in clean_title.split("·") if p.strip()]
        # 取倒数第二段（通常是核心标题）
        if len(parts) >= 2:
            clean_title = parts[-2] if "通用端" in parts[-1] else parts[-1]

    # 去除版本号、日期后缀
    clean_title = _re.sub(r"\s*v\d+\.\d+", "", clean_title, flags=_re.IGNORECASE)
    clean_title = _re.sub(r"_\d{4}", "", clean_title)
    clean_title = _re.sub(r"_\d{4}-\d{4}", "", clean_title)
    clean_title = clean_title.strip()

    # 检测酒类关键词
    alcohol_descs: list[str] = []
    for keyword, desc in _ALCOHOL_KEYWORDS.items():
        if keyword in title:
            alcohol_descs.append(desc)

    # 提取原始 metadata
    lines = original_content.split("\n")
    header_lines: list[str] = []
    for line in lines:
        if line.startswith("> 来源类型"):
            header_lines.append(line)

    parts = [f"# {title}\n"]
    parts.append(f"本文档标题为「{title}」。")

    if alcohol_descs:
        parts.append("\n相关酒类知识：")
        for desc in alcohol_descs:
            parts.append(f"- {desc}")
        category_label = "酒类知识"
    else:
        # 无酒类关键词匹配，使用标题本身作为可检索文本
        parts.append(f"本文档涉及主题：{clean_title}。")
        category_label = "行业资料"

    parts.append("")
    for h in header_lines:
        parts.append(h)
    parts.append(f"\n类别：{category_label}")
    parts.append(_ENRICHED_MARKER)
    return "\n".join(parts)


def main() -> int:
    enriched = 0
    skipped = 0
    no_match = 0
    no_match_titles: list[str] = []

    with get_session() as s:
        docs = s.exec(select(Document).where(Document.source == "ima")).all()
        print(f"扫描 {len(docs)} 篇 IMA 文档...")
        for doc in docs:
            if _ENRICHED_MARKER in (doc.content or ""):
                skipped += 1
                continue
            new_content = _enrich_content(doc.title or "", doc.content or "")
            if new_content is None:
                no_match += 1
                no_match_titles.append(doc.title or "")
                continue
            doc.content = new_content
            s.add(doc)
            enriched += 1
        s.commit()

    print(f"富化完成：{enriched} 篇已更新，{skipped} 篇已富化跳过，{no_match} 篇无匹配")
    if no_match_titles:
        print("\n未匹配标题（需手动补充知识库）：")
        for t in no_match_titles:
            print(f"  - {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
