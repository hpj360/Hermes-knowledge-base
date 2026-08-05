"""检查 IMA 文档内容质量。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document


def main() -> None:
    with get_session() as s:
        docs = s.exec(select(Document).where(Document.source == "ima")).all()

    print(f"Total IMA docs: {len(docs)}")
    empty = sum(1 for d in docs if not d.content)
    short = sum(1 for d in docs if d.content and len(d.content) < 50)
    print(f"Empty content: {empty}")
    print(f"Short content (<50 chars): {short}")

    print("\nSample contents (first 3):")
    for d in docs[:3]:
        print(f"--- {d.title[:40]} ---")
        print(d.content[:200] if d.content else "(empty)")
        print()

    # 按内容长度分布
    lengths = [len(d.content or "") for d in docs]
    if lengths:
        print(f"Content length - min: {min(lengths)}, max: {max(lengths)}, avg: {sum(lengths) // len(lengths)}")


if __name__ == "__main__":
    main()
