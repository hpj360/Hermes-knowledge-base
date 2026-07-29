"""V2-Task6：配方评分与调酒笔记服务。

UPSERT 语义：同一 (doc_id, user) 仅保留一条记录，再次评分/笔记更新原记录。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document, RecipeRating


def upsert_rating(
    doc_id: str,
    user: str,
    score: int | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """UPSERT 评分/笔记。

    - 同一 (doc_id, user) 仅保留一条记录
    - score 或 comment 任一非 None 即触发更新；二者皆 None 抛 ValueError
    - score=0 表示仅笔记无评分（合法值）
    - 仅 comment 提交时保留原 score 不变

    Args:
        doc_id: 配方 doc_id
        user: 用户标识（未启用认证为 "anonymous"）
        score: 0-5 星，None 表示不更新
        comment: 笔记内容，None 表示不更新

    Returns:
        {doc_id, user, score, comment, status}
    """
    if score is None and comment is None:
        raise ValueError("score 和 comment 不能同时为 None")

    if score is not None and (score < 0 or score > 5):
        raise ValueError(f"score 必须在 0-5 之间，当前: {score}")

    with get_session() as session:
        # 校验 doc_id 存在
        doc = session.get(Document, doc_id)
        if not doc:
            raise LookupError(f"配方不存在: {doc_id}")

        # 查找已有记录（UPSERT）
        stmt = select(RecipeRating).where(
            RecipeRating.doc_id == doc_id,
            RecipeRating.user == user,
        )
        existing = session.exec(stmt).first()

        if existing:
            # 更新：score/comment 仅在非 None 时覆盖
            if score is not None:
                existing.score = score
            if comment is not None:
                existing.comment = comment
            from hermes_kb.models import _now_utc
            existing.updated_at = _now_utc()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            result = {
                "doc_id": existing.doc_id,
                "user": existing.user,
                "score": existing.score,
                "comment": existing.comment,
                "status": "updated",
            }
        else:
            # 新建
            rating = RecipeRating(
                doc_id=doc_id,
                user=user,
                score=score if score is not None else 0,
                comment=comment if comment is not None else "",
            )
            session.add(rating)
            session.commit()
            session.refresh(rating)
            result = {
                "doc_id": rating.doc_id,
                "user": rating.user,
                "score": rating.score,
                "comment": rating.comment,
                "status": "created",
            }
        return result


def get_rating_summary(doc_id: str, current_user: str | None = None) -> dict[str, Any]:
    """获取配方评分摘要 + 笔记列表。

    Args:
        doc_id: 配方 doc_id
        current_user: 当前用户标识，提供时返回其个人评分/笔记（如有）

    Returns:
        {
            "doc_id": str,
            "average_score": float,  # 0.0-5.0，无评分时为 0.0
            "rating_count": int,     # 评分数（score > 0 计入）
            "note_count": int,       # 笔记数（comment 非空计入）
            "current_user_rating": {  # 当前用户评分，未登录或无评分时为 null
                "score": int,
                "comment": str,
                "updated_at": str,
            } | None,
            "notes": [               # 笔记列表（按 updated_at 倒序，最多 50 条）
                {"user": str, "score": int, "comment": str, "updated_at": str}
            ]
        }
    """
    with get_session() as session:
        # 校验 doc_id 存在
        doc = session.get(Document, doc_id)
        if not doc:
            raise LookupError(f"配方不存在: {doc_id}")

        # 平均分与评分人数（仅 score > 0 计入）
        avg_stmt = select(
            func.avg(RecipeRating.score).label("avg"),
            func.count(RecipeRating.id).label("cnt"),
        ).where(
            RecipeRating.doc_id == doc_id,
            RecipeRating.score > 0,
        )
        row = session.exec(avg_stmt).one()
        avg_score = float(row.avg or 0.0)
        rating_count = int(row.cnt or 0)

        # 全部记录（用于笔记列表 + 当前用户评分）
        all_stmt = select(RecipeRating).where(
            RecipeRating.doc_id == doc_id,
        ).order_by(RecipeRating.updated_at.desc())
        all_ratings = session.exec(all_stmt).all()

        # 笔记数（comment 非空）
        note_count = sum(1 for r in all_ratings if r.comment and r.comment.strip())

        # 当前用户评分
        current_user_rating: dict[str, Any] | None = None
        if current_user:
            for r in all_ratings:
                if r.user == current_user:
                    current_user_rating = {
                        "score": r.score,
                        "comment": r.comment,
                        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                    }
                    break

        # 笔记列表（comment 非空，按 updated_at 倒序，最多 50 条）
        notes = [
            {
                "user": r.user,
                "score": r.score,
                "comment": r.comment,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in all_ratings
            if r.comment and r.comment.strip()
        ][:50]

        return {
            "doc_id": doc_id,
            "average_score": round(avg_score, 2),
            "rating_count": rating_count,
            "note_count": note_count,
            "current_user_rating": current_user_rating,
            "notes": notes,
        }
