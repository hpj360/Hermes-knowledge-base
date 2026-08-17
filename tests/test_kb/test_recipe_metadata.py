"""recipe_metadata 模块单元测试。

覆盖 infer_technique / infer_glassware / infer_iba_category / infer_flavor_profile
各分支、大小写不敏感、中英文混合 content 等场景。
"""
from __future__ import annotations

# === infer_technique ===


def test_infer_technique_shake_yaojiuhu():
    """摇酒壶 → shake。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("摇酒壶加冰") == "shake"


def test_infer_technique_shake_yaoyun():
    """摇匀 → shake。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("摇匀后倒入杯中") == "shake"


def test_infer_technique_shake_english():
    """shake → shake。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("Shake with ice") == "shake"


def test_infer_technique_shake_uppercase():
    """SHAKE 大小写不敏感。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("SHAKE well") == "shake"


def test_infer_technique_shake_mixed_case():
    """sHaKe 混合大小写命中。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("sHaKe") == "shake"


def test_infer_technique_stir_chinese():
    """搅拌 → stir。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("搅拌均匀") == "stir"


def test_infer_technique_stir_english():
    """stir → stir。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("stir the mixture") == "stir"


def test_infer_technique_build_chinese_zhijie():
    """直接倒入 → build。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("直接倒入杯中") == "build"


def test_infer_technique_build_chinese_duihe():
    """兑和 → build。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("兑和法制作") == "build"


def test_infer_technique_build_english():
    """build → build。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("build in glass") == "build"


def test_infer_technique_layer_chinese():
    """分层 → layer。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("分层倒入") == "layer"


def test_infer_technique_layer_english():
    """layer → layer。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("layer the drinks") == "layer"


def test_infer_technique_muddle_dao():
    """捣压 → muddle。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("捣压薄荷叶") == "muddle"


def test_infer_technique_muddle_sui():
    """捣碎 → muddle。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("捣碎柠檬") == "muddle"


def test_infer_technique_muddle_english():
    """muddle → muddle。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("muddle the mint") == "muddle"


def test_infer_technique_blend_english():
    """blend → blend。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("blend with ice") == "blend"


def test_infer_technique_blend_chinese():
    """搅拌机 → blend（搅拌机是 blend 关键词，不应被 stir 的 '搅拌' 误匹配）。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("搅拌机打碎") == "blend"


def test_infer_technique_empty_no_match():
    """无任何关键词命中 → 空字符串。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("倒入杯中") == ""


def test_infer_technique_empty_string():
    """空字符串输入 → 空字符串。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("") == ""


def test_infer_technique_priority_shake_over_stir():
    """摇酒壶 + 搅拌 同时命中，优先 shake。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("摇酒壶搅拌均匀") == "shake"


def test_infer_technique_mixed_cn_en():
    """中英文混合 content 命中。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("用 shaker 摇匀") == "shake"


def test_infer_technique_ingredients_param_optional():
    """ingredients 参数可选，不影响 content 匹配。"""
    from hermes_kb.recipe_metadata import infer_technique

    assert infer_technique("摇匀", ingredients=["金酒"]) == "shake"
    assert infer_technique("倒入杯中", ingredients=["伏特加"]) == ""


# === infer_glassware ===


def test_infer_glassware_martini_chinese():
    """马天尼杯（中文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("倒入马天尼杯") == "马天尼杯"


def test_infer_glassware_martini_english():
    """martini glass（英文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("serve in martini glass") == "马天尼杯"


def test_infer_glassware_rocks_chinese():
    """古典杯（中文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("古典杯加冰") == "古典杯"


def test_infer_glassware_rocks_english():
    """rocks glass（英文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("rocks glass") == "古典杯"


def test_infer_glassware_old_fashioned():
    """old fashioned → 古典杯。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("old fashioned glass") == "古典杯"


def test_infer_glassware_highball_chinese():
    """高球杯（中文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("高球杯") == "高球杯"


def test_infer_glassware_highball_english():
    """highball（英文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("highball glass") == "高球杯"


def test_infer_glassware_collins_chinese():
    """柯林斯杯（中文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("柯林斯杯") == "柯林斯杯"


def test_infer_glassware_collins_english():
    """collins（英文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("collins glass") == "柯林斯杯"


def test_infer_glassware_champagne_chinese():
    """香槟杯（中文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("香槟杯") == "香槟杯"


def test_infer_glassware_champagne_english():
    """champagne flute（英文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("champagne flute") == "香槟杯"


def test_infer_glassware_hurricane_chinese():
    """飓风杯（中文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("飓风杯") == "飓风杯"


def test_infer_glassware_hurricane_english():
    """hurricane（英文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("hurricane glass") == "飓风杯"


def test_infer_glassware_margarita_chinese():
    """玛格丽特杯（中文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("玛格丽特杯") == "玛格丽特杯"


def test_infer_glassware_margarita_english():
    """margarita（英文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("margarita glass") == "玛格丽特杯"


def test_infer_glassware_brandy_chinese():
    """白兰地杯（中文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("白兰地杯") == "白兰地杯"


def test_infer_glassware_brandy_english():
    """snifter（英文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("snifter") == "白兰地杯"


def test_infer_glassware_coupe_chinese():
    """Coupe 杯（中文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("Coupe 杯") == "Coupe 杯"


def test_infer_glassware_coupe_english():
    """coupe（英文）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("coupe glass") == "Coupe 杯"


def test_infer_glassware_no_match():
    """无匹配 → 空字符串。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("倒入杯中") == ""


def test_infer_glassware_empty_string():
    """空字符串 → 空字符串。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("") == ""


def test_infer_glassware_case_insensitive():
    """大小写不敏感。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("MARTINI GLASS") == "马天尼杯"
    assert infer_glassware("Highball") == "高球杯"


def test_infer_glassware_title_param():
    """title 参数存在但不参与匹配（仅 content 匹配）。"""
    from hermes_kb.recipe_metadata import infer_glassware

    assert infer_glassware("马天尼杯", title="马天尼") == "马天尼杯"
    assert infer_glassware("倒入杯中", title="马天尼") == ""


# === infer_iba_category ===


def test_infer_iba_category_unforgettables():
    """The Unforgettables → unforgettables。"""
    from hermes_kb.recipe_metadata import infer_iba_category

    assert infer_iba_category("The Unforgettables") == "unforgettables"


def test_infer_iba_category_contemporary_classics():
    """Contemporary Classics → contemporary_classics。"""
    from hermes_kb.recipe_metadata import infer_iba_category

    assert infer_iba_category("Contemporary Classics") == "contemporary_classics"


def test_infer_iba_category_new_era_drinks():
    """New Era Drinks → new_era_drinks。"""
    from hermes_kb.recipe_metadata import infer_iba_category

    assert infer_iba_category("New Era Drinks") == "new_era_drinks"


def test_infer_iba_category_unknown():
    """未知分类 → contemporary_classics（旧分类默认映射）。"""
    from hermes_kb.recipe_metadata import infer_iba_category

    assert infer_iba_category("Some Other Category") == "contemporary_classics"


def test_infer_iba_category_empty():
    """空字符串 → 空字符串。"""
    from hermes_kb.recipe_metadata import infer_iba_category

    assert infer_iba_category("") == ""


# === infer_flavor_profile ===


def test_infer_flavor_profile_gin_vermouth_non_empty():
    """['金酒','味美思'] → 非空字符串。"""
    from hermes_kb.recipe_metadata import infer_flavor_profile

    result = infer_flavor_profile(["金酒", "味美思"])
    assert isinstance(result, str)
    assert result != ""
    # 金酒 tags: juniper, botanical, herbal, dry
    # 味美思 tags: botanical, aromatic, herbal, wine-fortified
    tags = result.split(";")
    assert "juniper" in tags
    assert "botanical" in tags
    assert "herbal" in tags
    assert "dry" in tags
    assert "aromatic" in tags
    assert "wine-fortified" in tags


def test_infer_flavor_profile_empty_list():
    """空列表 → 空字符串。"""
    from hermes_kb.recipe_metadata import infer_flavor_profile

    assert infer_flavor_profile([]) == ""


def test_infer_flavor_profile_dedup():
    """重复标签去重：金酒和味美思都有 botanical/herbal。"""
    from hermes_kb.recipe_metadata import infer_flavor_profile

    result = infer_flavor_profile(["金酒", "味美思"])
    tags = result.split(";")
    assert tags.count("botanical") == 1
    assert tags.count("herbal") == 1
    assert len(tags) == len(set(tags))


def test_infer_flavor_profile_unknown_ingredient():
    """未知材料无 tags → 空字符串。"""
    from hermes_kb.recipe_metadata import infer_flavor_profile

    assert infer_flavor_profile(["不存在的材料xyz"]) == ""


def test_infer_flavor_profile_no_tags_ingredient():
    """无 tags 字段的材料（如柠檬汁）→ 空字符串。"""
    from hermes_kb.recipe_metadata import infer_flavor_profile

    assert infer_flavor_profile(["柠檬汁"]) == ""


def test_infer_flavor_profile_canonicalize_alias():
    """传入英文别名也能归一化并查到 tags。"""
    from hermes_kb.recipe_metadata import infer_flavor_profile

    result = infer_flavor_profile(["gin", "vermouth"])
    assert result != ""
    tags = result.split(";")
    assert "juniper" in tags
    assert "botanical" in tags


def test_infer_flavor_profile_single_ingredient():
    """单材料聚合。"""
    from hermes_kb.recipe_metadata import infer_flavor_profile

    result = infer_flavor_profile(["金酒"])
    assert result != ""
    tags = result.split(";")
    assert "juniper" in tags
    assert "botanical" in tags
    assert "herbal" in tags
    assert "dry" in tags


def test_infer_flavor_profile_mixed_known_unknown():
    """已知 + 未知材料混合：只返回已知材料的 tags。"""
    from hermes_kb.recipe_metadata import infer_flavor_profile

    result = infer_flavor_profile(["金酒", "未知材料"])
    assert result != ""
    tags = result.split(";")
    assert "juniper" in tags
