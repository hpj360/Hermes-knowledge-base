# -*- coding: utf-8 -*-
"""classify_abv_bucket 边界值测试。"""
from __future__ import annotations

import pytest

from hermes_kb.recipe_stats import classify_abv_bucket


@pytest.mark.parametrize(
    "abv, expected",
    [
        (0.0, "low"),
        (0.149, "low"),
        (0.15, "medium"),
        (0.249, "medium"),
        (0.25, "high"),
        (0.349, "high"),
        (0.35, "strong"),
        (0.5, "strong"),
        (-0.1, ""),
        (None, ""),
    ],
)
def test_classify_abv_bucket(abv, expected):
    """验证 ABV 边界值分类。"""
    assert classify_abv_bucket(abv) == expected
