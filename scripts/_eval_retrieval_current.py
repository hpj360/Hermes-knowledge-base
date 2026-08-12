"""在当前数据库上运行检索评估，不重置数据。

用法：
    python scripts/_eval_retrieval_current.py [--top-k 3] [--sample 50]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# 必须加载 .env 以使用正确的 embedding provider（与数据库向量维度匹配）
from dotenv import load_dotenv

load_dotenv()

from hermes_kb.rag import HybridRetriever
from tests.eval import load_eval_set


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=3, help="Top-K 检索")
    parser.add_argument("--sample", type=int, default=0, help="抽样测试条数（0=全部）")
    parser.add_argument("--verbose", action="store_true", help="输出详细错误分析")
    args = parser.parse_args()

    eval_set = load_eval_set()
    if args.sample > 0:
        import random
        random.seed(42)
        eval_set = random.sample(eval_set, min(args.sample, len(eval_set)))

    print(f"评估集: {len(eval_set)} 条")
    print(f"Top-K: {args.top_k}")
    print()

    retriever = HybridRetriever()

    top1_hits = 0
    topk_hits = 0
    keyword_coverages: list[float] = []
    errors: list[dict] = []

    for i, item in enumerate(eval_set):
        query = item.query
        expected_titles = item.expected_doc_titles
        expected_keywords = item.expected_keywords

        try:
            results = retriever.retrieve(query, top_k=args.top_k)
        # 单条查询失败不中断整体评估，作为边界兜底静默记录
        except Exception as e:  # noqa: BLE001
            errors.append({"query": query, "error": str(e), "expected": expected_titles[0] if expected_titles else ""})
            continue

        # Top-1 命中
        top1_title = results[0].title if results else ""
        if top1_title in expected_titles:
            top1_hits += 1

        # Top-K 命中
        result_titles = [r.title for r in results]
        if any(t in result_titles for t in expected_titles):
            topk_hits += 1

        # 关键词覆盖
        if results and expected_keywords:
            top3_text = " ".join(r.text for r in results[:3])
            covered = sum(1 for kw in expected_keywords if kw in top3_text)
            coverage = covered / len(expected_keywords)
            keyword_coverages.append(coverage)

        # 记录错误
        if not any(t in result_titles for t in expected_titles):
            errors.append({
                "id": item.id,
                "query": query[:50],
                "expected": expected_titles[0][:40] if expected_titles else "",
                "got": [t[:40] for t in result_titles[:3]],
                "category": item.category,
            })

        if (i + 1) % 50 == 0:
            print(f"  进度: {i+1}/{len(eval_set)}")

    total = len(eval_set)
    top1_rate = top1_hits / total if total else 0
    topk_rate = topk_hits / total if total else 0
    avg_keyword = sum(keyword_coverages) / len(keyword_coverages) if keyword_coverages else 0

    print(f"\n{'=' * 60}")
    print("检索评估结果")
    print(f"{'=' * 60}")
    print(f"评估条数: {total}")
    print(f"Top-1 命中率: {top1_hits}/{total} ({top1_rate:.1%})")
    print(f"Top-{args.top_k} 命中率: {topk_hits}/{total} ({topk_rate:.1%})")
    print(f"关键词覆盖率: {avg_keyword:.1%}")
    print(f"未命中数: {len(errors)}")

    if args.verbose and errors:
        print("\n=== 错误分析（前 20 条）===")
        # 按类别分组
        from collections import Counter
        error_cats = Counter(e.get("category", "") for e in errors)
        print("未命中按类别:")
        for cat, n in error_cats.most_common():
            print(f"  {cat}: {n}")

        print("\n未命中样例:")
        for e in errors[:20]:
            print(f"  [{e.get('category', '')}] {e.get('query', '')}")
            print(f"    期望: {e.get('expected', '')}")
            print(f"    实际: {e.get('got', [])}")

    print(f"\n{'=' * 60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
