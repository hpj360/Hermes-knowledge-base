"""数据源注册表：加载、校验与查询。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"

# 合法取值
_VALID_TYPES = {"journal", "institution", "report", "reference"}
_VALID_ACCESS = {"api", "curated"}
_VALID_STATUS = {"active", "deprecated"}

# 必填字段
_REQUIRED_FIELDS = {
    "id",
    "name",
    "type",
    "authority_level",
    "accuracy_notes",
    "refresh_cadence_days",
    "last_verified",
    "license",
    "access",
    "import_adapter",
    "status",
}


class DataSourcesError(RuntimeError):
    """数据源注册表/接入错误。"""


def _load_raw() -> dict[str, dict[str, Any]]:
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise DataSourcesError("registry.json 顶层必须是对象")
    return data


def load_data_source_registry() -> dict[str, dict[str, Any]]:
    """按 id 索引加载数据源注册表。"""
    return _load_raw()


def get_source(source_id: str) -> dict[str, Any]:
    """按 id 返回数据源；不存在时抛出 DataSourcesError。"""
    reg = _load_raw()
    if source_id not in reg:
        raise DataSourcesError(f"未知数据源: {source_id}")
    return reg[source_id]


def validate_registry() -> list[str]:
    """校验注册表，返回问题列表（为空则通过）。

    - id 唯一且与键一致
    - 必填字段非空
    - type / access / status 取值合法
    - authority_level ∈ 1..5
    """
    reg = _load_raw()
    problems: list[str] = []
    for key, entry in reg.items():
        # 键与 id 一致
        if entry.get("id") != key:
            problems.append(f"{key}: id 与键不一致")
        # 必填字段
        for field in _REQUIRED_FIELDS:
            if field not in entry or entry[field] in (None, ""):
                problems.append(f"{key}: 缺少必填字段 {field}")
        # 枚举合法
        if entry.get("type") not in _VALID_TYPES:
            problems.append(f"{key}: 非法 type {entry.get('type')}")
        if entry.get("access") not in _VALID_ACCESS:
            problems.append(f"{key}: 非法 access {entry.get('access')}")
        if entry.get("status") not in _VALID_STATUS:
            problems.append(f"{key}: 非法 status {entry.get('status')}")
        # authority_level 范围
        lvl = entry.get("authority_level")
        if not isinstance(lvl, int) or not (1 <= lvl <= 5):
            problems.append(f"{key}: authority_level 需为 1..5 整数")
    # 键唯一性
    if len(reg) != len({e.get("id") for e in reg.values()}):
        problems.append("存在重复 id")
    return problems
