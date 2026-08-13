#!/usr/bin/env python3
"""外部数据收割编排脚本（Task 2）。

用法：
    python scripts/harvest_external_data.py [--source SOURCE] [--limit N] [--eval]

编排 TheCocktailDB / IBA dataset 的拉取，可选在收割后运行 eval 基线评估。

数据源：
- thecocktaildb: 调用 sync_thecocktaildb() 全量拉取（a-z + 0-9）
- iba_dataset:   调用 sync_iba_dataset() 拉取 IBA 官方配方（金标准 verified=True）
- all:           依次执行以上两个数据源

退出码：
- 0: 全部成功
- 1: 部分失败（某个数据源或 eval 抛出异常）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# 让脚本无需安装即可运行（参考 scripts/ 下其他脚本写法）
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from hermes_kb.data_sources import load_data_source_registry
from hermes_kb.data_sources.registry import get_adapter
from hermes_kb.iba_dataset_importer import sync_iba_dataset
from hermes_kb.rag import ImportService
from hermes_kb.retrieval import HybridRetriever
from hermes_kb.thecocktaildb_sync import sync_thecocktaildb
from tests.eval import load_eval_set

EVAL_SET_PATH = ROOT / "tests" / "eval" / "eval_set.jsonl"
BASELINE_PATH = ROOT / "tests" / "eval" / "baseline.json"

# 数据源注册表中的优质数据源（适配器接入）
QUALITY_SOURCE_IDS = [
    "wikidata",
    "crossref",
    "iwsr_summary",
    "who_alcohol",
    "oiv_stats",
    "niaaa_alcohol",
    "iba_official",
    "thecocktaildb",
    "wikipedia",
    "wikipedia_snapshot",
    "openfoodfacts",
    "usda_fooddata",
    "dbpedia",
]


def run_eval_baseline(top_k: int = 5) -> dict:
    """运行 eval 基线评估，写入 tests/eval/baseline.json 并返回结果。

    对 eval_set 中每条查询调用 HybridRetriever.retrieve()，计算：
    - recall_hit: 检索结果中包含 expected_doc_title 的查询数
    - keyword_hit: 检索结果中包含 expected_keywords 中任意关键词的查询数
    """
    items = load_eval_set(EVAL_SET_PATH)
    retriever = HybridRetriever()

    total = len(items)
    recall_hit = 0
    keyword_hit = 0

    for item in items:
        hits = retriever.retrieve(item.query, top_k=top_k)
        # recall: 检索结果中是否包含期望文档（按标题精确匹配）
        if any(h.title in item.expected_doc_titles for h in hits):
            recall_hit += 1
        # keyword: 检索结果文本中是否包含任意期望关键词
        if item.expected_keywords:
            joined_text = " ".join(h.text for h in hits)
            if any(kw in joined_text for kw in item.expected_keywords):
                keyword_hit += 1

    result = {
        "total": total,
        "recall_hit": recall_hit,
        "keyword_hit": keyword_hit,
        "recall_rate": round(recall_hit / total, 4) if total else 0.0,
        "keyword_rate": round(keyword_hit / total, 4) if total else 0.0,
        "harvested_at": datetime.now(timezone.utc).isoformat(),
    }

    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def harvest_quality_sources(
    importer: ImportService,
    source_ids: list[str] | None = None,
) -> dict:
    """通过数据源适配器编排优质数据源收割。

    对每个源调用 get_adapter(source_id).run(importer)，收集
    {imported, skipped, failed} 汇总；部分源失败不中断其他源。
    """
    ids = source_ids or QUALITY_SOURCE_IDS
    results: dict = {}
    for source_id in ids:
        try:
            results[source_id] = get_adapter(source_id).run(importer)
        except Exception as e:  # noqa: BLE001
            results[source_id] = {
                "error": str(e),
                "imported": 0,
                "skipped": 0,
                "failed": 0,
            }
            print(f"{source_id} 收割失败: {e}", file=sys.stderr)
    return results


def main() -> int:
    reg = load_data_source_registry()
    # --source 可选值：既有源 + 注册表优质源 + all + quality
    choices = ["thecocktaildb", "iba_dataset", "all", "quality"]
    choices.extend(reg)

    parser = argparse.ArgumentParser(description="外部数据收割编排")
    parser.add_argument(
        "--source",
        choices=choices,
        default="all",
        help="数据源（默认 all）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="TheCocktailDB 每个字母拉取上限（默认 500）",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="收割后运行 eval 基线评估",
    )
    args = parser.parse_args()

    importer = ImportService()
    results: dict = {}
    has_failure = False

    if args.source == "quality" or args.source in QUALITY_SOURCE_IDS:
        # 通过数据源适配器收割优质数据源
        if args.source == "quality":
            ids = QUALITY_SOURCE_IDS
        else:
            ids = [args.source]
        quality_results = harvest_quality_sources(importer, ids)
        results.update(quality_results)
        if any(r.get("error") for r in quality_results.values()):
            has_failure = True

    if args.source in ("thecocktaildb", "all"):
        try:
            results["thecocktaildb"] = sync_thecocktaildb(
                limit=args.limit, importer=importer
            )
        except (OSError, RuntimeError, ValueError, ConnectionError) as e:
            results["thecocktaildb"] = {
                "error": str(e),
                "imported": 0,
                "skipped": 0,
                "failed": 0,
            }
            print(f"TheCocktailDB 拉取失败: {e}", file=sys.stderr)
            has_failure = True

    if args.source in ("iba_dataset", "all"):
        try:
            results["iba_dataset"] = sync_iba_dataset(importer=importer)
        except (OSError, RuntimeError, ValueError, ConnectionError) as e:
            results["iba_dataset"] = {
                "error": str(e),
                "imported": 0,
                "skipped": 0,
                "failed": 0,
            }
            print(f"IBA dataset 拉取失败: {e}", file=sys.stderr)
            has_failure = True

    if args.eval:
        try:
            results["eval"] = run_eval_baseline()
        except (OSError, RuntimeError, ValueError, ConnectionError) as e:
            results["eval"] = {"error": str(e)}
            print(f"eval 基线运行失败: {e}", file=sys.stderr)
            has_failure = True

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
