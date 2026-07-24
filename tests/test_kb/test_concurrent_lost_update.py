"""P2-1 并发 lost-update 回归测试。

验证 SQLite WAL 模式下并发更新同一记录时的行为：
1. 并发标题更新——最终值是两个写入之一，不损坏
2. 并发状态转换——状态机不双提交（draft→pending 仅一次成功）
3. 并发分类更新——last-write-wins，最终值一致且不损坏

设计要点：
- SQLite WAL + busy_timeout=5000 串行化写入，避免 database is locked
- 每个线程独立 session（SQLModel session 不跨线程共享）
- 乐观锁未实现时，lost-update 是 SQLite 的固有行为；测试断言最终一致性而非防止丢失
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from hermes_kb.database import get_session
from hermes_kb.models import Document
from hermes_kb.recipe_crud import submit_recipe, create_recipe


def _create_test_doc(title: str = "并发测试文档", category: str = "烈酒") -> str:
    """创建一个测试文档，返回 doc_id。"""
    with get_session() as session:
        doc = Document(
            title=title,
            content="测试内容",
            source_type="local",
            file_type="txt",
            category=category,
            chunk_count=1,
        )
        session.add(doc)
        session.commit()
        return doc.doc_id


def _update_title(doc_id: str, new_title: str) -> str:
    """更新文档标题，返回更新后的值。"""
    with get_session() as session:
        doc = session.get(Document, doc_id)
        if doc:
            doc.title = new_title
            session.add(doc)
            session.commit()
            return doc.title
        return ""


def _update_category(doc_id: str, new_category: str) -> str:
    """更新文档分类，返回更新后的值。"""
    with get_session() as session:
        doc = session.get(Document, doc_id)
        if doc:
            doc.category = new_category
            session.add(doc)
            session.commit()
            return doc.category
        return ""


def test_concurrent_title_update_no_corruption(tmp_db):
    """1. 两个线程并发更新同一文档标题 → 最终值是两者之一，不损坏。"""
    doc_id = _create_test_doc(title="原始标题")

    titles = ["线程A更新", "线程B更新"]
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_update_title, doc_id, t)
            for t in titles
        ]
        results = [f.result() for f in as_completed(futures)]

    # 最终标题是两个值之一（last-write-wins），不是空或损坏
    with get_session() as session:
        doc = session.get(Document, doc_id)
        assert doc.title in titles, (
            f"标题损坏：期望 {titles} 之一，实际 '{doc.title}'"
        )


def test_concurrent_category_update_no_corruption(tmp_db):
    """2. 多线程并发更新同一文档分类 → 最终值是写入值之一，不损坏。"""
    doc_id = _create_test_doc(category="烈酒")

    categories = ["葡萄酒", "啤酒", "中国白酒", "利口酒"]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_update_category, doc_id, c)
            for c in categories
        ]
        results = [f.result() for f in as_completed(futures)]

    # 最终分类是写入值之一
    with get_session() as session:
        doc = session.get(Document, doc_id)
        assert doc.category in categories, (
            f"分类损坏：期望 {categories} 之一，实际 '{doc.category}'"
        )


def test_concurrent_recipe_submit_no_double_transition(tmp_db):
    """3. 两个线程并发提交同一配方（draft→pending）→ 仅一次成功，不双提交。"""
    result = create_recipe(
        title="并发提交测试配方",
        ingredients=["金酒", "汤力水"],
        content="将金酒和汤力水混合。",
    )
    doc_id = result["doc_id"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(submit_recipe, doc_id)
        f2 = executor.submit(submit_recipe, doc_id)
        r1 = f1.result()
        r2 = f2.result()

    # 恰好一次成功（状态机保护：draft→pending 后第二次找不到 draft 状态）
    successes = sum([r1, r2])
    assert successes == 1, (
        f"期望恰好 1 次成功，实际 {successes} 次（r1={r1}, r2={r2}）"
    )

    # 最终状态是 pending（不是 published 或其他）
    with get_session() as session:
        doc = session.get(Document, doc_id)
        assert doc.status == "pending", (
            f"期望状态 pending，实际 '{doc.status}'"
        )


def test_concurrent_mixed_field_update_consistency(tmp_db):
    """4. 并发更新不同字段 → 两个字段都更新成功，互不覆盖。"""
    doc_id = _create_test_doc(title="原始", category="烈酒")

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(_update_title, doc_id, "新标题")
        f2 = executor.submit(_update_category, doc_id, "葡萄酒")
        as_completed([f1, f2])
        f1.result()
        f2.result()

    with get_session() as session:
        doc = session.get(Document, doc_id)
        # 两个不同字段的并发更新应都生效（SQLite 行级锁串行化）
        assert doc.title == "新标题", f"标题未更新：'{doc.title}'"
        assert doc.category == "葡萄酒", f"分类未更新：'{doc.category}'"
