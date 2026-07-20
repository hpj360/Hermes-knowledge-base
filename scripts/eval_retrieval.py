#!/usr/bin/env python3
"""检索质量评测脚本。

用法：
    python scripts/eval_retrieval.py [--eval-set PATH] [--top-k 3] [--seed-first]

工作流：
1. 重置数据库 → 导入种子数据
2. 对评测集每条 query 调用 HybridRetriever.retrieve()
3. 计算 top1 / top3 准确率
4. 对错误样例输出错误分析

判定规则：
- top1 命中：检索结果第 1 条的 doc title ∈ expected_doc_titles
- top3 命中：前 3 条中任一 doc title ∈ expected_doc_titles
- 关键词覆盖：前 3 条 chunk 文本包含 expected_keywords 的比例

注意：沙箱环境下 embedding=hash, llm=mock，结果为基线对照。
真实模型（bge-small-zh + GLM-4-Flash）应显著优于基线。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# 让脚本无需安装即可运行
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from hermes_kb.config import get_settings, reset_settings  # noqa: E402
from hermes_kb.database import get_engine  # noqa: E402
from hermes_kb.embedding import EmbeddingService  # noqa: E402
from hermes_kb.rag import ImportService  # noqa: E402
from hermes_kb.retrieval import HybridRetriever  # noqa: E402
from hermes_kb.seed import SEED_DOCS  # noqa: E402

from tests.eval import load_eval_set  # noqa: E402


def setup_db(db_path: Path) -> None:
    """重置数据库 + 导入种子。"""
    # 通过环境变量重定向 db
    import os

    os.environ["KB_DB_PATH"] = str(db_path)
    reset_settings()
    # 强制重新初始化引擎
    import hermes_kb.database as db_mod

    if db_mod._ENGINE is not None:
        db_mod._ENGINE.dispose()
        db_mod._ENGINE = None
    get_engine()  # 触发 schema 创建
    importer = ImportService()
    for doc in SEED_DOCS:
        importer.import_text(
            content=doc["content"],
            title=doc["title"],
            source_type="seed",
            file_type="md",
        )


def evaluate(top_k: int = 5, eval_set_path: Path | None = None) -> dict:
    """运行评测。

    返回：
        {
          "total", "top1_hit", "top3_hit", "top1_acc", "top3_acc",
          "keyword_coverage",
          "by_category": {cat: {"total", "top1_hit", "top3_hit"}},
          "errors": [{"id", "query", "expected", "got_top1", "got_top3"}],
          "config": {...}
        }
    """
    settings = get_settings()
    items = load_eval_set(eval_set_path)
    retriever = HybridRetriever()

    total = len(items)
    top1_hit = 0
    top3_hit = 0
    keyword_total = 0
    keyword_match = 0
    errors: list[dict] = []
    by_cat: dict[str, dict] = defaultdict(lambda: {"total": 0, "top1_hit": 0, "top3_hit": 0})

    for item in items:
        hits = retriever.retrieve(item.query, top_k=top_k)
        got_titles_top1 = [h.title for h in hits[:1]]
        got_titles_top3 = [h.title for h in hits[:3]]
        got_text_top3 = " ".join(h.text for h in hits[:3])

        is_top1 = any(t in item.expected_doc_titles for t in got_titles_top1)
        is_top3 = any(t in item.expected_doc_titles for t in got_titles_top3)
        if is_top1:
            top1_hit += 1
        if is_top3:
            top3_hit += 1

        # 关键词覆盖
        for kw in item.expected_keywords:
            keyword_total += 1
            if kw in got_text_top3:
                keyword_match += 1

        by_cat[item.category]["total"] += 1
        if is_top1:
            by_cat[item.category]["top1_hit"] += 1
        if is_top3:
            by_cat[item.category]["top3_hit"] += 1

        if not is_top3:
            errors.append({
                "id": item.id,
                "query": item.query,
                "expected": item.expected_doc_titles,
                "got_top1": got_titles_top1,
                "got_top3": got_titles_top3,
                "category": item.category,
            })

    return {
        "total": total,
        "top1_hit": top1_hit,
        "top3_hit": top3_hit,
        "top1_acc": round(top1_hit / total, 4) if total else 0.0,
        "top3_acc": round(top3_hit / total, 4) if total else 0.0,
        "keyword_coverage": round(keyword_match / keyword_total, 4) if keyword_total else 0.0,
        "by_category": {k: v for k, v in sorted(by_cat.items())},
        "errors_count": len(errors),
        "errors": errors[:20],  # 仅前 20 条，避免输出过长
        "config": {
            "embedding_provider": settings.embedding_provider,
            "embedding_available": settings.embedding_available,
            "llm_provider": settings.llm_provider,
            "llm_available": settings.llm_available,
            "min_score_threshold": settings.min_score_threshold,
            "top_k": settings.top_k,
            "rrf_k": settings.rrf_k,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="检索质量评测")
    parser.add_argument(
        "--eval-set", default=None, help="评测集 JSONL 路径（默认 tests/eval/eval_set.jsonl）"
    )
    parser.add_argument("--top-k", type=int, default=5, help="每次检索返回数")
    parser.add_argument(
        "--db-path", default=None, help="评测用数据库路径（默认临时文件）"
    )
    parser.add_argument(
        "--no-setup", action="store_true", help="跳过数据库初始化（使用现有库）"
    )
    args = parser.parse_args()

    import tempfile

    db_path = Path(args.db_path) if args.db_path else Path(tempfile.mkdtemp()) / "eval.db"

    if not args.no_setup:
        print(f"[setup] 初始化数据库: {db_path}", file=sys.stderr)
        setup_db(db_path)
        print(f"[setup] 已导入 {len(SEED_DOCS)} 篇种子文档", file=sys.stderr)

    print(f"[eval] 开始评测（top_k={args.top_k}）", file=sys.stderr)
    result = evaluate(top_k=args.top_k, eval_set_path=Path(args.eval_set) if args.eval_set else None)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(
        f"\n[summary] top1={result['top1_acc']:.2%} top3={result['top3_acc']:.2%} "
        f"kw_cov={result['keyword_coverage']:.2%}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
