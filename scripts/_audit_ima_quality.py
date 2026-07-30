#!/usr/bin/env python3
"""IMA 文档内容质量审计脚本。

对 607 篇 IMA 富化后的文档进行分层抽样 30 篇，
检查内容长度、标题相关性、富化标记、结构完整性等质量维度，
识别低质量条目并输出审计报告。

用法：
    $env:KB_EMBEDDING_PROVIDER="hash"
    python scripts/_audit_ima_quality.py
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document

_ENRICHED_MARKER = "<!-- enriched -->"

# 酒类关键词（与 _enrich_ima_content.py _ALCOHOL_KEYWORDS 保持一致）
_ALCOHOL_KEYWORDS = [
    "朗姆酒", "金酒", "伏特加", "龙舌兰", "威士忌", "白兰地", "白酒", "啤酒",
    "清酒", "梅酒", "黄酒", "鸡尾酒", "利口酒", "香槟", "味美思", "梅斯卡尔",
    "葡萄酒",
]


@dataclass
class SampledDoc:
    """抽样文档元数据。"""
    doc_id: str
    title: str
    content: str
    layer: str


@dataclass
class QualityIssue:
    """质量问题。"""
    doc_id: str
    title: str
    layer: str
    issues: list[str] = field(default_factory=list)


def _categorize_layer(title: str) -> str:
    """根据标题推断分层类别。"""
    t = title or ""
    if "葡萄" in t and "葡萄酒" not in t:
        return "葡萄品种"
    if "产区" in t:
        return "产区"
    if "葡萄酒" in t:
        return "葡萄酒类型"
    if "果酒" in t:
        return "果酒"
    if any(k in t for k in _ALCOHOL_KEYWORDS):
        return "酒类知识"
    if "酒博士" in t or "发布稿" in t or "方法论" in t:
        return "行业报告"
    return "其他"


def _extract_keywords(title: str) -> list[str]:
    """从标题提取关键词用于内容相关性检查。"""
    # 清理常见分隔符
    cleaned = re.sub(r"[·_\-\|/\\]", " ", title)
    # 去除版本号
    cleaned = re.sub(r"v\d+\.\d+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\d{4}", "", cleaned)
    # 中文 + 英文 token
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", cleaned)
    # 过滤通用词
    stop = {"通用端", "知识", "酒博士", "MAS", "IMA", "发布稿", "方法论", "本文档", "标题"}
    return [t for t in tokens if t not in stop]


def _check_doc(doc: SampledDoc) -> QualityIssue:
    """检查单篇文档质量，返回问题列表。"""
    issues: list[str] = []
    content = doc.content or ""
    title = doc.title or ""

    # 1. 内容长度
    if len(content) < 100:
        issues.append(f"内容过短({len(content)}字)")

    # 2. 富化标记
    if _ENRICHED_MARKER not in content:
        issues.append("缺少富化标记")

    # 3. 结构完整性：# 标题行 / 来源类型行 / 类别行
    has_title_header = bool(re.search(r"^#\s+.+", content, re.MULTILINE))
    if not has_title_header:
        issues.append("缺少#标题行")
    if "来源类型" not in content:
        issues.append("缺少来源类型行")
    if "类别" not in content:
        issues.append("缺少类别行")

    # 4. 标题相关性：标题核心关键词应出现在内容中
    keywords = _extract_keywords(title)
    missing_kw = [kw for kw in keywords if kw not in content]
    # 允许部分关键词缺失（标题可能含通用词），但全部缺失视为低质量
    if missing_kw and len(missing_kw) == len(keywords):
        issues.append(f"关键词未匹配({missing_kw[:3]})")

    # 5. 明显错误描述或机器生成痕迹
    bad_patterns = [
        (r"TODO", "含TODO"),
        (r"FIXME", "含FIXME"),
        (r"placeholder", "含占位符"),
        (r"lorem ipsum", "含占位文本"),
    ]
    for pat, desc in bad_patterns:
        if re.search(pat, content, re.IGNORECASE):
            issues.append(desc)

    # 6. 标题清理错误（· 分隔符处理不当导致内容含明显错误标题）
    # 检查通用富化是否输出了未清理的多段标题
    if "本文档标题为「" in content:
        m = re.search(r"本文档标题为「(.+?)」", content)
        if m:
            embedded_title = m.group(1)
            # 如果嵌入的"标题"其实是整个原始多段标题，说明清理失败
            if embedded_title.count("·") >= 3:
                issues.append("标题清理错误(·分隔符未清理)")

    return QualityIssue(
        doc_id=doc.doc_id,
        title=title,
        layer=doc.layer,
        issues=issues,
    )


def _stratified_sample(seed: int = 42) -> list[SampledDoc]:
    """分层抽样 30 篇文档。"""
    import random
    random.seed(seed)

    with get_session() as s:
        # 仅审计可见文档（hidden=False）；hidden 文档为已标记的重复/低质量条目
        all_docs = s.exec(select(Document).where(Document.source == "ima")).all()
        docs = [d for d in all_docs if not d.hidden]
        print(f"总 IMA 文档数: {len(all_docs)}（其中 {len(all_docs) - len(docs)} 篇已标记 hidden）")
        print(f"参与抽样: {len(docs)} 篇可见文档")

        # 分层
        layers: dict[str, list[Document]] = {
            "葡萄品种": [],
            "产区": [],
            "葡萄酒类型": [],
            "果酒": [],
            "酒类知识": [],
            "行业报告": [],
            "其他": [],
        }
        for d in docs:
            layer = _categorize_layer(d.title or "")
            layers[layer].append(d)

        # 打印分层分布
        print("\n分层分布:")
        for name, lst in layers.items():
            print(f"  {name}: {len(lst)}")

        # 抽样：每层最多 5 篇，总数目标 30
        # 调整：行业报告/其他可适当多取，确保覆盖
        sampled: list[SampledDoc] = []
        target_per_layer = {
            "葡萄品种": 5,
            "产区": 5,
            "葡萄酒类型": 5,
            "果酒": 5,
            "酒类知识": 5,
            "行业报告": 5,
            "其他": 0,
        }
        # 如果某些层不足，从行业报告/其他补足到 30
        total_target = 30
        allocated = 0
        layer_samples: dict[str, list[Document]] = {}
        for layer, docs_in_layer in layers.items():
            n = min(target_per_layer.get(layer, 0), len(docs_in_layer))
            layer_samples[layer] = random.sample(docs_in_layer, n) if n > 0 else []
            allocated += n

        # 补足到 30
        if allocated < total_target:
            remaining = total_target - allocated
            # 从其他层补
            pool = layers["行业报告"] + layers["其他"]
            pool = [d for d in pool if d not in [sd for sl in layer_samples.values() for sd in sl]]
            extra = min(remaining, len(pool))
            if extra > 0:
                layer_samples.setdefault("行业报告", []).extend(random.sample(pool, extra))
                allocated += extra

        for layer, ds in layer_samples.items():
            for d in ds:
                sampled.append(SampledDoc(
                    doc_id=d.doc_id,
                    title=d.title or "",
                    content=d.content or "",
                    layer=layer,
                ))

        print(f"\n抽样数: {len(sampled)}")
        layer_count = Counter(d.layer for d in sampled)
        for layer, n in layer_count.items():
            print(f"  {layer}: {n}")

        return sampled


def _check_duplicates(sampled: list[SampledDoc]) -> dict[str, list[str]]:
    """检测重复内容（同一内容出现多次）。"""
    content_to_ids: dict[str, list[str]] = {}
    for d in sampled:
        # 取内容的前 200 字符作为指纹（去除元数据头部）
        fingerprint = (d.content or "")[:200]
        content_to_ids.setdefault(fingerprint, []).append(d.doc_id)
    return {k: v for k, v in content_to_ids.items() if len(v) > 1}


def main() -> int:
    sampled = _stratified_sample(seed=42)
    if len(sampled) < 30:
        print(f"警告：仅抽样到 {len(sampled)} 篇（目标 30）")

    # 质量检查
    issues_list = [_check_doc(d) for d in sampled]

    # 重复检测
    duplicates = _check_duplicates(sampled)
    if duplicates:
        for doc_ids in duplicates.values():
            for doc_id in doc_ids:
                for issue in issues_list:
                    if issue.doc_id == doc_id and "重复内容" not in issue.issues:
                        issue.issues.append(f"重复内容(共{len(doc_ids)}篇)")

    # 统计
    low_quality = [i for i in issues_list if i.issues]
    passed = [i for i in issues_list if not i.issues]

    print("\n=== IMA 内容质量审计报告 ===")
    print(f"抽样数: {len(sampled)}")
    print(f"合格: {len(passed)}")
    print(f"低质量: {len(low_quality)}")

    print("\n低质量条目详情:")
    if low_quality:
        for issue in low_quality:
            print(f"- {issue.doc_id} [{issue.layer}] {issue.title}:")
            for desc in issue.issues:
                print(f"    · {desc}")
    else:
        print("  (无)")

    # 重复内容统计
    if duplicates:
        print("\n重复内容组:")
        for i, (fp, ids) in enumerate(duplicates.items(), 1):
            print(f"  组{i}: {len(ids)}篇 - {ids}")
            print(f"    指纹: {fp[:80]}...")

    # 按问题类型统计
    print("\n问题类型统计:")
    type_count: Counter = Counter()
    for issue in low_quality:
        for desc in issue.issues:
            # 提取问题类型（括号前的关键词）
            ptype = re.split(r"[（(]", desc)[0]
            type_count[ptype] += 1
    for ptype, count in type_count.most_common():
        print(f"  {ptype}: {count}")

    # 分层合格率
    print("\n分层合格率:")
    layer_total: Counter = Counter(d.layer for d in sampled)
    layer_pass: Counter = Counter(d.layer for d in sampled if not _check_doc(d).issues)
    for layer in sorted(layer_total.keys()):
        total = layer_total[layer]
        p = layer_pass[layer]
        rate = (p / total * 100) if total else 0
        print(f"  {layer}: {p}/{total} ({rate:.0f}%)")

    # 保存抽样结果到磁盘，便于后续修复
    out_path = ROOT / "scripts" / "_audit_ima_sample.json"
    import json
    audit_data = {
        "sampled": [
            {
                "doc_id": d.doc_id,
                "title": d.title,
                "layer": d.layer,
                "content_length": len(d.content),
                "content_preview": d.content[:500],
            }
            for d in sampled
        ],
        "issues": [
            {
                "doc_id": i.doc_id,
                "title": i.title,
                "layer": i.layer,
                "issues": i.issues,
            }
            for i in low_quality
        ],
        "duplicates": {k: v for k, v in duplicates.items()},
    }
    out_path.write_text(json.dumps(audit_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n详细审计数据已保存到: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
