"""Task 5.5：检查配方图片覆盖率。"""
from dotenv import load_dotenv

load_dotenv()

from collections import defaultdict
from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document


def check_coverage() -> None:
    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.category == "recipe")
        ).all()

        total = len(docs)
        with_img = len([d for d in docs if d.image_url])

        by_source: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "with_img": 0}
        )
        for d in docs:
            src = d.source or "unknown"
            by_source[src]["total"] += 1
            if d.image_url:
                by_source[src]["with_img"] += 1

        print(f"Total recipes: {total}")
        print(f"With image: {with_img} ({100 * with_img / total:.1f}%)")
        print(f"Without image: {total - with_img}")
        print("\nBy source:")
        for src, counts in sorted(by_source.items()):
            pct = 100 * counts["with_img"] / counts["total"] if counts["total"] else 0
            print(f"  {src}: {counts['total']} total, {counts['with_img']} with img ({pct:.1f}%)")


if __name__ == "__main__":
    check_coverage()
