#!/usr/bin/env python3
"""数据源质量验证脚本。

校验维度：
1. 来源合法值 —— DB 中 source 取值与注册表 id / 已知存量取值一致
2. 溯源完整性 —— 优质源文档的 source_authority/url/refreshed_at/license 四字段齐全
3. 时效性 —— source_refreshed_at 未超过 refresh_cadence_days
4. 去重 —— 同一来源内标题无重复
5. 模式一致性 —— registry.json 通过 validate_registry()

退出码：0 通过，1 存在问题。
"""
from __future__ import annotations

import logging
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

logging.disable(logging.INFO)
warnings.filterwarnings("ignore", message="KB_JWT_SECRET.*", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sqlmodel import select  # noqa: E402

from hermes_kb.data_sources import (  # noqa: E402
    load_data_source_registry,
    validate_registry,
)
from hermes_kb.database import get_session  # noqa: E402
from hermes_kb.models import Document  # noqa: E402

# 注册表未覆盖但已知合法的存量 source 值
_LEGACY_SOURCES = {
    "local",
    "upload",
    "seed",
    "ima",
    "iba",
    "user",
    "ugc",
    "obsidian",
    "ingredient_profile",
}

# 需要完整溯源的优质源（注册表中的 source_id）
_QUALITY_SOURCE_IDS = set(load_data_source_registry().keys())

# 溯源完整性的四要素
_PROVENANCE_FIELDS = [
    "source_authority",
    "source_url",
    "source_refreshed_at",
    "source_license",
]


def _fmt_pct(n: int, total: int) -> str:
    return f"{n}/{total} ({n / total * 100:.1f}%)" if total else "0/0 (0.0%)"


def main() -> int:
    failures: list[str] = []

    # === 1. 注册表模式一致性 ===
    reg_problems = validate_registry()
    if reg_problems:
        failures.append(f"registry.json 校验失败: {reg_problems}")
        for p in reg_problems:
            print(f"  - {p}")

    with get_session() as s:
        docs = s.exec(select(Document)).all()
        sources_in_db = {d.source for d in docs}

    # === 2. 来源合法值 ===
    legal = set(_LEGACY_SOURCES) | _QUALITY_SOURCE_IDS
    illegal = sorted(sources_in_db - legal)
    if illegal:
        failures.append(f"存在非注册表来源: {illegal}")

    # === 3. 溯源完整性（优质源文档） ===
    quality_docs = [d for d in docs if d.source in _QUALITY_SOURCE_IDS]
    missing_prov: list[str] = []
    for d in quality_docs:
        for f in _PROVENANCE_FIELDS:
            if not getattr(d, f, None):
                missing_prov.append(f"{d.doc_id}({d.title}) 缺 {f}")
    if missing_prov:
        failures.append(f"溯源不完整 {len(missing_prov)} 处")
        for m in missing_prov[:20]:
            print(f"  - {m}")

    # === 4. 时效性 ===
    now = datetime.now(timezone.utc)
    reg = load_data_source_registry()
    stale: list[str] = []
    for d in quality_docs:
        refreshed = d.source_refreshed_at
        if not refreshed:
            continue
        if refreshed.tzinfo is None:
            refreshed = refreshed.replace(tzinfo=timezone.utc)
        cadence = reg.get(d.source, {}).get("refresh_cadence_days", 730)
        age_days = (now - refreshed).days
        if age_days > cadence:
            stale.append(f"{d.title}（{d.source}，{age_days} 天 > {cadence} 天）")
    if stale:
        # 时效性为软告警（审计告警而非硬门禁）
        print("⚠️  过期数据源（软告警，不阻断）:")
        for st in stale[:20]:
            print(f"  - {st}")

    # === 5. 去重（注册表优质源内标题重复） ===
    # 仅校验注册表数据源：存量 IMA/seed 等历史数据存在已知重复，由各自去重工具治理，不在本源级校验范围。
    dup_titles: list[str] = []
    seen: dict[tuple[str, str], int] = {}
    for d in quality_docs:
        key = (d.source or "", d.title or "")
        seen[key] = seen.get(key, 0) + 1
    for (source, title), n in seen.items():
        if n > 1:
            dup_titles.append(f"{source}/{title} x{n}")
    if dup_titles:
        failures.append(f"来源内标题重复 {len(dup_titles)} 组")
        for dt in dup_titles[:20]:
            print(f"  - {dt}")

    # === 输出 ===
    print("=" * 40)
    print("数据源质量验证报告")
    print("=" * 40)
    print(f"文档总数: {len(docs)}")
    print(f"优质源文档数: {len(quality_docs)}")
    print(f"来源合法值校验: {'通过' if not (sources_in_db - legal) else '失败'}")
    print(
        f"溯源完整性: {_fmt_pct(len(quality_docs) - len(set(m.split('(')[0] for m in missing_prov)), len(quality_docs))}"
        if quality_docs
        else "溯源完整性: 无优质源文档"
    )
    print(f"去重校验: {'通过' if not dup_titles else f'{len(dup_titles)} 组重复'}")
    print("=" * 40)

    if failures:
        print("验证结果: FAIL")
        for f in failures:
            print(f"  - {f}")
        print("=" * 40)
        return 1
    print("验证结果: PASS")
    print("=" * 40)
    return 0


if __name__ == "__main__":
    sys.exit(main())
