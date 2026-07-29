#!/usr/bin/env python3
"""RAG 评估自动化管线脚本。

用法：
    python scripts/run_eval.py [--eval-set PATH] [--baseline PATH] [--output-dir DIR]
                               [--top-k N] [--no-regression] [--verbose]
                               [--no-rewrite] [--hyde]

功能：
1. 读取评估集（tests/eval/eval_set.jsonl），对每题调用 HybridRetriever.retrieve()
2. 检索前可选应用查询改写（QueryRewriter）+ HyDE（假设文档生成）
3. 计算 recall_rate / keyword_rate / 延迟指标（avg / p95）
4. 与 baseline.json 对比，检测回归
5. 输出 JSON 报告（eval_report.json）+ Markdown 报告（eval_report.md）
6. recall_rate 低于基线时退出码 1（回归告警），--no-regression 可跳过

判定规则：
- recall_hit：检索结果中任一 hit 的 title 包含 expected_doc_title（或反向包含）
- keyword_hit：检索结果合并文本中是否包含任一 expected_keyword
  （与 baseline.json 生成语义一致，确保对比有效）
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# 让脚本无需安装即可运行
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# 项目记忆：config.py 不自动加载 .env，需手动加载
from dotenv import load_dotenv

load_dotenv()

from hermes_kb.config import get_settings  # noqa: E402
from hermes_kb.hyde import HyDEGenerator  # noqa: E402
from hermes_kb.query_rewriter import QueryRewriter  # noqa: E402
from hermes_kb.retrieval import HybridRetriever  # noqa: E402
from tests.eval import load_eval_set  # noqa: E402


def title_matches(hit_title: str, expected_titles: list[str]) -> bool:
    """检查 hit title 是否包含任一 expected title（或反向包含）。"""
    for exp in expected_titles:
        if not exp:
            continue
        if exp in hit_title or hit_title in exp:
            return True
    return False


def keywords_any_in_combined(hits_text: list[str], keywords: list[str]) -> bool:
    """检查合并后的检索文本中是否包含任一 keyword。

    与 baseline.json 生成语义一致（harvest_external_data.py run_eval_baseline）：
    将所有 hit 的 text 合并，检查是否包含 expected_keywords 中任意一个。
    """
    if not keywords:
        return False
    joined = " ".join(hits_text)
    return any(kw in joined for kw in keywords)


def compute_p95(data: list[float]) -> float:
    """使用 statistics 模块计算 p95。

    quantiles(data, n=100) 返回 99 个分位点（p1..p99），index 94 = p95。
    """
    if not data:
        return 0.0
    if len(data) < 2:
        return data[0]
    qs = statistics.quantiles(data, n=100, method="inclusive")
    return qs[94]


def load_baseline(path: Path) -> dict | None:
    """加载基线文件，失败返回 None。"""
    if not path.exists():
        print(f"[warn] 基线文件不存在: {path}", file=sys.stderr)
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[warn] 基线文件解析失败: {exc}", file=sys.stderr)
        return None


def run_evaluation(
    eval_set_path: Path,
    top_k: int,
    verbose: bool,
    rewrite_enabled: bool,
    hyde_enabled: bool,
) -> tuple[dict, list[dict], dict[str, dict]]:
    """运行评估，返回 (summary, details, by_category)。

    检索流程：
    1. （可选）查询改写：rewriter.rewrite(query)
    2. （可选）HyDE：hyde_generator.generate(query)，用假设文档替换检索 query
    3. HybridRetriever.retrieve(retrieval_query)
    """
    items = load_eval_set(eval_set_path)
    if not items:
        print(f"[error] 评估集为空: {eval_set_path}", file=sys.stderr)
        sys.exit(2)

    settings = get_settings()
    retriever = HybridRetriever()
    # 查询改写器：默认启用（与 RAG 引擎行为一致），--no-rewrite 时跳过
    rewriter = QueryRewriter() if rewrite_enabled else None
    # HyDE 生成器：--hyde 或 KB_HYDE=true 时启用
    hyde_gen = HyDEGenerator() if hyde_enabled else None
    if hyde_gen is not None:
        # CLI --hyde 显式覆盖配置，强制启用
        hyde_gen.enabled = True

    total = len(items)
    recall_hit_count = 0
    keyword_hit_count = 0
    latencies: list[float] = []
    details: list[dict] = []
    by_category: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "recall_hit": 0, "keyword_hit": 0}
    )

    for i, item in enumerate(items, start=1):
        t0 = time.perf_counter()
        # 检索前处理：查询改写 + HyDE
        retrieval_query = item.query
        if rewriter is not None:
            try:
                retrieval_query = rewriter.rewrite(item.query)
            except Exception:  # noqa: BLE001 — 软降级，不阻塞主流程
                retrieval_query = item.query
        if hyde_gen is not None:
            hyde_doc = hyde_gen.generate(item.query)
            if hyde_doc and hyde_doc.strip():
                retrieval_query = hyde_doc
        hits = retriever.retrieve(retrieval_query, top_k=top_k)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(latency_ms)

        r_hit = any(title_matches(h.title, item.expected_doc_titles) for h in hits)
        k_hit = keywords_any_in_combined(
            [h.text for h in hits], item.expected_keywords
        )

        if r_hit:
            recall_hit_count += 1
        if k_hit:
            keyword_hit_count += 1

        top_hit_title = hits[0].title if hits else ""

        details.append(
            {
                "id": item.id,
                "query": item.query,
                "recall_hit": r_hit,
                "keyword_hit": k_hit,
                "latency_ms": round(latency_ms, 1),
                "top_hit_title": top_hit_title,
            }
        )

        by_category[item.category]["total"] += 1
        if r_hit:
            by_category[item.category]["recall_hit"] += 1
        if k_hit:
            by_category[item.category]["keyword_hit"] += 1

        if verbose:
            r_mark = "Y" if r_hit else "N"
            k_mark = "Y" if k_hit else "N"
            print(
                f"[{item.id}] query={item.query!r} recall={r_mark} keyword={k_mark} "
                f"latency={latency_ms:.1f}ms top={top_hit_title!r}",
                file=sys.stderr,
            )

        if i % 10 == 0 or i == total:
            print(f"[eval] {i}/{total}", file=sys.stderr)

    recall_rate = round(recall_hit_count / total, 4) if total else 0.0
    keyword_rate = round(keyword_hit_count / total, 4) if total else 0.0
    avg_latency = round(sum(latencies) / total, 1) if total else 0.0
    p95 = round(compute_p95(latencies), 1)

    summary = {
        "total": total,
        "recall_hit": recall_hit_count,
        "keyword_hit": keyword_hit_count,
        "recall_rate": recall_rate,
        "keyword_rate": keyword_rate,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95,
        "evaluated_at": datetime.now().isoformat(),
        "embedding_provider": settings.embedding_provider,
        "top_k": top_k,
        "query_rewrite": rewrite_enabled,
        "hyde": hyde_enabled,
    }

    return summary, details, dict(by_category)


def build_json_report(
    summary: dict,
    details: list[dict],
    baseline: dict | None,
    regression: bool,
) -> dict:
    """构建 JSON 报告。"""
    report = dict(summary)
    report["baseline"] = (
        {
            "recall_rate": baseline.get("recall_rate"),
            "keyword_rate": baseline.get("keyword_rate"),
        }
        if baseline
        else None
    )
    report["regression"] = regression
    report["details"] = details
    return report


def build_markdown_report(
    summary: dict,
    by_category: dict[str, dict],
    baseline: dict | None,
    regression: bool,
) -> str:
    """构建 Markdown 报告。"""
    b_recall = baseline.get("recall_rate") if baseline else None
    b_keyword = baseline.get("keyword_rate") if baseline else None

    def fmt_pct(v: float | None) -> str:
        return f"{v * 100:.1f}%" if v is not None else "-"

    def fmt_delta(cur: float, base: float | None) -> str:
        if base is None:
            return "-"
        return f"{(cur - base) * 100:+.1f}%"

    lines: list[str] = []
    lines.append("# RAG 评估报告")
    lines.append("")
    lines.append(f"**评估时间**: {summary['evaluated_at']}")
    lines.append(f"**Embedding Provider**: {summary['embedding_provider']}")
    lines.append(f"**Top-K**: {summary['top_k']}")
    lines.append(
        f"**Query Rewrite**: {'enabled' if summary.get('query_rewrite') else 'disabled'}"
    )
    lines.append(f"**HyDE**: {'enabled' if summary.get('hyde') else 'disabled'}")
    lines.append("")
    lines.append("## 汇总指标")
    lines.append("")
    lines.append("| 指标 | 当前 | 基线 | 变化 |")
    lines.append("|------|------|------|------|")
    lines.append(
        f"| Recall Rate | {fmt_pct(summary['recall_rate'])} | {fmt_pct(b_recall)} | "
        f"{fmt_delta(summary['recall_rate'], b_recall)} |"
    )
    lines.append(
        f"| Keyword Rate | {fmt_pct(summary['keyword_rate'])} | {fmt_pct(b_keyword)} | "
        f"{fmt_delta(summary['keyword_rate'], b_keyword)} |"
    )
    lines.append(f"| Avg Latency | {int(round(summary['avg_latency_ms']))}ms | - | - |")
    lines.append(f"| P95 Latency | {int(round(summary['p95_latency_ms']))}ms | - | - |")
    lines.append("")
    lines.append("## 按类别分组")
    lines.append("")
    lines.append("| 类别 | 题数 | Recall Hit | Keyword Hit |")
    lines.append("|------|------|-----------|------------|")
    for cat in sorted(by_category.keys()):
        c = by_category[cat]
        lines.append(
            f"| {cat} | {c['total']} | {c['recall_hit']} | {c['keyword_hit']} |"
        )
    lines.append("")
    lines.append("## 回归检测")
    lines.append("")
    if regression:
        lines.append(
            f"❌ 回归: recall_rate 从 {fmt_pct(b_recall)} 降至 "
            f"{fmt_pct(summary['recall_rate'])}"
        )
    else:
        lines.append("✅ 无回归")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG 评估自动化管线")
    parser.add_argument(
        "--eval-set",
        default="tests/eval/eval_set.jsonl",
        help="评估集 JSONL 路径（默认 tests/eval/eval_set.jsonl）",
    )
    parser.add_argument(
        "--baseline",
        default="tests/eval/baseline.json",
        help="基线 JSON 路径（默认 tests/eval/baseline.json）",
    )
    parser.add_argument(
        "--output-dir",
        default="tests/eval/",
        help="报告输出目录（默认 tests/eval/）",
    )
    parser.add_argument("--top-k", type=int, default=5, help="检索 top_k（默认 5）")
    parser.add_argument(
        "--no-regression",
        action="store_true",
        help="不检查回归（始终退出 0）",
    )
    parser.add_argument(
        "--no-rewrite",
        action="store_true",
        help="禁用查询改写（用于对比测试），默认启用改写（与 RAG 引擎一致）",
    )
    parser.add_argument(
        "--hyde",
        action="store_true",
        help="启用 HyDE 假设文档检索（默认跟随 KB_HYDE 配置，默认关闭）",
    )
    parser.add_argument("--verbose", action="store_true", help="输出每题详情")
    args = parser.parse_args()

    # 查询改写：默认启用，--no-rewrite 禁用
    rewrite_enabled = not args.no_rewrite
    # HyDE：--hyde 显式启用，否则跟随 KB_HYDE 配置
    hyde_enabled = args.hyde or get_settings().hyde_enabled

    # 相对路径基于项目根目录解析，保证从任意 CWD 运行均可
    eval_set_path = Path(args.eval_set)
    if not eval_set_path.is_absolute():
        eval_set_path = ROOT / eval_set_path
    baseline_path = Path(args.baseline)
    if not baseline_path.is_absolute():
        baseline_path = ROOT / baseline_path
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not eval_set_path.exists():
        print(f"[error] 评估集不存在: {eval_set_path}", file=sys.stderr)
        return 2

    baseline = load_baseline(baseline_path)

    print(f"[eval] 开始评估（top_k={args.top_k}）", file=sys.stderr)
    print(
        f"[eval] Query Rewrite: {'enabled' if rewrite_enabled else 'disabled'} | "
        f"HyDE: {'enabled' if hyde_enabled else 'disabled'}",
        file=sys.stderr,
    )
    summary, details, by_category = run_evaluation(
        eval_set_path, args.top_k, args.verbose, rewrite_enabled, hyde_enabled
    )

    # 回归检测：recall_rate 低于基线即为回归
    b_recall = baseline.get("recall_rate") if baseline else None
    regression = b_recall is not None and summary["recall_rate"] < b_recall

    # JSON 报告
    json_report = build_json_report(summary, details, baseline, regression)
    json_path = output_dir / "eval_report.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    print(f"[report] JSON 报告: {json_path}", file=sys.stderr)

    # Markdown 报告
    md_report = build_markdown_report(summary, by_category, baseline, regression)
    md_path = output_dir / "eval_report.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"[report] Markdown 报告: {md_path}", file=sys.stderr)

    # 汇总输出
    print(
        f"\n[summary] recall_rate={summary['recall_rate']:.4f} "
        f"keyword_rate={summary['keyword_rate']:.4f} "
        f"avg_latency={summary['avg_latency_ms']:.1f}ms "
        f"p95_latency={summary['p95_latency_ms']:.1f}ms",
        file=sys.stderr,
    )

    # 退出码：回归且未禁用检查时退出 1
    if regression and not args.no_regression:
        print(
            f"[regression] recall_rate 从 {b_recall:.4f} 降至 "
            f"{summary['recall_rate']:.4f}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
