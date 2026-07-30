#!/usr/bin/env python3
"""知识库综合质量审计脚本。

输出：文档总数、来源分布、类别分布、元数据覆盖率、空内容检测、IMA 富化率。
退出码：0 合格，1 质量问题。
"""
from __future__ import annotations

import json
import logging
import sys
import warnings
from pathlib import Path

# 抑制 alembic 迁移日志与 dev 模式 JWT 警告，保持审计输出整洁。
# alembic 在 run_migrations() 内会重配自身 logger，仅 setLevel 无效，
# 需用 logging.disable 全局压制 INFO 级别。
logging.disable(logging.INFO)
warnings.filterwarnings("ignore", message="KB_JWT_SECRET.*", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sqlmodel import func, select

from hermes_kb.database import get_session
from hermes_kb.models import Document

# IMA 富化标记（与 _enrich_ima_content.py 保持一致）
_ENRICHED_MARKER = "<!-- enriched -->"

# 评估集默认路径
_EVAL_SET_PATH = ROOT / "tests" / "eval" / "eval_set.jsonl"

# 短内容阈值（字符数）
_SHORT_CONTENT_THRESHOLD = 50

# 质量阈值
_META_THRESHOLDS = {
    "difficulty": 0.95,
    "season": 0.90,
    "technique": 0.60,
    "glassware": 0.70,
    "abv_bucket": 0.90,
}
_IMA_ENRICHMENT_THRESHOLD = 0.95
_EVAL_SET_MIN_COUNT = 180


def _load_meta(doc: Document) -> dict:
    """安全解析 doc.meta JSON，失败返回空 dict。"""
    if not doc.meta or doc.meta == "{}":
        return {}
    try:
        result = json.loads(doc.meta)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def audit_overview() -> dict:
    """文档总数、来源分布、类别分布。"""
    with get_session() as s:
        total = s.exec(select(func.count(Document.doc_id))).one()
        by_source: dict[str, int] = {}
        for source, count in s.exec(
            select(Document.source, func.count(Document.doc_id)).group_by(Document.source)
        ).all():
            by_source[source or "unknown"] = count
        by_category: dict[str, int] = {}
        for category, count in s.exec(
            select(Document.category, func.count(Document.doc_id)).group_by(Document.category)
        ).all():
            by_category[category or "unknown"] = count
    return {"total": total, "by_source": by_source, "by_category": by_category}


def audit_metadata_coverage() -> dict:
    """529 篇配方的 difficulty/season/abv_bucket/technique/glassware 覆盖率。

    覆盖判定：meta JSON 或列属性任一非空即视为已覆盖（与 _backfill_metadata.py
    双写策略一致）。
    """
    fields = ["difficulty", "season", "abv_bucket", "technique", "glassware"]
    with get_session() as s:
        recipes = s.exec(select(Document).where(Document.category == "recipe")).all()
    total = len(recipes)
    counts = {f: 0 for f in fields}
    for doc in recipes:
        meta = _load_meta(doc)
        for f in fields:
            value = meta.get(f) or getattr(doc, f, "") or ""
            if value:
                counts[f] += 1
    coverage = {f: (counts[f], total) for f in fields}
    return {"recipe_total": total, "coverage": coverage}


def audit_content_quality() -> dict:
    """空内容检测、短内容检测（<50 字）、IMA 富化率。"""
    with get_session() as s:
        docs = s.exec(select(Document)).all()
    empty_count = 0
    short_count = 0
    ima_total = 0
    ima_enriched = 0
    for doc in docs:
        content = doc.content or ""
        if not content:
            empty_count += 1
        elif len(content) < _SHORT_CONTENT_THRESHOLD:
            short_count += 1
        if doc.source == "ima":
            ima_total += 1
            if _ENRICHED_MARKER in content:
                ima_enriched += 1
    return {
        "empty_count": empty_count,
        "short_count": short_count,
        "ima_total": ima_total,
        "ima_enriched": ima_enriched,
    }


def audit_ima_quality() -> dict:
    """IMA 文档总数、富化数、hidden 数、重复数。

    重复数：非 hidden 文档中 (title, content) 指纹相同的额外篇数
    （已 hidden 的重复不计入，dedup 已处理的条目视为已治理）。
    """
    with get_session() as s:
        docs = s.exec(select(Document).where(Document.source == "ima")).all()
    total = len(docs)
    enriched = sum(1 for d in docs if _ENRICHED_MARKER in (d.content or ""))
    hidden = sum(1 for d in docs if d.hidden)
    visible = [d for d in docs if not d.hidden]
    groups: dict[tuple[str, str], int] = {}
    for d in visible:
        key = (d.title or "", d.content or "")
        groups[key] = groups.get(key, 0) + 1
    duplicates = sum(n - 1 for n in groups.values() if n > 1)
    return {"total": total, "enriched": enriched, "hidden": hidden, "duplicates": duplicates}


def audit_eval_set() -> dict:
    """评估集条目数、类别分布、JSONL 有效性。"""
    path = _EVAL_SET_PATH
    if not path.is_file():
        return {"total": 0, "valid": 0, "invalid": 0, "categories": {}, "exists": False}
    categories: dict[str, int] = {}
    valid = 0
    invalid = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                cat = obj.get("category", "")
                categories[cat] = categories.get(cat, 0) + 1
                valid += 1
            except (json.JSONDecodeError, TypeError):
                invalid += 1
    return {
        "total": valid + invalid,
        "valid": valid,
        "invalid": invalid,
        "categories": categories,
        "exists": True,
    }


def _fmt_pct(n: int, total: int) -> str:
    pct = (n / total * 100) if total else 0.0
    return f"{n}/{total} ({pct:.1f}%)"


def _check_threshold(n: int, total: int, threshold: float) -> bool:
    rate = (n / total) if total else 0.0
    return rate >= threshold


def main() -> int:
    overview = audit_overview()
    metadata = audit_metadata_coverage()
    content = audit_content_quality()
    ima = audit_ima_quality()
    eval_set = audit_eval_set()

    failures: list[str] = []

    print("=" * 40)
    print("知识库质量审计报告")
    print("=" * 40)

    # === 1. 文档总览 ===
    print("\n=== 1. 文档总览 ===")
    print(f"总文档数: {overview['total']}")
    print("按来源:")
    for source, count in sorted(overview["by_source"].items(), key=lambda x: -x[1]):
        print(f"  {source}: {count}")
    print("按类别:")
    for category, count in sorted(overview["by_category"].items(), key=lambda x: -x[1]):
        print(f"  {category}: {count}")

    # === 2. 配方元数据覆盖率 ===
    recipe_total = metadata["recipe_total"]
    print(f"\n=== 2. 配方元数据覆盖率 ({recipe_total} 篇) ===")
    for field in ["difficulty", "season", "abv_bucket", "technique", "glassware"]:
        covered, total = metadata["coverage"][field]
        threshold = _META_THRESHOLDS[field]
        ok = _check_threshold(covered, total, threshold)
        mark = "✅" if ok else "❌"
        print(f"{field}: {_fmt_pct(covered, total)} {mark}")
        if not ok:
            failures.append(f"{field} 覆盖率 {covered}/{total} 低于阈值 {threshold:.0%}")

    # === 3. 内容质量 ===
    print("\n=== 3. 内容质量 ===")
    empty_ok = content["empty_count"] == 0
    short_ok = content["short_count"] == 0
    # IMA 文档数为 0 时跳过富化率检查（IMA 同步需要单独 API 凭证，非 seed 流程必需）
    if content["ima_total"] > 0:
        ima_rate_ok = _check_threshold(
            content["ima_enriched"], content["ima_total"], _IMA_ENRICHMENT_THRESHOLD
        )
    else:
        ima_rate_ok = True  # 无 IMA 文档时跳过
    print(f"空内容: {content['empty_count']} {'✅' if empty_ok else '❌'}")
    print(f"短内容(<50字): {content['short_count']} {'✅' if short_ok else '❌'}")
    if content["ima_total"] > 0:
        print(
            f"IMA 富化率: {_fmt_pct(content['ima_enriched'], content['ima_total'])} "
            f"{'✅' if ima_rate_ok else '❌'}"
        )
    else:
        print("IMA 富化率: 跳过（无 IMA 文档） ⏭️")
    if not empty_ok:
        failures.append(f"空内容 {content['empty_count']} 篇（阈值 0）")
    if not short_ok:
        failures.append(f"短内容 {content['short_count']} 篇（阈值 0）")
    if not ima_rate_ok:
        failures.append(
            f"IMA 富化率 {content['ima_enriched']}/{content['ima_total']} "
            f"低于阈值 {_IMA_ENRICHMENT_THRESHOLD:.0%}"
        )

    # === 4. IMA 文档质量 ===
    print("\n=== 4. IMA 文档质量 ===")
    print(f"总数: {ima['total']}")
    print(f"已富化: {ima['enriched']}")
    print(f"hidden: {ima['hidden']}")
    print(f"重复: {ima['duplicates']}")

    # === 5. 评估集 ===
    print("\n=== 5. 评估集 ===")
    eval_ok = eval_set["valid"] >= _EVAL_SET_MIN_COUNT and eval_set["invalid"] == 0
    print(f"总条目数: {eval_set['valid']} {'✅' if eval_ok else '❌'}")
    if eval_set["invalid"] > 0:
        print(f"无效行: {eval_set['invalid']} ❌")
    if not eval_set["exists"]:
        print("⚠️  评估集文件不存在")
    print("类别分布:")
    for cat, count in sorted(eval_set["categories"].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    if not eval_ok:
        detail = f" 或存在 {eval_set['invalid']} 条无效 JSON" if eval_set["invalid"] else ""
        failures.append(
            f"评估集条目数 {eval_set['valid']} 低于阈值 {_EVAL_SET_MIN_COUNT}{detail}"
        )

    # === 审计结果 ===
    print("\n" + "=" * 40)
    if failures:
        print("审计结果: FAIL")
        print(f"不达标项 ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        print("=" * 40)
        return 1
    print("审计结果: PASS")
    print("=" * 40)
    return 0


if __name__ == "__main__":
    sys.exit(main())
