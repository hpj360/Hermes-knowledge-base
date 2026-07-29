"""UGC 配方 CRUD + 审核状态机（M4.3 / V3-Task11）。

状态机：draft → pending → published / rejected
- draft: 用户编辑中，仅自己可见
- pending: 提交审核，进入审核队列
- published: 审核通过，进实验室匹配（verified=True）
- rejected: 审核驳回，附驳回理由；可 resubmit 回 draft 修订

V3-Task11 增强：
- author/reviewer 记录到 Document.meta JSON 字段
- resubmit_recipe：rejected → draft（作者修订后重新提交）
- list_my_recipes：按 author 筛选个人配方库
- 审核通知：基于 AuditLog 查询
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text as sa_text
from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document, _gen_doc_id, _now_utc
from hermes_kb.rag import ImportService


def _read_meta(doc: Document) -> dict[str, Any]:
    """安全读取 Document.meta JSON。"""
    try:
        return json.loads(doc.meta) if doc.meta else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _write_meta(doc: Document, meta: dict[str, Any]) -> None:
    """写入 Document.meta JSON。"""
    doc.meta = json.dumps(meta, ensure_ascii=False)


def create_recipe(
    title: str,
    ingredients: list[str],
    content: str,
    base_spirit: str = "",
    difficulty: str = "easy",
    season: str | None = None,
    importer: ImportService | None = None,
    author: str = "anonymous",
) -> dict[str, Any]:
    """创建 UGC 配方（draft 状态）。

    Args:
        importer: 可选的 ImportService 实例（由 router 通过 app.state 注入）。
                  为 None 时内部新建（保持向后兼容）。
        author: V3-Task11 创建者用户名（未启用认证时为 "anonymous"）。

    Returns:
        {doc_id, status, title}
    """
    importer = importer or ImportService()
    new_doc_id = _gen_doc_id()
    result = importer.import_text(
        content=content,
        title=title,
        source_type="ugc",
        file_type="md",
        doc_id=new_doc_id,
        category="recipe",
        source="ugc",
        source_id=f"ugc-{new_doc_id}",
        verified=False,
        status="draft",
        season=season,
    )
    # V3-Task11: author 写入 meta（不新增数据库字段，向后兼容）
    # import_text 不支持 metadata 参数，故导入后单独更新 meta 字段
    meta = {"author": author}
    with get_session() as session:
        doc = session.get(Document, new_doc_id)
        if doc:
            doc.meta = json.dumps(meta, ensure_ascii=False)
            session.add(doc)
            session.commit()
    return {"doc_id": result.get("doc_id"), "status": "draft", "title": title}


def update_recipe(
    doc_id: str,
    title: str | None = None,
    ingredients: list[str] | None = None,
    content: str | None = None,
    season: str | None = None,
) -> bool:
    """编辑配方（仅 draft 状态可编辑）。

    注意：``ingredients`` 更新需重新分片，本函数不支持。调用方若传入非空
    ``ingredients`` 将被显式拒绝（抛 ValueError），避免"接受即丢弃"的契约陷阱
    （P2-2）。如需更新材料，应删除后重新 ``create_recipe``。
    """
    if ingredients:
        raise ValueError(
            "update_recipe 不支持更新 ingredients（需重新分片）；"
            "请删除后重新 create_recipe，或在 content 中更新材料 frontmatter"
        )
    with get_session() as session:
        doc = session.get(Document, doc_id)
        if not doc or doc.status != "draft":
            return False
        if title is not None:
            doc.title = title
        if content is not None:
            doc.content = content
        if season is not None:
            doc.season = season
        # 注意：ingredients 更新需重新分片，此处仅更新 content
        # 若需更新 ingredients，应重新 import_text
        session.add(doc)
        session.commit()
        return True


def submit_recipe(doc_id: str) -> bool:
    """提交审核（draft → pending）。

    用原子 SQL UPDATE WHERE status='draft' 消除读-改-写竞态，
    防止并发双提交（P2-1 同类问题：两个线程同时读到 draft 都返回 True）。
    """
    with get_session() as session:
        result = session.execute(
            sa_text(
                "UPDATE document SET status='pending' "
                "WHERE doc_id=:did AND status='draft'"
            ),
            {"did": doc_id},
        )
        session.commit()
        return result.rowcount > 0


def approve_recipe(doc_id: str, reviewer: str = "anonymous") -> bool:
    """审核通过（pending → published, verified=True）。

    V3-Task11: 记录 reviewer 和 reviewed_at 到 meta。
    """
    with get_session() as session:
        doc = session.get(Document, doc_id)
        if not doc or doc.status != "pending":
            return False
        doc.status = "published"
        doc.verified = True
        meta = _read_meta(doc)
        meta["reviewer"] = reviewer
        meta["reviewed_at"] = _now_utc().isoformat()
        _write_meta(doc, meta)
        session.add(doc)
        session.commit()
        return True


def reject_recipe(doc_id: str, reason: str = "", reviewer: str = "anonymous") -> bool:
    """审核驳回（pending → rejected）。

    V3-Task11: 记录 reviewer 和 reviewed_at 到 meta。
    """
    with get_session() as session:
        doc = session.get(Document, doc_id)
        if not doc or doc.status != "pending":
            return False
        doc.status = "rejected"
        doc.verified = False
        meta = _read_meta(doc)
        meta["reject_reason"] = reason
        meta["reviewer"] = reviewer
        meta["reviewed_at"] = _now_utc().isoformat()
        _write_meta(doc, meta)
        session.add(doc)
        session.commit()
        return True


def resubmit_recipe(doc_id: str) -> bool:
    """V3-Task11: 重新提交（rejected → draft）。

    作者修订被驳回的配方后，调用此函数回到 draft 状态，再 edit + submit。

    用原子 SQL UPDATE WHERE status='rejected' 消除读-改-写竞态。
    """
    with get_session() as session:
        result = session.execute(
            sa_text(
                "UPDATE document SET status='draft' "
                "WHERE doc_id=:did AND status='rejected'"
            ),
            {"did": doc_id},
        )
        session.commit()
        return result.rowcount > 0


def list_pending_recipes(limit: int = 20) -> list[dict[str, Any]]:
    """列出待审核配方。"""
    with get_session() as session:
        docs = session.exec(
            select(Document)
            .where(Document.category == "recipe", Document.status == "pending")
            .limit(limit)
        ).all()
        return [_recipe_summary(d) for d in docs]


def list_my_recipes(author: str, limit: int = 50) -> list[dict[str, Any]]:
    """V3-Task11: 列出当前用户的配方（个人配方库）。

    通过 meta JSON 中的 author 字段筛选。SQLite 的 json_extract 可提取嵌套值。
    未启用 multiuser 时 author="anonymous"，返回所有 UGC 配方。
    """
    with get_session() as session:
        # 用 json_extract 从 meta 中提取 author 字段
        stmt = (
            select(Document)
            .where(Document.category == "recipe")
            .where(Document.source == "ugc")
            .where(sa_text("json_extract(metadata, '$.author') = :author"))
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        docs = session.exec(stmt, params={"author": author}).all()
        return [_recipe_summary(d) for d in docs]


def get_recipe_author(doc_id: str) -> str:
    """V3-Task11: 获取配方作者（从 meta 读取）。

    用于权限校验（仅作者可编辑自己的 draft 配方）。
    """
    with get_session() as session:
        doc = session.get(Document, doc_id)
        if not doc:
            return ""
        meta = _read_meta(doc)
        return str(meta.get("author", "anonymous"))


def _recipe_summary(doc: Document) -> dict[str, Any]:
    """配方摘要信息（含 meta 中的 author/reviewer/reject_reason）。"""
    meta = _read_meta(doc)
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "source": doc.source,
        "status": doc.status,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "author": meta.get("author", "anonymous"),
        "reviewer": meta.get("reviewer", ""),
        "reviewed_at": meta.get("reviewed_at"),
        "reject_reason": meta.get("reject_reason", ""),
    }
