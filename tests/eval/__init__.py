"""评测集加载工具。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalItem:
    """单条评测样本。"""

    id: str
    query: str
    expected_doc_titles: list[str]
    expected_keywords: list[str]
    category: str


def load_eval_set(path: str | Path | None = None) -> list[EvalItem]:
    """加载评测集 JSONL。

    格式兼容单/多期望文档：
        {"id", "query", "expected_doc_title" | "expected_doc_titles", "expected_keywords", "category"}
    """
    if path is None:
        path = Path(__file__).parent / "eval_set.jsonl"
    path = Path(path)
    items: list[EvalItem] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            titles = obj.get("expected_doc_titles")
            if titles is None:
                single = obj.get("expected_doc_title", "")
                titles = [single] if single else []
            items.append(
                EvalItem(
                    id=obj["id"],
                    query=obj["query"],
                    expected_doc_titles=titles,
                    expected_keywords=obj.get("expected_keywords", []),
                    category=obj.get("category", ""),
                )
            )
    return items
