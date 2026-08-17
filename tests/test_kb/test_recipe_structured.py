"""配方结构化字段工具测试（V6-Phase 2）。

覆盖 recipe_structured 全部函数：
- _to_ml / _split_fraction：单位换算与数量解析
- parse_recipe_section / _parse_one / _clean_name：用料表解析
- infer_base_spirit：基酒推断（显式映射/类目兜底/other/空）
- compute_abv：体积加权 / 无体积估算兜底 / 异常降级
- _ingredient_abv：注册表 / 兜底表 / 品牌前缀剥离 / 基酒词兜底
- build_ingredients_json：序列化
- _parse_abv_section：显式酒精度解析
- structured_from_content：一键入口
"""
from __future__ import annotations

import pytest


# ===========================================================================
# _to_ml：单位换算
# ===========================================================================
class TestToMl:
    def test_no_unit_returns_amount(self):
        from hermes_kb.recipe_structured import _to_ml

        assert _to_ml(1, "") == 1.0

    def test_ml(self):
        from hermes_kb.recipe_structured import _to_ml

        assert _to_ml(60, "ml") == 60.0

    def test_cl(self):
        from hermes_kb.recipe_structured import _to_ml

        assert _to_ml(6, "cl") == 60.0

    def test_plural_unit(self):
        from hermes_kb.recipe_structured import _to_ml

        assert _to_ml(2, "cups") == 480.0

    def test_parts(self):
        from hermes_kb.recipe_structured import _to_ml

        assert _to_ml(2, "parts") == 60.0

    def test_bar_spoon(self):
        from hermes_kb.recipe_structured import _to_ml

        assert _to_ml(2, "bar spoon") == 10.0

    def test_no_volume_unit(self):
        from hermes_kb.recipe_structured import _to_ml

        assert _to_ml(1, "whole") == 0.0
        assert _to_ml(2, "slices") == 0.0

    def test_unknown_unit(self):
        from hermes_kb.recipe_structured import _to_ml

        assert _to_ml(1, "xyz") == 0.0


# ===========================================================================
# _split_fraction：数量解析
# ===========================================================================
class TestSplitFraction:
    def test_range_midpoint(self):
        from hermes_kb.recipe_structured import _split_fraction

        assert _split_fraction("1-2") == 1.5

    def test_whole_and_fraction(self):
        from hermes_kb.recipe_structured import _split_fraction

        assert _split_fraction("1 3/4") == 1.75

    def test_pure_fraction(self):
        from hermes_kb.recipe_structured import _split_fraction

        assert _split_fraction("3/4") == 0.75

    def test_plain_int(self):
        from hermes_kb.recipe_structured import _split_fraction

        assert _split_fraction("2") == 2.0

    def test_invalid_returns_zero(self):
        from hermes_kb.recipe_structured import _split_fraction

        assert _split_fraction("abc") == 0.0

    def test_zero_denominator_returns_zero(self):
        from hermes_kb.recipe_structured import _split_fraction

        assert _split_fraction("1/0") == 0.0


# ===========================================================================
# parse_recipe_section：用料表解析
# ===========================================================================
class TestParseRecipeSection:
    def test_empty_content(self):
        from hermes_kb.recipe_structured import parse_recipe_section

        assert parse_recipe_section("") == []

    def test_no_recipe_section(self):
        from hermes_kb.recipe_structured import parse_recipe_section

        assert parse_recipe_section("# 标题\n\n## 简介\n无配方") == []

    def test_standard_iba_format(self):
        """名称在前："金酒 60ml"。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = (
            "# 金菲士\n\n## 配方\n"
            "- 金酒 60ml\n"
            "- 柠檬汁 30 ml\n"
            "\n## 调制技法\nShake\n"
        )
        items = parse_recipe_section(content)
        assert items == [
            {"name": "金酒", "measure": "60ml", "amount_ml": 60.0},
            {"name": "柠檬汁", "measure": "30ml", "amount_ml": 30.0},
        ]

    def test_measure_first_format(self):
        """数量在前（bar_assistant）："60 ml 金酒"。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = "# X\n\n## 配方\n- 60 ml 金酒\n- 30 ml 柠檬汁\n"
        items = parse_recipe_section(content)
        assert items[0] == {"name": "金酒", "measure": "60ml", "amount_ml": 60.0}

    def test_fraction_shot(self):
        """"金酒 1 3/4 shot" → 1.75 * 45 = 78.75ml。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = "# X\n\n## 配方\n- 金酒 1 3/4 shot\n"
        items = parse_recipe_section(content)
        assert items[0]["name"] == "金酒"
        assert items[0]["amount_ml"] == pytest.approx(78.75)

    def test_fraction_cup_trailing_desc(self):
        """"咖啡 1/2 cup instant" → 0.5 * 240 = 120ml。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = "# X\n\n## 配方\n- 咖啡 1/2 cup instant\n"
        items = parse_recipe_section(content)
        assert items[0]["name"] == "咖啡"
        assert items[0]["amount_ml"] == 120.0

    def test_parts_unit(self):
        """"伏特加 3 parts" → 3 * 30 = 90ml。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = "# X\n\n## 配方\n- 伏特加 3 parts\n"
        items = parse_recipe_section(content)
        assert items[0]["amount_ml"] == 90.0

    def test_no_amount_keeps_name(self):
        """无用量行仅保留名称。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = "# X\n\n## 配方\n- 少量\n"
        items = parse_recipe_section(content)
        assert items[0] == {"name": "少量", "measure": "", "amount_ml": 0.0}

    def test_skips_non_dash_and_blank_and_section(self):
        """跳过非列表行、空行与下一段落。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = "# X\n\n## 配方\n- 金酒 60ml\n\n普通说明文字\n\n## 调制技法\nShake\n- 后面不算\n"
        items = parse_recipe_section(content)
        assert [i["name"] for i in items] == ["金酒"]

    def test_skips_exclamation_raw(self):
        """以 ! 开头（装饰行）跳过。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = "# X\n\n## 配方\n- !garnish 橄榄\n- 金酒 60ml\n"
        items = parse_recipe_section(content)
        assert [i["name"] for i in items] == ["金酒"]

    def test_skips_empty_raw(self):
        """"- " 空行跳过。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = "# X\n\n## 配方\n- \n- 金酒 60ml\n"
        items = parse_recipe_section(content)
        assert [i["name"] for i in items] == ["金酒"]

    def test_trailing_quantifier_stripped(self):
        """装饰数量（"橄榄 1 颗"）剥离数量词保留材料名。"""
        from hermes_kb.recipe_structured import parse_recipe_section

        content = "# X\n\n## 配方\n- 橄榄 1 颗\n- 金酒 60ml\n"
        items = parse_recipe_section(content)
        assert items[0]["name"] == "橄榄"


# ===========================================================================
# _clean_name：材料名清理
# ===========================================================================
class TestCleanName:
    def test_strip_parentheses(self):
        from hermes_kb.recipe_structured import _clean_name

        assert _clean_name("威士忌（波本）") == "威士忌"

    def test_strip_trailing_quantifier(self):
        from hermes_kb.recipe_structured import _clean_name

        assert _clean_name("橄榄 1 颗") == "橄榄"

    def test_strip_trailing_punctuation(self):
        from hermes_kb.recipe_structured import _clean_name

        assert _clean_name("柠檬片。") == "柠檬片"


# ===========================================================================
# infer_base_spirit：基酒推断
# ===========================================================================
class TestInferBaseSpirit:
    def test_empty(self):
        from hermes_kb.recipe_structured import infer_base_spirit

        assert infer_base_spirit([]) == ""

    def test_explicit_map_hit(self):
        from hermes_kb.recipe_structured import infer_base_spirit

        assert infer_base_spirit(["金酒", "柠檬汁"]) == "gin"
        assert infer_base_spirit(["干邑白兰地"]) == "brandy"

    def test_registry_category_unmapped_other(self):
        """base_spirit 类目但未显式映射 → other（如白酒）。"""
        from hermes_kb.recipe_structured import infer_base_spirit

        assert infer_base_spirit(["白酒"]) == "other"

    def test_no_base_spirit_returns_empty(self):
        from hermes_kb.recipe_structured import infer_base_spirit

        assert infer_base_spirit(["柠檬汁", "糖浆"]) == ""


# ===========================================================================
# compute_abv：酒精度计算
# ===========================================================================
class TestComputeAbv:
    def test_weighted_average(self):
        """金酒(0.40)*60 + 柠檬汁(0.0)*30 → 0.2667。"""
        from hermes_kb.recipe_structured import compute_abv

        items = [
            {"name": "金酒", "amount_ml": 60.0},
            {"name": "柠檬汁", "amount_ml": 30.0},
        ]
        assert compute_abv(items) == pytest.approx(0.2667, abs=1e-4)

    def test_skips_zero_volume(self):
        from hermes_kb.recipe_structured import compute_abv

        items = [
            {"name": "金酒", "amount_ml": 60.0},
            {"name": "薄荷叶", "amount_ml": 0.0},
        ]
        assert compute_abv(items) == 0.4

    def test_empty_returns_zero(self):
        from hermes_kb.recipe_structured import compute_abv

        assert compute_abv([]) == 0.0

    def test_no_names_returns_zero(self):
        from hermes_kb.recipe_structured import compute_abv

        assert compute_abv([{"name": "", "amount_ml": 0.0}]) == 0.0

    def test_no_volume_falls_back_to_estimate(self):
        """无有效体积 → ingredient_strength 估算兜底。"""
        from hermes_kb.recipe_structured import compute_abv

        result = compute_abv([{"name": "金酒", "amount_ml": 0.0}])
        assert result == pytest.approx(0.4)

    def test_estimate_error_returns_zero(self, monkeypatch):
        """估算抛异常 → 0.0（不阻塞）。"""
        import hermes_kb.ingredient_strength as is_mod
        from hermes_kb.recipe_structured import compute_abv

        def boom(names):
            raise RuntimeError("boom")

        monkeypatch.setattr(is_mod, "estimate_recipe_stats", boom)
        assert compute_abv([{"name": "金酒", "amount_ml": 0.0}]) == 0.0


# ===========================================================================
# _ingredient_abv：材料酒精度
# ===========================================================================
class TestIngredientAbv:
    def test_registry_hit(self):
        from hermes_kb.recipe_structured import _ingredient_abv

        assert _ingredient_abv("金酒") == 0.40

    def test_fallback_dict(self):
        from hermes_kb.recipe_structured import _ingredient_abv

        assert _ingredient_abv("Everclear") == 0.95

    def test_brand_prefix_strip(self):
        """"Fresh Gin" → 剥离品牌前缀 fresh → gin(0.40)。"""
        from hermes_kb.recipe_structured import _ingredient_abv

        assert _ingredient_abv("Fresh Gin") == 0.40

    def test_spirit_word_fallback(self):
        """"Goslings Rum" → 尾部基酒词 rum(0.40)。"""
        from hermes_kb.recipe_structured import _ingredient_abv

        assert _ingredient_abv("Goslings Rum") == 0.40

    def test_brand_strip_hits_fallback_dict(self):
        """"Fresh Lemon Juice" → 剥离 fresh 后命中兜底表 lemon juice(0.0)。"""
        from hermes_kb.recipe_structured import _ingredient_abv

        assert _ingredient_abv("Fresh Lemon Juice") == 0.0

    def test_brand_strip_hits_fallback_after_canonicalize(self):
        """"Fresh Soda Water" → 剥离 fresh 后 soda water 命中兜底表(0.0)。"""
        from hermes_kb.recipe_structured import _ingredient_abv

        assert _ingredient_abv("Fresh Soda Water") == 0.0

    def test_first_spirit_word_fallback(self):
        """"Rum Punch" → 首词基酒 rum(0.40)。"""
        from hermes_kb.recipe_structured import _ingredient_abv

        assert _ingredient_abv("Rum Punch") == 0.40

    def test_unknown_returns_zero(self):
        from hermes_kb.recipe_structured import _ingredient_abv

        assert _ingredient_abv("神秘材料XYZ") == 0.0


# ===========================================================================
# build_ingredients_json：序列化
# ===========================================================================
class TestBuildIngredientsJson:
    def test_with_measure(self):
        from hermes_kb.recipe_structured import build_ingredients_json

        items = [{"name": "金酒", "measure": "60ml"}]
        assert build_ingredients_json(items) == '[{"name": "金酒", "measure": "60ml"}]'

    def test_without_measure_omitted(self):
        from hermes_kb.recipe_structured import build_ingredients_json

        items = [{"name": "金酒", "measure": ""}]
        assert build_ingredients_json(items) == '[{"name": "金酒"}]'

    def test_filters_empty_name(self):
        from hermes_kb.recipe_structured import build_ingredients_json

        assert build_ingredients_json([{"name": ""}]) == "[]"

    def test_empty(self):
        from hermes_kb.recipe_structured import build_ingredients_json

        assert build_ingredients_json([]) == "[]"


# ===========================================================================
# _parse_abv_section：显式酒精度
# ===========================================================================
class TestParseAbvSection:
    def test_single_line_percent(self):
        from hermes_kb.recipe_structured import _parse_abv_section

        assert _parse_abv_section("## 酒精度 12.5%") == 0.125

    def test_empty_returns_none(self):
        from hermes_kb.recipe_structured import _parse_abv_section

        assert _parse_abv_section("") is None

    def test_no_abv_section_returns_none(self):
        from hermes_kb.recipe_structured import _parse_abv_section

        assert _parse_abv_section("# X\n\n## 简介\n无酒精度信息") is None

    def test_out_of_range_returns_none(self):
        from hermes_kb.recipe_structured import _parse_abv_section

        assert _parse_abv_section("## 酒精度 120%") is None

    def test_invalid_percent_returns_none(self):
        from hermes_kb.recipe_structured import _parse_abv_section

        assert _parse_abv_section("## 酒精度 abc%") is None

    def test_two_line_format_returns_none(self):
        """bar-assistant 两行格式（当前实现不识别，记录现状）。"""
        from hermes_kb.recipe_structured import _parse_abv_section

        assert _parse_abv_section("## 酒精度\n12.5%") is None


# ===========================================================================
# structured_from_content：一键入口
# ===========================================================================
class TestStructuredFromContent:
    def test_full_recipe(self):
        from hermes_kb.recipe_structured import structured_from_content

        content = "# 金菲士\n\n## 配方\n- 金酒 60ml\n- 柠檬汁 30 ml\n\n## 调制技法\nShake\n"
        result = structured_from_content(content)
        assert result["base_spirit"] == "gin"
        assert result["abv"] == pytest.approx(0.2667, abs=1e-4)
        assert result["ingredients_json"] == (
            '[{"name": "金酒", "measure": "60ml"}, '
            '{"name": "柠檬汁", "measure": "30ml"}]'
        )

    def test_explicit_abv_preferred(self):
        """显式酒精度优先于体积加权。"""
        from hermes_kb.recipe_structured import structured_from_content

        content = "## 配方\n- 金酒 60ml\n\n## 酒精度 40%"
        result = structured_from_content(content)
        assert result["abv"] == 0.4

    def test_no_spirit_defaults_other(self):
        from hermes_kb.recipe_structured import structured_from_content

        content = "## 配方\n- 柠檬汁 30 ml\n"
        result = structured_from_content(content)
        assert result["base_spirit"] == "other"

    def test_empty_content(self):
        from hermes_kb.recipe_structured import structured_from_content

        result = structured_from_content("")
        assert result == {"base_spirit": "other", "abv": 0.0, "ingredients_json": "[]"}
