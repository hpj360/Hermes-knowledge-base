"""增强版材料注册表测试（G1：ABV + 品牌字段 + 扩展材料）。"""
from __future__ import annotations

import pytest


def test_get_abv():
    """G1: 根据标准名获取 ABV，未知返回 0.0。"""
    from hermes_kb.ingredients import get_abv

    assert get_abv("金酒") == pytest.approx(0.40)
    assert get_abv("威士忌") == pytest.approx(0.40)
    assert get_abv("味美思") == pytest.approx(0.18)
    assert get_abv("苦精") == pytest.approx(0.44)
    assert get_abv("糖浆") == pytest.approx(0.0)
    assert get_abv("柠檬汁") == pytest.approx(0.0)
    # 未知材料
    assert get_abv("不存在的材料") == pytest.approx(0.0)
    assert get_abv("") == pytest.approx(0.0)


def test_get_brands():
    """G1: 已知材料返回品牌列表，未知返回空。"""
    from hermes_kb.ingredients import get_brands

    gin_brands = get_brands("金酒")
    assert isinstance(gin_brands, list)
    assert "Gordon's" in gin_brands
    assert "Tanqueray" in gin_brands
    # campari 只有一个品牌
    assert get_brands("金巴利") == ["Campari"]
    # 非酒精材料品牌为空列表
    assert get_brands("柠檬汁") == []
    # 未知材料
    assert get_brands("不存在的材料") == []
    # 返回的列表不应是内部引用（避免外部篡改注册表）
    brands = get_brands("金酒")
    brands.append("HACK")
    assert "HACK" not in get_brands("金酒")


def test_new_ingredients_coverage():
    """G1: 新增材料都能通过 canonicalize 查到。"""
    from hermes_kb.ingredients import canonicalize

    new_canonicals = [
        # 烈酒类
        "苦艾烈酒", "波本威士忌", "干邑白兰地", "爱尔兰威士忌", "黑麦威士忌",
        "苏格兰威士忌", "皮斯科", "阿夸维特", "黑朗姆酒", "白朗姆酒", "陈年朗姆酒",
        # 利口酒类
        "苦杏仁酒", "百利甜酒", "香波力娇酒", "咖啡力娇酒", "柑曼怡", "加利亚诺",
        "蜜瓜力娇酒", "蓝柑香酒", "可可力娇酒", "黑加仑力娇酒", "薄荷力娇酒",
        "白橙力娇酒", "蜜桃香甜酒", "杏子白兰地", "樱桃力娇酒",
        # 葡萄酒/起泡酒
        "香槟", "普罗塞克", "红葡萄酒", "波特酒",
        # 其他
        "干味美思", "甜味美思", "橙味苦精", "蛋清", "奶油", "浓缩咖啡",
        "红石榴糖浆", "蜂蜜糖浆", "龙舌兰蜜", "椰奶油",
    ]
    for canonical in new_canonicals:
        assert canonicalize(canonical) == canonical, f"新增材料未被注册: {canonical}"

    # 部分新材料的英文别名也可归一化
    assert canonicalize("amaretto") == "苦杏仁酒"
    assert canonicalize("irish cream") == "百利甜酒"
    assert canonicalize("grand marnier") == "柑曼怡"
    assert canonicalize("blue curacao") == "蓝柑香酒"
    assert canonicalize("champagne") == "香槟"
    assert canonicalize("red wine") == "红葡萄酒"


def test_new_ingredients_have_abv_and_brands():
    """G1: 新增材料条目均含 abv 与 brands 字段。"""
    from hermes_kb.ingredients import INGREDIENT_REGISTRY, get_abv, get_brands

    # 抽检若干新材料具备 ABV 与品牌字段
    assert get_abv("苦艾烈酒") == pytest.approx(0.55)
    assert get_abv("咖啡力娇酒") == pytest.approx(0.20)
    # P2-A: 品牌列表已扩充，使用包含断言代替严格相等
    amaretto_brands = get_brands("苦杏仁酒")
    assert "Disaronno" in amaretto_brands
    assert amaretto_brands[0] == "Disaronno"  # 主品牌保持首位
    coffee_brands = get_brands("咖啡力娇酒")
    assert "Kahlúa" in coffee_brands and "Tia Maria" in coffee_brands
    assert get_brands("百利甜酒")[0] == "Baileys"

    # 全注册表每条都应有 abv(float) 与 brands(list)
    for info in INGREDIENT_REGISTRY.values():
        assert "abv" in info, f"{info['canonical']} 缺 abv"
        assert isinstance(info["abv"], float)
        assert 0.0 <= info["abv"] <= 1.0
        assert "brands" in info, f"{info['canonical']} 缺 brands"
        assert isinstance(info["brands"], list)


def test_backward_compatible():
    """G1: 原有函数行为不变（具体烈酒英文别名已解冲突，归一化到具体条目）。"""
    from hermes_kb.ingredients import (
        all_canonical,
        canonicalize,
        get_category,
        list_by_category,
        INGREDIENT_REGISTRY,
    )

    # canonicalize 核心映射保持
    assert canonicalize("gin") == "金酒"
    assert canonicalize("Gordon's") == "金酒"
    assert canonicalize("whiskey") == "威士忌"
    assert canonicalize("whisky") == "威士忌"
    assert canonicalize("rum") == "朗姆酒"
    assert canonicalize("vermouth") == "味美思"
    assert canonicalize("苦艾酒") == "味美思"
    # P2-A 修复：具体烈酒英文别名归一化到具体条目（不再被通用别名遮蔽）
    assert canonicalize("bourbon") == "波本威士忌"
    assert canonicalize("scotch") == "苏格兰威士忌"
    assert canonicalize("rye") == "黑麦威士忌"
    assert canonicalize("cognac") == "干邑白兰地"
    assert canonicalize("white rum") == "白朗姆酒"
    assert canonicalize("dark rum") == "黑朗姆酒"
    assert canonicalize("triple sec") == "白橙力娇酒"
    # 未知材料返回原值
    assert canonicalize("某未知材料") == "某未知材料"
    assert canonicalize("") == ""

    # get_category
    assert get_category("金酒") == "base_spirit"
    assert get_category("柠檬汁") == "juice"
    assert get_category("橄榄") == "garnish"
    assert get_category("不存在") is None

    # list_by_category：原 5 种装饰仍在（M3-A 扩展后 garnish 增多，验证前 5 项不变）
    garnishes = list_by_category("garnish")
    assert garnishes[:5] == ["橄榄", "柠檬片", "薄荷叶", "樱桃", "橙皮"]
    assert len(garnishes) >= 5
    # 原有基酒 6 种仍在
    spirits = list_by_category("base_spirit")
    for s in ["金酒", "威士忌", "朗姆酒", "龙舌兰", "白兰地", "伏特加"]:
        assert s in spirits

    # all_canonical：含原有材料，且因扩展而增长
    all_names = all_canonical()
    for n in ["金酒", "威士忌", "朗姆酒", "味美思", "柠檬汁", "橄榄"]:
        assert n in all_names
    assert len(all_names) >= 26
    # 去重（标准名唯一）
    assert len(all_names) == len(set(all_names))
    # 注册表条目数与 all_canonical 一致
    assert len(all_names) == len(INGREDIENT_REGISTRY)


def test_specific_spirit_abv_resolution():
    """P2-A: 具体烈酒英文别名归一化后查到正确的 ABV（不再用通用条目 ABV）。"""
    from hermes_kb.ingredient_strength import get_ingredient_abv

    # dark rum 应查到黑朗姆酒 ABV 0.43，而非朗姆酒 0.40
    assert get_ingredient_abv("dark rum") == 0.43
    # white rum 查到白朗姆酒 0.40
    assert get_ingredient_abv("white rum") == 0.40
    # triple sec 查到白橙力娇酒 0.30，而非君度 0.40
    assert get_ingredient_abv("triple sec") == 0.30
    # 通用 rum 仍查到朗姆酒 0.40
    assert get_ingredient_abv("rum") == 0.40


# ===========================================================================
# P2-A 新增字段查询函数：get_tags / get_origin / get_abv_range
# ===========================================================================
class TestTagsOriginAbvRange:
    """覆盖 P2-A 新增的 tags/origin/abv_range 字段查询函数。"""

    def test_get_tags_known_ingredient(self):
        """已知材料的 tags 返回（含金酒的 juniper/botanical）。"""
        from hermes_kb.ingredients import get_tags

        gin_tags = get_tags("金酒")
        assert isinstance(gin_tags, list)
        assert "juniper" in gin_tags
        assert "botanical" in gin_tags

    def test_get_tags_no_tags_returns_empty(self):
        """无 tags 字段的材料返回空列表。"""
        from hermes_kb.ingredients import get_tags

        # 柠檬汁这类果汁通常无 tags
        result = get_tags("柠檬汁")
        assert result == []

    def test_get_tags_unknown_returns_empty(self):
        """未知材料返回空列表。"""
        from hermes_kb.ingredients import get_tags

        assert get_tags("不存在的材料") == []
        assert get_tags("") == []

    def test_get_tags_returns_copy_not_reference(self):
        """返回的列表是副本，外部修改不影响注册表。"""
        from hermes_kb.ingredients import get_tags

        tags = get_tags("金酒")
        tags.append("HACK_TAG")
        assert "HACK_TAG" not in get_tags("金酒")

    def test_get_origin_known(self):
        """已知材料返回产地。"""
        from hermes_kb.ingredients import get_origin

        gin_origin = get_origin("金酒")
        assert isinstance(gin_origin, str)
        # 金酒产地包含 Netherlands 或 UK
        assert "Netherlands" in gin_origin or "UK" in gin_origin

    def test_get_origin_no_origin_returns_empty(self):
        """无 origin 字段的材料返回空字符串。"""
        from hermes_kb.ingredients import get_origin

        # 柠檬汁这类通常无产地
        result = get_origin("柠檬汁")
        assert result == ""

    def test_get_origin_unknown_returns_empty(self):
        """未知材料返回空字符串。"""
        from hermes_kb.ingredients import get_origin

        assert get_origin("不存在的材料") == ""
        assert get_origin("") == ""

    def test_get_abv_range_known(self):
        """已知材料返回 (min, max) 范围。"""
        from hermes_kb.ingredients import get_abv_range

        gin_range = get_abv_range("金酒")
        assert gin_range is not None
        assert isinstance(gin_range, tuple)
        assert len(gin_range) == 2
        min_v, max_v = gin_range
        assert min_v == 0.37
        assert max_v == 0.47
        assert min_v < max_v

    def test_get_abv_range_unknown_returns_none(self):
        """未知材料返回 None。"""
        from hermes_kb.ingredients import get_abv_range

        assert get_abv_range("不存在的材料") is None
        assert get_abv_range("") is None

    def test_get_abv_range_no_range_field_returns_none(self):
        """无 abv_range 字段的材料返回 None。"""
        from hermes_kb.ingredients import get_abv_range

        # 柠檬汁通常无 abv_range
        result = get_abv_range("柠檬汁")
        assert result is None


# ===========================================================================
# find_by_tags / find_by_origin
# ===========================================================================
class TestFindByTagsAndOrigin:
    """覆盖按 tags/origin 反查材料的函数。"""

    def test_find_by_tags_or_match(self):
        """OR 匹配：任一标签命中即返回。"""
        from hermes_kb.ingredients import find_by_tags

        result = find_by_tags(["juniper"])
        assert isinstance(result, list)
        assert "金酒" in result

    def test_find_by_tags_multiple_or(self):
        """OR 匹配多个标签。"""
        from hermes_kb.ingredients import find_by_tags

        result = find_by_tags(["juniper", "citrus"])
        assert "金酒" in result  # juniper 命中
        # citrus 命中的材料也应在结果中

    def test_find_by_tags_and_match(self):
        """AND 匹配：必须全部命中。"""
        from hermes_kb.ingredients import find_by_tags

        # 金酒有 juniper + botanical + herbal + dry
        result = find_by_tags(["juniper", "botanical"], match_all=True)
        assert "金酒" in result

    def test_find_by_tags_and_no_match(self):
        """AND 匹配无命中返回空。"""
        from hermes_kb.ingredients import find_by_tags

        # 不可能同时存在的标签组合
        result = find_by_tags(["juniper", "nonexistent_tag_xyz"], match_all=True)
        assert result == []

    def test_find_by_tags_empty_input(self):
        """空 tags 列表返回空。"""
        from hermes_kb.ingredients import find_by_tags

        assert find_by_tags([]) == []

    def test_find_by_tags_case_insensitive(self):
        """标签大小写不敏感。"""
        from hermes_kb.ingredients import find_by_tags

        result_upper = find_by_tags(["JUNIPER"])
        result_lower = find_by_tags(["juniper"])
        assert result_upper == result_lower
        assert "金酒" in result_upper

    def test_find_by_tags_no_match(self):
        """无命中的标签返回空列表。"""
        from hermes_kb.ingredients import find_by_tags

        assert find_by_tags(["nonexistent_tag_xyz"]) == []

    def test_find_by_tags_skips_empty_tags_items(self):
        """无 tags 字段的材料被跳过（不报错）。"""
        from hermes_kb.ingredients import find_by_tags

        # 柠檬汁无 tags，搜索任何标签都不应包含它
        result = find_by_tags(["citrus", "sweet", "juniper"])
        assert "柠檬汁" not in result

    def test_find_by_origin_known(self):
        """按已知产地查询返回材料。"""
        from hermes_kb.ingredients import find_by_origin

        # Netherlands 应匹配金酒（origin=Netherlands/UK）
        result = find_by_origin("Netherlands")
        assert "金酒" in result

    def test_find_by_origin_case_insensitive(self):
        """产地关键词大小写不敏感。"""
        from hermes_kb.ingredients import find_by_origin

        result_upper = find_by_origin("NETHERLANDS")
        result_lower = find_by_origin("netherlands")
        assert result_upper == result_lower
        assert "金酒" in result_upper

    def test_find_by_origin_partial_match(self):
        """产地部分匹配（关键词是 origin 子串）。"""
        from hermes_kb.ingredients import find_by_origin

        # "Scot" 应匹配 Scotland
        result = find_by_origin("Scot")
        assert "威士忌" in result or "苏格兰威士忌" in result

    def test_find_by_origin_empty_input(self):
        """空产地关键词返回空。"""
        from hermes_kb.ingredients import find_by_origin

        assert find_by_origin("") == []

    def test_find_by_origin_no_match(self):
        """无命中返回空。"""
        from hermes_kb.ingredients import find_by_origin

        assert find_by_origin("不存在的国家XYZ") == []

    def test_find_by_origin_skips_empty_origin(self):
        """无 origin 字段的材料被跳过。"""
        from hermes_kb.ingredients import find_by_origin

        # 柠檬汁无 origin，搜索任何产地都不应包含
        result = find_by_origin("Netherlands")
        assert "柠檬汁" not in result


# ===========================================================================
# all_tags / all_origins
# ===========================================================================
class TestAllTagsAndOrigins:
    """覆盖 all_tags / all_origins 列表函数。"""

    def test_all_tags_returns_sorted_unique(self):
        """all_tags 返回排序去重的标签列表。"""
        from hermes_kb.ingredients import all_tags

        tags = all_tags()
        assert isinstance(tags, list)
        assert len(tags) > 0
        # 排序
        assert tags == sorted(tags)
        # 去重
        assert len(tags) == len(set(tags))
        # 包含已知标签
        assert "juniper" in tags
        assert "botanical" in tags

    def test_all_tags_lowercase(self):
        """all_tags 所有标签为小写。"""
        from hermes_kb.ingredients import all_tags

        for tag in all_tags():
            assert tag == tag.lower()

    def test_all_origins_returns_sorted_unique(self):
        """all_origins 返回排序去重的产地列表。"""
        from hermes_kb.ingredients import all_origins

        origins = all_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0
        # 排序
        assert origins == sorted(origins)
        # 去重
        assert len(origins) == len(set(origins))
        # 包含已知产地（Netherlands 来自金酒）
        assert "Netherlands" in origins

    def test_all_origins_splits_multi_origin(self):
        """多产地字符串（如 Netherlands/UK）被拆分为独立项。"""
        from hermes_kb.ingredients import all_origins

        origins = all_origins()
        # 金酒 origin=Netherlands/UK，应拆分为 Netherlands 和 UK
        assert "Netherlands" in origins
        assert "UK" in origins

    def test_all_origins_no_empty_strings(self):
        """all_origins 不含空字符串。"""
        from hermes_kb.ingredients import all_origins

        origins = all_origins()
        assert "" not in origins
