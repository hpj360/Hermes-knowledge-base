"""材料强度与营养计算模块测试（G2）。"""
from __future__ import annotations

import pytest


def test_get_ingredient_abv():
    """G2: 已知材料返回正确 ABV，未知返回 0.0。"""
    from hermes_kb.ingredient_strength import get_ingredient_abv

    assert get_ingredient_abv("gin") == pytest.approx(0.40)
    assert get_ingredient_abv("Gordon's") == pytest.approx(0.40)  # 别名归一化
    assert get_ingredient_abv("vermouth") == pytest.approx(0.18)
    assert get_ingredient_abv("angostura") == pytest.approx(0.44)
    assert get_ingredient_abv("lemon juice") == pytest.approx(0.0)
    # 未知材料
    assert get_ingredient_abv("某种神秘液体") == pytest.approx(0.0)
    assert get_ingredient_abv("") == pytest.approx(0.0)


def test_calculate_cocktail_abv():
    """G2: 加权平均 ABV（45ml gin 0.40 + 15ml vermouth 0.18 = 0.345）。"""
    from hermes_kb.ingredient_strength import calculate_cocktail_abv

    abv = calculate_cocktail_abv([("gin", 45.0), ("vermouth", 15.0)])
    # (0.40*45 + 0.18*15) / 60 = 20.7/60 = 0.345
    assert abv == pytest.approx(0.345)
    # 含非酒精材料稀释
    abv2 = calculate_cocktail_abv([("gin", 45.0), ("tonic", 90.0)])
    # (0.40*45 + 0*90) / 135 = 18/135 ≈ 0.1333
    assert abv2 == pytest.approx(0.1333, abs=1e-3)
    # 空输入 / 零体积
    assert calculate_cocktail_abv([]) == pytest.approx(0.0)
    assert calculate_cocktail_abv([("gin", 0.0)]) == pytest.approx(0.0)


def test_calculate_alcohol_calories():
    """G2: 纯酒精卡路里公式（100ml × 0.40 × 0.789 × 7 = 220.92 kcal）。"""
    from hermes_kb.ingredient_strength import calculate_alcohol_calories

    kcal = calculate_alcohol_calories(100.0, 0.40)
    assert kcal == pytest.approx(220.92)
    # 非酒精材料卡路里为 0
    assert calculate_alcohol_calories(200.0, 0.0) == pytest.approx(0.0)
    # 零体积
    assert calculate_alcohol_calories(0.0, 0.40) == pytest.approx(0.0)


def test_estimate_recipe_stats():
    """G2: 无体积估算返回三字段，ABV 在合理范围。"""
    from hermes_kb.ingredient_strength import estimate_recipe_stats

    stats = estimate_recipe_stats(["gin", "vermouth", "lemon juice"])
    assert set(stats.keys()) == {"estimated_abv", "estimated_calories", "total_volume_ml"}
    # ABV 合理范围
    assert 0.0 <= stats["estimated_abv"] <= 1.0
    assert stats["total_volume_ml"] > 0
    assert stats["estimated_calories"] >= 0
    # 全装饰（零体积）应安全返回 0 ABV
    stats2 = estimate_recipe_stats(["mint", "olive"])
    assert stats2["estimated_abv"] == pytest.approx(0.0)
    assert stats2["total_volume_ml"] == pytest.approx(0.0)


def test_fetch_iba_strength_data_network_fail(monkeypatch):
    """G2: httpx 失败且无本地文件时返回空 dict。"""
    from hermes_kb import ingredient_strength
    import httpx
    from pathlib import Path

    def fake_get(*args, **kwargs):
        raise httpx.HTTPError("network down")

    def fake_exists(self):
        return False

    monkeypatch.setattr(ingredient_strength.httpx, "get", fake_get)
    monkeypatch.setattr(Path, "exists", fake_exists)
    result = ingredient_strength.fetch_iba_strength_data()
    assert result == {}


def test_get_ingredient_abv_with_fallback_prefers_local():
    """优先本地注册表：gin 命中本地 0.40，即使 strength_data 给不同值也用本地。"""
    from hermes_kb.ingredient_strength import get_ingredient_abv_with_fallback

    # 本地 gin=0.40，strength_data 故意给 0.99 验证不被采用
    abv = get_ingredient_abv_with_fallback("gin", {"gin": 0.99})
    assert abv == pytest.approx(0.40)


def test_get_ingredient_abv_with_fallback_uses_strength_data_when_local_misses():
    """本地未命中时回退 strength_data：'1 sugar cube' 本地未知，strength_data 给 0.0。"""
    from hermes_kb.ingredient_strength import get_ingredient_abv_with_fallback

    # 本地无 "1 sugar cube" 别名，回退到 strength_data
    abv = get_ingredient_abv_with_fallback("1 sugar cube", {"1 sugar cube": 0.0})
    assert abv == pytest.approx(0.0)

    # 非零回退：虚构材料 'magic liqueur' 本地未知，strength_data 给 0.25
    abv2 = get_ingredient_abv_with_fallback("Magic Liqueur", {"magic liqueur": 0.25})
    assert abv2 == pytest.approx(0.25)


def test_get_ingredient_abv_with_fallback_no_strength_data():
    """strength_data 为 None 或空时，等价于 get_ingredient_abv。"""
    from hermes_kb.ingredient_strength import (
        get_ingredient_abv,
        get_ingredient_abv_with_fallback,
    )

    assert get_ingredient_abv_with_fallback("gin", None) == get_ingredient_abv("gin")
    assert get_ingredient_abv_with_fallback("gin", {}) == get_ingredient_abv("gin")
    # 未知材料 + 无 strength_data → 0.0
    assert get_ingredient_abv_with_fallback("神秘液体", None) == pytest.approx(0.0)
    # 空字符串
    assert get_ingredient_abv_with_fallback("", {"gin": 0.4}) == pytest.approx(0.0)


def test_get_ingredient_abv_with_fallback_invalid_strength_value():
    """strength_data 值非数字时不抛异常，返回 0.0。"""
    from hermes_kb.ingredient_strength import get_ingredient_abv_with_fallback

    # 非数字值应被 try/except 兜住
    abv = get_ingredient_abv_with_fallback(
        "神秘液体", {"神秘液体": "not-a-number"}
    )
    assert abv == pytest.approx(0.0)


def test_calculate_cocktail_abv_with_strength_data():
    """calculate_cocktail_abv 接受 strength_data，未知材料用兜底 ABV。"""
    from hermes_kb.ingredient_strength import calculate_cocktail_abv

    # gin 本地 0.40 + 'mystery liqueur' 本地未知但 strength_data 给 0.25
    # 加权: (0.40*45 + 0.25*15) / 60 = (18 + 3.75) / 60 = 0.3625
    abv = calculate_cocktail_abv(
        [("gin", 45.0), ("mystery liqueur", 15.0)],
        strength_data={"mystery liqueur": 0.25},
    )
    assert abv == pytest.approx(0.3625, abs=1e-3)


def test_fetch_iba_strength_data_direct_success(monkeypatch):
    """直连 GitHub 成功时返回解析后的 dict。"""
    from hermes_kb import ingredient_strength


    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"gin": 0.4, "vodka": 0.4, "broken": "not-a-number"}

    def fake_get(url, timeout):
        assert "raw.githubusercontent.com" in url
        assert "/master/" in url or "/main/" in url
        return FakeResp()

    monkeypatch.setattr(ingredient_strength.httpx, "get", fake_get)
    result = ingredient_strength.fetch_iba_strength_data()
    assert result == {"gin": 0.4, "vodka": 0.4}  # broken 被过滤


def test_fetch_iba_strength_data_local_fallback(monkeypatch):
    """直连+镜像失败时回退本地文件。"""
    from hermes_kb import ingredient_strength
    import httpx


    def fake_get(url, timeout):
        raise httpx.HTTPError("network down")

    # 不覆盖 Path.exists，让本地 data/iba_strength.json 真实存在
    monkeypatch.setattr(ingredient_strength.httpx, "get", fake_get)
    result = ingredient_strength.fetch_iba_strength_data()
    # 本地文件存在且非空
    assert isinstance(result, dict)
    assert len(result) > 0
    # vodka 之前是脏数据 0.0，清洗后应为 0.4
    assert result.get("vodka") == pytest.approx(0.4)
    # 重复键 red vermouth 应只出现一次（dict 自然去重）
    assert sum(1 for k in result if k == "red vermouth") == 1
    # 拼写错误的 worchestershire 应不存在
    assert "worchestershire sauce" not in result
    assert "worcestershire sauce" in result


def test_fetch_iba_strength_data_mirror_success(monkeypatch):
    """直连失败但 gh-proxy 镜像成功时返回镜像数据。"""
    from hermes_kb import ingredient_strength
    import httpx


    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"campari": 0.2}

    call_count = {"n": 0}

    def fake_get(url, timeout):
        call_count["n"] += 1
        # 直连 GitHub 的两次请求（master + main）都失败
        if "gh-proxy.com" not in url:
            raise httpx.HTTPError("direct blocked")
        # 镜像成功
        return FakeResp()

    monkeypatch.setattr(ingredient_strength.httpx, "get", fake_get)
    result = ingredient_strength.fetch_iba_strength_data()
    assert result == {"campari": 0.2}
    # 至少调用了 3 次（2 次直连 + 1 次镜像）
    assert call_count["n"] >= 3
