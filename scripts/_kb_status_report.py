"""知识库综合状态报告：文档分布、内容质量、类别覆盖。"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document


def main() -> None:
    with get_session() as s:
        docs = s.exec(select(Document)).all()

    total = len(docs)
    print("=" * 60)
    print("知识库综合状态报告")
    print("=" * 60)
    print(f"\n总文档数: {total}")

    # 按来源
    by_source = Counter(d.source or "unknown" for d in docs)
    print("\n=== 按来源 ===")
    for src, n in by_source.most_common():
        print(f"  {src}: {n} ({n/total*100:.1f}%)")

    # 按类别
    by_cat = Counter(d.category or "unknown" for d in docs)
    print("\n=== 按类别 ===")
    for cat, n in by_cat.most_common():
        print(f"  {cat}: {n} ({n/total*100:.1f}%)")

    # 可见文档（非 hidden）
    visible = [d for d in docs if not d.hidden]
    hidden = [d for d in docs if d.hidden]
    print("\n=== 可见性 ===")
    print(f"  可见: {len(visible)} ({len(visible)/total*100:.1f}%)")
    print(f"  隐藏: {len(hidden)} ({len(hidden)/total*100:.1f}%)")

    # 内容长度分布
    lengths = [len(d.content or "") for d in visible]
    if lengths:
        avg = sum(lengths) // len(lengths)
        print("\n=== 内容长度（可见文档）===")
        print(f"  最短: {min(lengths)} 字符")
        print(f"  最长: {max(lengths)} 字符")
        print(f"  平均: {avg} 字符")
        print(f"  中位数: {sorted(lengths)[len(lengths)//2]} 字符")

        # 长度分布
        buckets = {"<100": 0, "100-500": 0, "500-1000": 0, "1000-2000": 0, ">2000": 0}
        for l in lengths:
            if l < 100:
                buckets["<100"] += 1
            elif l < 500:
                buckets["100-500"] += 1
            elif l < 1000:
                buckets["500-1000"] += 1
            elif l < 2000:
                buckets["1000-2000"] += 1
            else:
                buckets[">2000"] += 1
        print("  长度分布:")
        for bucket, n in buckets.items():
            print(f"    {bucket}: {n}")

    # IMA 文档富化情况
    ima_docs = [d for d in docs if d.source == "ima"]
    ima_enriched = sum(1 for d in ima_docs if "<!-- enriched -->" in (d.content or ""))
    ima_hidden = sum(1 for d in ima_docs if d.hidden)
    print("\n=== IMA 文档质量 ===")
    print(f"  总数: {len(ima_docs)}")
    print(f"  已富化: {ima_enriched} ({ima_enriched/len(ima_docs)*100:.1f}%)")
    print(f"  隐藏(__OLD): {ima_hidden}")

    # 配方元数据覆盖
    recipes = [d for d in docs if d.category == "recipe"]
    print(f"\n=== 配方元数据覆盖 ({len(recipes)} 篇) ===")
    fields = ["difficulty", "season", "abv_bucket", "technique", "glassware"]
    for field in fields:
        covered = 0
        for d in recipes:
            meta = json.loads(d.meta or "{}")
            value = meta.get(field) or getattr(d, field, "") or ""
            if value:
                covered += 1
        print(f"  {field}: {covered}/{len(recipes)} ({covered/len(recipes)*100:.1f}%)")

    # 评估集统计
    eval_path = ROOT / "tests" / "eval" / "eval_set.jsonl"
    if eval_path.is_file():
        lines = eval_path.read_text(encoding="utf-8").strip().split("\n")
        eval_cats = Counter()
        for line in lines:
            if line.strip():
                obj = json.loads(line)
                eval_cats[obj.get("category", "")] += 1
        print(f"\n=== 评估集 ({len(lines)} 条) ===")
        for cat, n in eval_cats.most_common():
            print(f"  {cat}: {n}")

    # IMA 文档按前缀分类
    ima_visible = [d for d in ima_docs if not d.hidden]
    prefix_cats = Counter()
    for d in ima_visible:
        title = d.title or ""
        if "_" in title:
            prefix = title.split("_")[0]
        else:
            prefix = "中文/其他"
        prefix_cats[prefix] += 1
    print(f"\n=== IMA 可见文档按前缀 ({len(ima_visible)} 篇) ===")
    for prefix, n in prefix_cats.most_common():
        print(f"  {prefix}: {n}")

    print(f"\n{'=' * 60}")
    print("报告完成")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
