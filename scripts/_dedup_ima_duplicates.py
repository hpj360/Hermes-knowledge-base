#!/usr/bin/env python3
"""IMA 重复文档标记脚本。

检测 IMA 同步引入的重复文档（相同标题 + 相同内容，不同 source_id），
保留每组最早创建的一篇，其余标记 hidden=True（不删除，可回滚）。

幂等：重复检测基于 (title, content) 指纹，已 hidden 的文档不重复标记。

用法：
    python scripts/_dedup_ima_duplicates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document


def main() -> int:
    with get_session() as s:
        docs = s.exec(select(Document).where(Document.source == "ima")).all()
        print(f"扫描 {len(docs)} 篇 IMA 文档...")

        # 按 (title, content) 指纹分组
        groups: dict[tuple[str, str], list[Document]] = {}
        for d in docs:
            key = (d.title or "", d.content or "")
            groups.setdefault(key, []).append(d)

        dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
        print(f"发现 {len(dup_groups)} 组重复文档")

        marked = 0
        already_hidden = 0
        for (title, _content), group in dup_groups.items():
            # 按 created_at 升序，保留最早一篇；其余标记 hidden
            group_sorted = sorted(group, key=lambda d: (d.created_at, d.doc_id))
            keep = group_sorted[0]
            hide = group_sorted[1:]
            print(f"\n标题: {title!r}")
            print(f"  保留: {keep.doc_id} (created={keep.created_at})")
            for d in hide:
                if d.hidden:
                    already_hidden += 1
                    print(f"  已隐藏: {d.doc_id}")
                    continue
                d.hidden = True
                s.add(d)
                marked += 1
                print(f"  标记隐藏: {d.doc_id} (source_id={d.source_id!r})")

        s.commit()

    print(f"\n标记完成：{marked} 篇新标记 hidden，{already_hidden} 篇已是 hidden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
