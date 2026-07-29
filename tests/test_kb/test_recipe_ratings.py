"""V2-Task6: 配方评分与调酒笔记测试。"""
from __future__ import annotations

import pytest


@pytest.fixture
def recipe_doc(tmp_db):
    """创建一个测试配方 doc，返回 doc_id。"""
    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    with get_session() as session:
        doc = Document(title="测试配方", content="内容", category="recipe")
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc.doc_id


# ============================================================================
# 模型测试
# ============================================================================


def test_recipe_rating_model(tmp_db, recipe_doc):
    """RecipeRating 表可创建并写入（FK 约束要求 doc 必须存在）。"""
    from hermes_kb.database import get_session
    from hermes_kb.models import RecipeRating

    with get_session() as session:
        r = RecipeRating(
            doc_id=recipe_doc,
            user="alice",
            score=5,
            comment="非常好喝",
        )
        session.add(r)
        session.commit()
        session.refresh(r)
        assert r.id is not None
        assert r.doc_id == recipe_doc
        assert r.user == "alice"
        assert r.score == 5
        assert r.comment == "非常好喝"
        assert r.created_at is not None
        assert r.updated_at is not None


def test_recipe_rating_unique_constraint(tmp_db, recipe_doc):
    """(doc_id, user) 唯一约束：同一用户对同一配方只能一条记录。"""
    from sqlalchemy.exc import IntegrityError

    from hermes_kb.database import get_session
    from hermes_kb.models import RecipeRating

    with get_session() as session:
        r1 = RecipeRating(doc_id=recipe_doc, user="alice", score=4, comment="好")
        session.add(r1)
        session.commit()

        # 第二条 (doc_id, user) 相同应抛 IntegrityError
        r2 = RecipeRating(doc_id=recipe_doc, user="alice", score=5, comment="改主意了")
        session.add(r2)
        with pytest.raises(IntegrityError):
            session.commit()


def test_recipe_rating_cascade_on_doc_delete(tmp_db, recipe_doc):
    """doc 删除时级联删除其评分记录。"""
    from sqlmodel import select

    from hermes_kb.database import get_session
    from hermes_kb.models import Document, RecipeRating

    with get_session() as session:
        r = RecipeRating(doc_id=recipe_doc, user="alice", score=5, comment="好评")
        session.add(r)
        session.commit()

    with get_session() as session:
        doc = session.get(Document, recipe_doc)
        session.delete(doc)
        session.commit()

    with get_session() as session:
        ratings = session.exec(
            select(RecipeRating).where(RecipeRating.doc_id == recipe_doc)
        ).all()
        assert len(ratings) == 0


# ============================================================================
# 服务层测试
# ============================================================================


def test_upsert_rating_create_new(tmp_db, recipe_doc):
    """首次评分：创建新记录。"""
    from hermes_kb.recipe_ratings import upsert_rating

    result = upsert_rating(recipe_doc, user="alice", score=5, comment="好喝")
    assert result["status"] == "created"
    assert result["doc_id"] == recipe_doc
    assert result["user"] == "alice"
    assert result["score"] == 5
    assert result["comment"] == "好喝"


def test_upsert_rating_update_existing(tmp_db, recipe_doc):
    """重复评分：更新已有记录（UPSERT）。"""
    from hermes_kb.recipe_ratings import upsert_rating

    # 首次
    upsert_rating(recipe_doc, user="alice", score=3, comment="一般")
    # 更新
    result = upsert_rating(recipe_doc, user="alice", score=5, comment="改主意了，很好喝")
    assert result["status"] == "updated"
    assert result["score"] == 5
    assert result["comment"] == "改主意了，很好喝"


def test_upsert_rating_partial_update_score_only(tmp_db, recipe_doc):
    """仅更新 score 时保留原 comment。"""
    from hermes_kb.recipe_ratings import upsert_rating

    upsert_rating(recipe_doc, user="alice", score=3, comment="原笔记")
    result = upsert_rating(recipe_doc, user="alice", score=5, comment=None)
    assert result["status"] == "updated"
    assert result["score"] == 5
    assert result["comment"] == "原笔记"  # 保留原 comment


def test_upsert_rating_partial_update_comment_only(tmp_db, recipe_doc):
    """仅更新 comment 时保留原 score。"""
    from hermes_kb.recipe_ratings import upsert_rating

    upsert_rating(recipe_doc, user="alice", score=4, comment="原笔记")
    result = upsert_rating(recipe_doc, user="alice", score=None, comment="新笔记")
    assert result["status"] == "updated"
    assert result["score"] == 4  # 保留原 score
    assert result["comment"] == "新笔记"


def test_upsert_rating_note_only(tmp_db, recipe_doc):
    """仅提交笔记无评分（score=0）。"""
    from hermes_kb.recipe_ratings import upsert_rating

    result = upsert_rating(recipe_doc, user="bob", score=0, comment="只记笔记")
    assert result["status"] == "created"
    assert result["score"] == 0
    assert result["comment"] == "只记笔记"


def test_upsert_rating_invalid_score(tmp_db, recipe_doc):
    """score 越界抛 ValueError。"""
    from hermes_kb.recipe_ratings import upsert_rating

    with pytest.raises(ValueError):
        upsert_rating(recipe_doc, user="alice", score=6, comment="")

    with pytest.raises(ValueError):
        upsert_rating(recipe_doc, user="alice", score=-1, comment="")


def test_upsert_rating_both_none_raises(tmp_db, recipe_doc):
    """score 和 comment 同时为 None 抛 ValueError。"""
    from hermes_kb.recipe_ratings import upsert_rating

    with pytest.raises(ValueError):
        upsert_rating(recipe_doc, user="alice", score=None, comment=None)


def test_upsert_rating_doc_not_found(tmp_db):
    """配方不存在抛 LookupError。"""
    from hermes_kb.recipe_ratings import upsert_rating

    with pytest.raises(LookupError):
        upsert_rating("doc_not_exist", user="alice", score=5, comment="good")


def test_get_rating_summary_empty(tmp_db, recipe_doc):
    """无评分时返回零值。"""
    from hermes_kb.recipe_ratings import get_rating_summary

    summary = get_rating_summary(recipe_doc, current_user="alice")
    assert summary["doc_id"] == recipe_doc
    assert summary["average_score"] == 0.0
    assert summary["rating_count"] == 0
    assert summary["note_count"] == 0
    assert summary["current_user_rating"] is None
    assert summary["notes"] == []


def test_get_rating_summary_with_data(tmp_db, recipe_doc):
    """有评分数据时返回正确摘要。"""
    from hermes_kb.recipe_ratings import get_rating_summary, upsert_rating

    upsert_rating(recipe_doc, user="alice", score=5, comment="好喝")
    upsert_rating(recipe_doc, user="bob", score=3, comment="")
    upsert_rating(recipe_doc, user="carol", score=4, comment="不错")

    summary = get_rating_summary(recipe_doc, current_user="alice")
    assert summary["doc_id"] == recipe_doc
    # 平均分：(5+3+4)/3 = 4.0
    assert summary["average_score"] == 4.0
    assert summary["rating_count"] == 3
    # 笔记数：alice + carol（bob 空字符串不计入）
    assert summary["note_count"] == 2
    # 当前用户 alice 的评分
    assert summary["current_user_rating"] is not None
    assert summary["current_user_rating"]["score"] == 5
    assert summary["current_user_rating"]["comment"] == "好喝"
    # 笔记列表：alice + carol，按 updated_at 倒序
    assert len(summary["notes"]) == 2


def test_get_rating_summary_current_user_not_rated(tmp_db, recipe_doc):
    """当前用户未评分时 current_user_rating 为 None。"""
    from hermes_kb.recipe_ratings import get_rating_summary, upsert_rating

    upsert_rating(recipe_doc, user="alice", score=5, comment="好喝")
    summary = get_rating_summary(recipe_doc, current_user="bob")
    assert summary["current_user_rating"] is None


def test_get_rating_summary_no_current_user(tmp_db, recipe_doc):
    """current_user 为 None 时返回 current_user_rating=None。"""
    from hermes_kb.recipe_ratings import get_rating_summary, upsert_rating

    upsert_rating(recipe_doc, user="alice", score=5, comment="好喝")
    summary = get_rating_summary(recipe_doc, current_user=None)
    assert summary["current_user_rating"] is None


def test_get_rating_summary_doc_not_found(tmp_db):
    """配方不存在抛 LookupError。"""
    from hermes_kb.recipe_ratings import get_rating_summary

    with pytest.raises(LookupError):
        get_rating_summary("doc_not_exist", current_user="alice")


def test_get_rating_summary_score_zero_excluded(tmp_db, recipe_doc):
    """score=0（仅笔记）不计入平均分和 rating_count。"""
    from hermes_kb.recipe_ratings import get_rating_summary, upsert_rating

    upsert_rating(recipe_doc, user="alice", score=0, comment="仅笔记")
    upsert_rating(recipe_doc, user="bob", score=5, comment="")

    summary = get_rating_summary(recipe_doc)
    assert summary["average_score"] == 5.0  # 只有 bob 的 5 分
    assert summary["rating_count"] == 1  # alice score=0 不计入
    assert summary["note_count"] == 1  # alice 有笔记


# ============================================================================
# API 端点测试
# ============================================================================


def test_api_rate_recipe_create(client, recipe_doc):
    """POST /api/lab/recipes/{doc_id}/rate 创建评分。"""
    resp = client.post(
        f"/api/lab/recipes/{recipe_doc}/rate",
        json={"score": 5, "comment": "好喝"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "created"
    assert body["doc_id"] == recipe_doc
    assert body["score"] == 5
    assert body["comment"] == "好喝"


def test_api_rate_recipe_update(client, recipe_doc):
    """POST /api/lab/recipes/{doc_id}/rate 重复评分触发 UPSERT。"""
    # 首次
    client.post(
        f"/api/lab/recipes/{recipe_doc}/rate",
        json={"score": 3, "comment": "一般"},
    )
    # 更新
    resp = client.post(
        f"/api/lab/recipes/{recipe_doc}/rate",
        json={"score": 5, "comment": "改主意了"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "updated"
    assert resp.json()["score"] == 5


def test_api_rate_recipe_score_only(client, recipe_doc):
    """POST /api/lab/recipes/{doc_id}/rate 仅传 score。"""
    resp = client.post(
        f"/api/lab/recipes/{recipe_doc}/rate",
        json={"score": 4},
    )
    assert resp.status_code == 200
    assert resp.json()["score"] == 4
    assert resp.json()["comment"] == ""


def test_api_rate_recipe_comment_only(client, recipe_doc):
    """POST /api/lab/recipes/{doc_id}/rate 仅传 comment。"""
    resp = client.post(
        f"/api/lab/recipes/{recipe_doc}/rate",
        json={"comment": "只记笔记"},
    )
    assert resp.status_code == 200
    assert resp.json()["score"] == 0  # 默认 0
    assert resp.json()["comment"] == "只记笔记"


def test_api_rate_recipe_both_empty_rejected(client, recipe_doc):
    """score 和 comment 同时为空返回 422。"""
    resp = client.post(
        f"/api/lab/recipes/{recipe_doc}/rate",
        json={},
    )
    assert resp.status_code == 422
    assert "至少提交一项" in resp.json()["detail"]


def test_api_rate_recipe_invalid_score(client, recipe_doc):
    """score 超出 0-5 范围返回 422（Pydantic 校验）。"""
    resp = client.post(
        f"/api/lab/recipes/{recipe_doc}/rate",
        json={"score": 6},
    )
    assert resp.status_code == 422


def test_api_rate_recipe_doc_not_found(client):
    """配方不存在返回 404。"""
    resp = client.post(
        "/api/lab/recipes/doc_not_exist/rate",
        json={"score": 5},
    )
    assert resp.status_code == 404


def test_api_get_rating_empty(client, recipe_doc):
    """GET /api/lab/recipes/{doc_id}/rating 无评分时返回零值。"""
    resp = client.get(f"/api/lab/recipes/{recipe_doc}/rating")
    assert resp.status_code == 200
    body = resp.json()
    assert body["average_score"] == 0.0
    assert body["rating_count"] == 0
    assert body["note_count"] == 0
    assert body["notes"] == []


def test_api_get_rating_with_data(client, recipe_doc):
    """GET /api/lab/recipes/{doc_id}/rating 有评分时返回摘要。"""
    # 用服务层构造两个不同用户的评分（API 端点未启用认证时所有请求均为 anonymous，
    # UPSERT 语义下同 anonymous 多次 POST 只剩 1 条，故此处用服务层构造多用户场景）
    from hermes_kb.recipe_ratings import upsert_rating

    upsert_rating(recipe_doc, user="alice", score=5, comment="好喝")
    upsert_rating(recipe_doc, user="bob", score=3, comment="一般")

    resp = client.get(f"/api/lab/recipes/{recipe_doc}/rating")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rating_count"] == 2
    assert body["average_score"] == 4.0  # (5+3)/2
    assert body["note_count"] == 2
    assert len(body["notes"]) == 2


def test_api_get_rating_doc_not_found(client):
    """GET /api/lab/recipes/{doc_id}/rating 配方不存在返回 404。"""
    resp = client.get("/api/lab/recipes/doc_not_exist/rating")
    assert resp.status_code == 404


def test_api_rate_and_get_flow(client, recipe_doc):
    """端到端：评分 → 获取摘要 → 更新评分 → 获取摘要。"""
    # 1. 评分 3
    client.post(
        f"/api/lab/recipes/{recipe_doc}/rate",
        json={"score": 3, "comment": "初次评价"},
    )
    # 2. 获取摘要
    resp = client.get(f"/api/lab/recipes/{recipe_doc}/rating")
    assert resp.json()["average_score"] == 3.0
    assert resp.json()["rating_count"] == 1

    # 3. 更新为 5
    client.post(
        f"/api/lab/recipes/{recipe_doc}/rate",
        json={"score": 5, "comment": "改主意了"},
    )
    # 4. 再次获取：仍只有一条记录，平均分为 5
    resp = client.get(f"/api/lab/recipes/{recipe_doc}/rating")
    assert resp.json()["average_score"] == 5.0
    assert resp.json()["rating_count"] == 1
    assert resp.json()["notes"][0]["comment"] == "改主意了"
