"""阶段 A.6：初始化开发态 DB（同步种子配方）。

将 SEED_RECIPES 中的 57 款 IBA 配方同步导入开发态 SQLite DB。

幂等性：
- 通过 title 去重，已存在的配方跳过
- 不影响其他已有文档

使用方式：
    python scripts/_init_dev_db.py [--force]

环境变量：
    KB_DB_PATH：DB 路径（默认 .hermes_kb/hermes_kb.db）
    --force：先清空 category=recipe 的种子配方再导入
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 确保 src 目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化开发态 DB（同步种子配方）")
    parser.add_argument(
        "--force",
        action="store_true",
        help="先清空现有 seed 来源的 recipe 文档再导入",
    )
    args = parser.parse_args()

    from sqlmodel import select

    from hermes_kb.database import get_session, init_db
    from hermes_kb.models import Document
    from hermes_kb.rag import ImportService
    from hermes_kb.seed_recipes import SEED_RECIPES

    # 1. 初始化 DB schema（幂等）
    print("=== 初始化 DB schema ===")
    init_db()

    # 2. 可选清空
    if args.force:
        print("\n=== 清空现有 seed 来源 recipe 文档 ===")
        with get_session() as session:
            rows = session.exec(
                select(Document).where(
                    Document.category == "recipe",
                    Document.source == "seed",
                )
            ).all()
            count = len(rows)
            for r in rows:
                session.delete(r)
            session.commit()
        print(f"已删除 {count} 条 seed recipe 文档")

    # 3. 同步种子配方（幂等：按 title 去重）
    print(f"\n=== 同步种子配方（{len(SEED_RECIPES)} 款）===")
    importer = ImportService()
    seeded = 0
    skipped = 0
    failed = 0

    for recipe in SEED_RECIPES:
        with get_session() as session:
            existing = session.exec(
                select(Document).where(Document.title == recipe["title"])
            ).first()
            if existing:
                skipped += 1
                continue
        try:
            importer.import_text(
                content=recipe["content"],
                title=recipe["title"],
                source_type="seed",
                file_type="md",
                category="recipe",
                source="seed",
                verified=True,
                status="published",
            )
            seeded += 1
        except Exception as e:  # noqa: BLE001 — 软降级，不阻塞主流程
            failed += 1
            print(f"  ❌ 失败: {recipe['title']} → {e}")

    print("\n=== 同步结果 ===")
    print(f"  导入: {seeded}")
    print(f"  跳过: {skipped}")
    print(f"  失败: {failed}")

    # 4. 验证：统计 DB 中 recipe 总数
    print("\n=== DB 状态验证 ===")
    with get_session() as session:
        total_recipes = session.exec(
            select(Document).where(Document.category == "recipe")
        ).all()
        seed_recipes = [
            r for r in total_recipes if r.source == "seed"
        ]
        print(f"  DB 中 recipe 总数: {len(total_recipes)}")
        print(f"  其中 seed 来源: {len(seed_recipes)}")

        # 按来源统计
        by_source: dict[str, int] = {}
        for r in total_recipes:
            src = r.source or "(空)"
            by_source[src] = by_source.get(src, 0) + 1
        print(f"  按来源分布: {by_source}")

    print("\n✅ 开发态 DB 初始化完成")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
