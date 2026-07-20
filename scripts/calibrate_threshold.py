#!/usr/bin/env python3
"""阈值校准脚本（M2-02）。

用法：
    python scripts/calibrate_threshold.py [--eval-set PATH] [--min 0.001] [--max 0.05] [--step 0.001]

工作流：
1. 扫描一组 min_score_threshold 值
2. 对每个阈值跑评测集
3. 计算每个阈值的：
   - top1/top3 准确率
   - 召回率（未被判低置信度的比例）
   - F1（准确率 × 召回率 的调和平均）
4. 输出最优阈值 + 全量曲线

判定说明：
- 低置信度：所有 hits 的 score < threshold
- 召回率 = 未被判低置信度的样本数 / 总样本数
- 精确率 = top3 命中数 / 未判低置信度样本数
- F1 = 2 × P × R / (P + R)

注意：在 hash embedding 基线下，最优阈值可能与真实模型不同。
真实模型（bge-small-zh）应重新校准。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from hermes_kb.config import get_settings, reset_settings, override_settings  # noqa: E402
from hermes_kb.database import get_engine  # noqa: E402
from hermes_kb.rag import ImportService  # noqa: E402
from hermes_kb.retrieval import HybridRetriever  # noqa: E402
from hermes_kb.seed import SEED_DOCS  # noqa: E402

from tests.eval import load_eval_set  # noqa: E402


def setup_db(db_path: Path) -> None:
    os.environ["KB_DB_PATH"] = str(db_path)
    reset_settings()
    import hermes_kb.database as db_mod

    if db_mod._ENGINE is not None:
        db_mod._ENGINE.dispose()
        db_mod._ENGINE = None
    get_engine()
    importer = ImportService()
    for doc in SEED_DOCS:
        importer.import_text(
            content=doc["content"], title=doc["title"],
            source_type="seed", file_type="md",
        )


def evaluate_threshold(retriever: HybridRetriever, threshold: float, items) -> dict:
    """评估给定阈值下的 P/R/F1。"""
    total = len(items)
    top1_hit = 0
    top3_hit = 0
    not_low_conf = 0  # 未被判低置信度的样本数

    for item in items:
        hits = retriever.retrieve(item.query, top_k=5)
        is_low = all(h.score < threshold for h in hits) if hits else True
        if not is_low:
            not_low_conf += 1
            got_top1 = [h.title for h in hits[:1]]
            got_top3 = [h.title for h in hits[:3]]
            if any(t in item.expected_doc_titles for t in got_top1):
                top1_hit += 1
            if any(t in item.expected_doc_titles for t in got_top3):
                top3_hit += 1

    recall = not_low_conf / total if total else 0.0
    precision_top1 = top1_hit / not_low_conf if not_low_conf else 0.0
    precision_top3 = top3_hit / not_low_conf if not_low_conf else 0.0
    f1_top1 = (2 * precision_top1 * recall / (precision_top1 + recall)) if (precision_top1 + recall) > 0 else 0.0
    f1_top3 = (2 * precision_top3 * recall / (precision_top3 + recall)) if (precision_top3 + recall) > 0 else 0.0

    return {
        "threshold": threshold,
        "not_low_conf": not_low_conf,
        "recall": round(recall, 4),
        "top1_hit": top1_hit,
        "top3_hit": top3_hit,
        "precision_top1": round(precision_top1, 4),
        "precision_top3": round(precision_top3, 4),
        "f1_top1": round(f1_top1, 4),
        "f1_top3": round(f1_top3, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="阈值校准")
    parser.add_argument("--eval-set", default=None)
    parser.add_argument("--min", type=float, default=0.001, help="起始阈值")
    parser.add_argument("--max", type=float, default=0.05, help="结束阈值")
    parser.add_argument("--step", type=float, default=0.002, help="步长")
    args = parser.parse_args()

    db_path = Path(tempfile.mkdtemp()) / "calib.db"
    print(f"[setup] 初始化数据库: {db_path}", file=sys.stderr)
    setup_db(db_path)

    items = load_eval_set(Path(args.eval_set) if args.eval_set else None)
    retriever = HybridRetriever()

    # 扫描阈值
    thresholds = []
    t = args.min
    while t <= args.max + 1e-9:
        thresholds.append(round(t, 4))
        t += args.step

    print(f"[calibrate] 扫描 {len(thresholds)} 个阈值: {thresholds[0]}~{thresholds[-1]}", file=sys.stderr)
    results = []
    for th in thresholds:
        r = evaluate_threshold(retriever, th, items)
        results.append(r)
        print(
            f"  th={th:.4f}  recall={r['recall']:.2%}  "
            f"P_top3={r['precision_top3']:.2%}  F1_top3={r['f1_top3']:.4f}",
            file=sys.stderr,
        )

    # 找 F1_top3 最优
    best = max(results, key=lambda r: r["f1_top3"])
    print(
        f"\n[best] threshold={best['threshold']}  "
        f"F1_top3={best['f1_top3']:.4f}  recall={best['recall']:.2%}  "
        f"P_top3={best['precision_top3']:.2%}",
        file=sys.stderr,
    )

    output = {
        "best": best,
        "curve": results,
        "config": {
            "embedding_provider": get_settings().embedding_provider,
            "embedding_available": get_settings().embedding_available,
        },
        "recommendation": (
            f"建议将 KB_MIN_SCORE 设为 {best['threshold']} "
            f"（F1_top3={best['f1_top3']:.4f}）"
        ),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
