"""M4.3 UGC 调酒研究室测试。"""
from __future__ import annotations

import pytest
from sqlmodel import select


def test_recipe_variant_model(tmp_db):
    """RecipeVariant 表可创建并写入（FK 约束要求 doc 必须存在）。"""
    from hermes_kb.models import Document, RecipeVariant
    from hermes_kb.database import get_session

    with get_session() as session:
        # FK 约束要求 base/variant doc 必须先存在
        base_doc = Document(title="原版", content="内容")
        variant_doc = Document(title="变体", content="内容")
        session.add(base_doc)
        session.add(variant_doc)
        session.commit()
        session.refresh(base_doc)
        session.refresh(variant_doc)

        v = RecipeVariant(
            base_doc_id=base_doc.doc_id,
            variant_doc_id=variant_doc.doc_id,
            variant_note="辛辣版，增加苦精",
        )
        session.add(v)
        session.commit()
        session.refresh(v)
        assert v.id is not None
        assert v.base_doc_id == base_doc.doc_id
        assert v.variant_doc_id == variant_doc.doc_id
        assert v.variant_note == "辛辣版，增加苦精"
        assert v.created_at is not None


def test_create_ugc_recipe(tmp_db):
    """创建 UGC 配方（draft 状态）。"""
    from hermes_kb.recipe_crud import create_recipe

    result = create_recipe(
        title="我的特调",
        ingredients=["金酒", "柠檬汁", "蜂蜜"],
        content="# 我的特调\n\n## 配方\n- 金酒 50ml\n- 柠檬汁 20ml\n- 蜂蜜 15ml",
        base_spirit="gin",
        difficulty="easy",
        season="spring",
    )
    assert result["doc_id"] is not None
    assert result["status"] == "draft"

    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    with get_session() as session:
        doc = session.get(Document, result["doc_id"])
        assert doc.title == "我的特调"
        assert doc.category == "recipe"
        assert doc.source == "ugc"
        assert doc.verified is False
        assert doc.status == "draft"
        assert doc.season == "spring"


def test_submit_recipe(tmp_db):
    """提交审核（draft → pending）。"""
    from hermes_kb.recipe_crud import create_recipe, submit_recipe
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    created = create_recipe(
        title="待审核配方",
        ingredients=["金酒"],
        content="# 待审核\n\n## 配方\n- 金酒 50ml",
        base_spirit="gin",
        difficulty="easy",
    )
    doc_id = created["doc_id"]

    ok = submit_recipe(doc_id)
    assert ok is True

    with get_session() as session:
        doc = session.get(Document, doc_id)
        assert doc.status == "pending"


def test_approve_recipe(tmp_db):
    """审核通过（pending → published, verified=True）。"""
    from hermes_kb.recipe_crud import create_recipe, submit_recipe, approve_recipe
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    created = create_recipe(
        title="将通过",
        ingredients=["金酒"],
        content="# 将通过\n\n## 配方\n- 金酒 50ml",
        base_spirit="gin",
        difficulty="easy",
    )
    submit_recipe(created["doc_id"])

    ok = approve_recipe(created["doc_id"])
    assert ok is True

    with get_session() as session:
        doc = session.get(Document, created["doc_id"])
        assert doc.status == "published"
        assert doc.verified is True


def test_reject_recipe(tmp_db):
    """审核驳回（pending → rejected）。"""
    from hermes_kb.recipe_crud import create_recipe, submit_recipe, reject_recipe
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    created = create_recipe(
        title="将驳回",
        ingredients=["金酒"],
        content="# 将驳回\n\n## 配方\n- 金酒 50ml",
        base_spirit="gin",
        difficulty="easy",
    )
    submit_recipe(created["doc_id"])

    ok = reject_recipe(created["doc_id"], reason="材料比例不合理")
    assert ok is True

    with get_session() as session:
        doc = session.get(Document, created["doc_id"])
        assert doc.status == "rejected"
        assert doc.verified is False


def test_update_recipe(tmp_db):
    """编辑配方（仅 draft 状态可编辑）。"""
    from hermes_kb.recipe_crud import create_recipe, update_recipe, submit_recipe
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    created = create_recipe(
        title="原配方",
        ingredients=["金酒"],
        content="# 原配方\n\n## 配方\n- 金酒 50ml",
        base_spirit="gin",
        difficulty="easy",
    )
    # draft 状态可编辑
    ok = update_recipe(
        created["doc_id"],
        title="改后配方",
        content="# 改后配方\n\n## 配方\n- 金酒 50ml\n- 柠檬汁 20ml",
    )
    assert ok is True

    with get_session() as session:
        doc = session.get(Document, created["doc_id"])
        assert doc.title == "改后配方"

    # pending 状态不可编辑
    submit_recipe(created["doc_id"])
    ok2 = update_recipe(
        created["doc_id"],
        title="再改",
        content="# 再改",
    )
    assert ok2 is False


@pytest.fixture
def base_and_variant(tmp_db):
    """创建一个原配方和一个变体。"""
    from hermes_kb.recipe_crud import create_recipe

    base = create_recipe(
        title="原版马天尼",
        ingredients=["金酒", "味美思", "橄榄"],
        content="# 原版马天尼\n\n## 配方\n- 金酒 60ml\n- 味美思 10ml\n- 橄榄 1颗",
        base_spirit="gin",
        difficulty="easy",
    )
    variant = create_recipe(
        title="辛辣马天尼",
        ingredients=["金酒", "味美思", "苦精"],
        content="# 辛辣马天尼\n\n## 配方\n- 金酒 60ml\n- 味美思 10ml\n- 苦精 2滴",
        base_spirit="gin",
        difficulty="medium",
    )
    return base, variant


def test_create_variant_link(base_and_variant):
    """创建变体关联。"""
    from hermes_kb.recipe_variants import create_variant_link, get_variants

    base, variant = base_and_variant
    ok = create_variant_link(
        base_doc_id=base["doc_id"],
        variant_doc_id=variant["doc_id"],
        variant_note="增加苦精的辛辣版",
    )
    assert ok is True

    variants = get_variants(base["doc_id"])
    assert len(variants) == 1
    assert variants[0]["variant_doc_id"] == variant["doc_id"]
    assert variants[0]["variant_note"] == "增加苦精的辛辣版"
    assert variants[0]["variant_title"] == "辛辣马天尼"


def test_get_base_recipe(base_and_variant):
    """查询变体的原配方。"""
    from hermes_kb.recipe_variants import create_variant_link, get_base_recipe

    base, variant = base_and_variant
    create_variant_link(base["doc_id"], variant["doc_id"], "测试")

    base_info = get_base_recipe(variant["doc_id"])
    assert base_info is not None
    assert base_info["base_doc_id"] == base["doc_id"]
    assert base_info["base_title"] == "原版马天尼"


def test_create_variant_duplicate(base_and_variant):
    """重复创建变体关联返回 False。"""
    from hermes_kb.recipe_variants import create_variant_link

    base, variant = base_and_variant
    create_variant_link(base["doc_id"], variant["doc_id"], "第一次")
    ok = create_variant_link(base["doc_id"], variant["doc_id"], "第二次")
    assert ok is False


def test_api_create_recipe(client):
    """POST /api/lab/recipes 创建 UGC 配方。"""
    resp = client.post("/api/lab/recipes", json={
        "title": "API 特调",
        "ingredients": ["金酒", "柠檬汁"],
        "content": "# API 特调\n\n## 配方\n- 金酒 50ml\n- 柠檬汁 20ml",
        "base_spirit": "gin",
        "difficulty": "easy",
        "season": "summer",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert data["doc_id"] is not None


def test_api_recipe_lifecycle(client):
    """UGC 配方完整生命周期：创建→提交→通过。"""
    # 创建
    created = client.post("/api/lab/recipes", json={
        "title": "生命周期测试",
        "ingredients": ["金酒"],
        "content": "# 生命周期测试\n\n## 配方\n- 金酒 50ml",
        "base_spirit": "gin",
        "difficulty": "easy",
    }).json()
    doc_id = created["doc_id"]

    # 提交
    resp = client.post(f"/api/lab/recipes/{doc_id}/submit")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    # 通过
    resp = client.post(f"/api/lab/recipes/{doc_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_api_recipe_reject(client):
    """POST /api/lab/recipes/{doc_id}/reject 审核驳回。"""
    created = client.post("/api/lab/recipes", json={
        "title": "将被驳回",
        "ingredients": ["金酒"],
        "content": "# 将被驳回",
        "base_spirit": "gin",
        "difficulty": "easy",
    }).json()
    client.post(f"/api/lab/recipes/{created['doc_id']}/submit")

    resp = client.post(
        f"/api/lab/recipes/{created['doc_id']}/reject",
        json={"reason": "配方不完整"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_api_recipe_variants(client, base_and_variant):
    """GET /api/lab/recipes/{doc_id}/variants 查看变体。"""
    from hermes_kb.recipe_variants import create_variant_link

    base, variant = base_and_variant
    create_variant_link(base["doc_id"], variant["doc_id"], "测试变体")

    resp = client.get(f"/api/lab/recipes/{base['doc_id']}/variants")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["variant_title"] == "辛辣马天尼"


def test_api_pending_recipes(client, base_and_variant):
    """GET /api/lab/recipes?status=pending 查看待审核。"""
    from hermes_kb.recipe_crud import submit_recipe

    base, _ = base_and_variant
    submit_recipe(base["doc_id"])

    resp = client.get("/api/lab/recipes", params={"status": "pending"})
    assert resp.status_code == 200
    data = resp.json()
    assert any(i["title"] == "原版马天尼" for i in data["items"])


def test_update_recipe_rejects_ingredients(tmp_db):
    """P2-2: update_recipe 传非空 ingredients 应抛 ValueError（显式拒绝而非静默丢弃）。"""
    from hermes_kb.recipe_crud import create_recipe, update_recipe

    created = create_recipe(
        title="测试配方",
        ingredients=["金酒"],
        content="# 测试配方\n\n## 配方\n- 金酒 50ml",
    )
    # 传非空 ingredients 应抛 ValueError
    with pytest.raises(ValueError, match="不支持更新 ingredients"):
        update_recipe(created["doc_id"], ingredients=["金酒", "柠檬汁"])
    # 不传 ingredients 正常工作
    ok = update_recipe(created["doc_id"], title="新标题")
    assert ok is True


def test_api_update_recipe_ingredients_returns_400(client):
    """P2-2: PUT /api/lab/recipes/{doc_id} 传 ingredients 返回 400 而非静默丢弃。"""
    created = client.post("/api/lab/recipes", json={
        "title": "API 编辑测试",
        "ingredients": ["金酒"],
        "content": "# API 编辑测试\n\n## 配方\n- 金酒 50ml",
    }).json()
    resp = client.put(f"/api/lab/recipes/{created['doc_id']}", json={
        "ingredients": ["金酒", "柠檬汁"],
    })
    assert resp.status_code == 400
    assert "ingredients" in resp.json()["detail"]


def test_import_text_governance_atomic(tmp_db):
    """P2-3: import_text 治理字段与 doc 在同一事务原子落库（无第二阶段）。

    验证 verified/status/source/category/source_id/image_url 一次性写入，
    避免崩溃残留模型默认（verified=True/status=published）绕过治理意图。
    """
    from hermes_kb.rag import ImportService
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    importer = ImportService()
    result = importer.import_text(
        content="# 外部配方\n\n## 配方\n- 金酒 50ml",
        title="外部待审核",
        source_type="upload",
        file_type="md",
        category="recipe",
        source="thecocktaildb",
        source_id="cocktail-11008",
        verified=False,
        status="pending",
        image_url="https://example.com/drink.png",
        season="summer",
    )
    doc_id = result["doc_id"]

    # 单次读取即应包含全部治理字段（证明同一事务写入，无需第二阶段）
    with get_session() as session:
        doc = session.get(Document, doc_id)
        assert doc.category == "recipe"
        assert doc.source == "thecocktaildb"
        assert doc.source_id == "cocktail-11008"
        assert doc.verified is False  # 关键：未残留模型默认 True
        assert doc.status == "pending"  # 关键：未残留模型默认 published
        assert doc.image_url == "https://example.com/drink.png"
        assert doc.season == "summer"


def test_import_text_governance_defaults_preserved(tmp_db):
    """P2-3: 不传治理字段时保留模型默认（向后兼容）。"""
    from hermes_kb.rag import ImportService
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    importer = ImportService()
    result = importer.import_text(
        content="普通文档内容",
        title="普通文档",
    )
    with get_session() as session:
        doc = session.get(Document, result["doc_id"])
        assert doc.verified is True  # 模型默认
        assert doc.status == "published"  # 模型默认
        assert doc.source == "local"  # 模型默认
        assert doc.category == ""


def test_create_recipe_governance_atomic(tmp_db):
    """P2-3: create_recipe 落地 verified=False/status=draft 原子（无残留 published）。"""
    from hermes_kb.recipe_crud import create_recipe
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    result = create_recipe(
        title="UGC 原子测试",
        ingredients=["金酒"],
        content="# UGC 原子测试\n\n## 配方\n- 金酒 50ml",
        season="winter",
    )
    with get_session() as session:
        doc = session.get(Document, result["doc_id"])
        assert doc.verified is False
        assert doc.status == "draft"
        assert doc.source == "ugc"
        assert doc.category == "recipe"
        assert doc.source_id == f"ugc-{result['doc_id']}"
        assert doc.season == "winter"


def test_recipe_variant_cascade_on_delete(base_and_variant):
    """P0-2: 删除 base 配方后，RecipeVariant 关联应级联删除（不留孤儿）。"""
    from hermes_kb.recipe_variants import create_variant_link
    from hermes_kb.models import Document, RecipeVariant
    from hermes_kb.database import get_session

    base, variant = base_and_variant
    create_variant_link(base["doc_id"], variant["doc_id"], "测试级联")

    with get_session() as session:
        # 确认关联已建立
        links_before = session.exec(
            select(RecipeVariant).where(RecipeVariant.base_doc_id == base["doc_id"])
        ).all()
        assert len(links_before) == 1

        # 删除 base Document
        doc = session.get(Document, base["doc_id"])
        session.delete(doc)
        session.commit()

        # RecipeVariant 应被级联删除（不留孤儿）
        links_after = session.exec(
            select(RecipeVariant).where(RecipeVariant.base_doc_id == base["doc_id"])
        ).all()
        assert len(links_after) == 0


def test_recipe_variant_cascade_on_delete_variant(base_and_variant):
    """P0-2: 删除 variant 配方后，RecipeVariant 关联也应级联删除。"""
    from hermes_kb.recipe_variants import create_variant_link
    from hermes_kb.models import Document, RecipeVariant
    from hermes_kb.database import get_session

    base, variant = base_and_variant
    create_variant_link(base["doc_id"], variant["doc_id"], "测试级联")

    with get_session() as session:
        links_before = session.exec(
            select(RecipeVariant).where(RecipeVariant.variant_doc_id == variant["doc_id"])
        ).all()
        assert len(links_before) == 1

        # 删除 variant Document
        doc = session.get(Document, variant["doc_id"])
        session.delete(doc)
        session.commit()

        # RecipeVariant 应被级联删除
        links_after = session.exec(
            select(RecipeVariant).where(RecipeVariant.variant_doc_id == variant["doc_id"])
        ).all()
        assert len(links_after) == 0


# ---------------------------------------------------------------------------
# V3-Task11: UGC 审核流完善（author/reviewer/resubmit/list_my_recipes）
# ---------------------------------------------------------------------------


def test_create_recipe_records_author_in_meta(tmp_db):
    """V3-Task11: create_recipe 将 author 写入 meta JSON。"""
    from hermes_kb.recipe_crud import create_recipe, _read_meta
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    result = create_recipe(
        title="作者测试",
        ingredients=["金酒"],
        content="# 作者测试\n\n## 配方\n- 金酒 50ml",
        author="alice",
    )
    with get_session() as session:
        doc = session.get(Document, result["doc_id"])
        meta = _read_meta(doc)
        assert meta["author"] == "alice"


def test_create_recipe_default_author_anonymous(tmp_db):
    """V3-Task11: 未传 author 时默认 "anonymous"（向后兼容）。"""
    from hermes_kb.recipe_crud import create_recipe, _read_meta
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    result = create_recipe(
        title="匿名测试",
        ingredients=["金酒"],
        content="# 匿名测试",
    )
    with get_session() as session:
        doc = session.get(Document, result["doc_id"])
        meta = _read_meta(doc)
        assert meta["author"] == "anonymous"


def test_approve_recipe_records_reviewer(tmp_db):
    """V3-Task11: approve_recipe 将 reviewer 和 reviewed_at 写入 meta。"""
    from hermes_kb.recipe_crud import (
        approve_recipe,
        create_recipe,
        _read_meta,
        submit_recipe,
    )
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    created = create_recipe(
        title="审核人测试",
        ingredients=["金酒"],
        content="# 审核人测试",
        author="alice",
    )
    submit_recipe(created["doc_id"])
    ok = approve_recipe(created["doc_id"], reviewer="owner_bob")
    assert ok is True

    with get_session() as session:
        doc = session.get(Document, created["doc_id"])
        meta = _read_meta(doc)
        assert meta["reviewer"] == "owner_bob"
        assert meta["reviewed_at"] is not None
        assert doc.status == "published"
        assert doc.verified is True


def test_reject_recipe_records_reviewer_and_reason(tmp_db):
    """V3-Task11: reject_recipe 将 reviewer/reject_reason/reviewed_at 写入 meta。"""
    from hermes_kb.recipe_crud import (
        create_recipe,
        _read_meta,
        reject_recipe,
        submit_recipe,
    )
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    created = create_recipe(
        title="驳回理由测试",
        ingredients=["金酒"],
        content="# 驳回理由测试",
        author="alice",
    )
    submit_recipe(created["doc_id"])
    ok = reject_recipe(
        created["doc_id"],
        reason="材料比例不对",
        reviewer="owner_bob",
    )
    assert ok is True

    with get_session() as session:
        doc = session.get(Document, created["doc_id"])
        meta = _read_meta(doc)
        assert meta["reviewer"] == "owner_bob"
        assert meta["reject_reason"] == "材料比例不对"
        assert meta["reviewed_at"] is not None
        assert doc.status == "rejected"


def test_resubmit_recipe_rejected_to_draft(tmp_db):
    """V3-Task11: resubmit_recipe 将 rejected → draft。"""
    from hermes_kb.recipe_crud import (
        create_recipe,
        reject_recipe,
        resubmit_recipe,
        submit_recipe,
    )
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    created = create_recipe(
        title="重新提交测试",
        ingredients=["金酒"],
        content="# 重新提交测试",
    )
    submit_recipe(created["doc_id"])
    reject_recipe(created["doc_id"], reason="需修改")

    # rejected → draft
    ok = resubmit_recipe(created["doc_id"])
    assert ok is True
    with get_session() as session:
        doc = session.get(Document, created["doc_id"])
        assert doc.status == "draft"


def test_resubmit_recipe_only_from_rejected(tmp_db):
    """V3-Task11: resubmit_recipe 仅 rejected 状态可调用，其他状态返回 False。"""
    from hermes_kb.recipe_crud import (
        create_recipe,
        resubmit_recipe,
        submit_recipe,
    )

    created = create_recipe(
        title="状态测试",
        ingredients=["金酒"],
        content="# 状态测试",
    )
    # draft 状态不可 resubmit
    assert resubmit_recipe(created["doc_id"]) is False

    # pending 状态不可 resubmit
    submit_recipe(created["doc_id"])
    assert resubmit_recipe(created["doc_id"]) is False


def test_resubmit_recipe_nonexistent_returns_false(tmp_db):
    """V3-Task11: resubmit_recipe 对不存在的 doc_id 返回 False。"""
    from hermes_kb.recipe_crud import resubmit_recipe

    assert resubmit_recipe("doc-nonexistent-xyz") is False


def test_list_my_recipes_filters_by_author(tmp_db):
    """V3-Task11: list_my_recipes 按 author 筛选个人配方库。"""
    from hermes_kb.recipe_crud import create_recipe, list_my_recipes

    # alice 创建 2 个配方
    create_recipe(
        title="Alice 配方 1",
        ingredients=["金酒"],
        content="# Alice 1",
        author="alice",
    )
    create_recipe(
        title="Alice 配方 2",
        ingredients=["金酒"],
        content="# Alice 2",
        author="alice",
    )
    # bob 创建 1 个配方
    create_recipe(
        title="Bob 配方 1",
        ingredients=["金酒"],
        content="# Bob 1",
        author="bob",
    )

    alice_recipes = list_my_recipes(author="alice")
    assert len(alice_recipes) == 2
    assert all(r["author"] == "alice" for r in alice_recipes)
    titles = {r["title"] for r in alice_recipes}
    assert "Alice 配方 1" in titles
    assert "Alice 配方 2" in titles
    assert "Bob 配方 1" not in titles

    bob_recipes = list_my_recipes(author="bob")
    assert len(bob_recipes) == 1
    assert bob_recipes[0]["title"] == "Bob 配方 1"


def test_list_my_recipes_returns_empty_for_unknown_author(tmp_db):
    """V3-Task11: 未知作者返回空列表。"""
    from hermes_kb.recipe_crud import list_my_recipes

    result = list_my_recipes(author="nobody")
    assert result == []


def test_list_my_recipes_excludes_non_ugc(tmp_db):
    """V3-Task11: list_my_recipes 仅返回 source=ugc 的配方，排除其他来源。"""
    from hermes_kb.recipe_crud import create_recipe, list_my_recipes
    from hermes_kb.rag import ImportService

    # 创建 UGC 配方
    create_recipe(
        title="UGC 配方",
        ingredients=["金酒"],
        content="# UGC",
        author="alice",
    )
    # 创建非 UGC 配方（iba）
    importer = ImportService()
    importer.import_text(
        content="# IBA 配方",
        title="IBA 配方",
        category="recipe",
        source="iba",
        verified=True,
        status="published",
    )

    alice_recipes = list_my_recipes(author="alice")
    assert len(alice_recipes) == 1
    assert alice_recipes[0]["title"] == "UGC 配方"


def test_list_my_recipes_summary_includes_meta_fields(tmp_db):
    """V3-Task11: _recipe_summary 包含 author/reviewer/reject_reason 字段。"""
    from hermes_kb.recipe_crud import (
        create_recipe,
        list_my_recipes,
        reject_recipe,
        submit_recipe,
    )

    created = create_recipe(
        title="摘要测试",
        ingredients=["金酒"],
        content="# 摘要测试",
        author="alice",
    )
    submit_recipe(created["doc_id"])
    reject_recipe(created["doc_id"], reason="不行", reviewer="bob")

    alice_recipes = list_my_recipes(author="alice")
    assert len(alice_recipes) == 1
    item = alice_recipes[0]
    assert item["author"] == "alice"
    assert item["reviewer"] == "bob"
    assert item["reject_reason"] == "不行"
    assert item["status"] == "rejected"
    assert item["doc_id"] == created["doc_id"]


def test_get_recipe_author_returns_meta_author(tmp_db):
    """V3-Task11: get_recipe_author 从 meta 读取作者。"""
    from hermes_kb.recipe_crud import create_recipe, get_recipe_author

    created = create_recipe(
        title="作者读取测试",
        ingredients=["金酒"],
        content="# 作者读取",
        author="carol",
    )
    assert get_recipe_author(created["doc_id"]) == "carol"


def test_get_recipe_author_returns_anonymous_for_legacy(tmp_db):
    """V3-Task11: 旧配方（无 meta.author）返回 "anonymous"。"""
    from hermes_kb.recipe_crud import get_recipe_author
    from hermes_kb.rag import ImportService

    result = ImportService().import_text(
        content="# 旧配方",
        title="旧配方",
        category="recipe",
        source="ugc",
    )
    # 旧配方 meta 默认 "{}"，无 author 字段
    assert get_recipe_author(result["doc_id"]) == "anonymous"


def test_get_recipe_author_returns_empty_for_nonexistent(tmp_db):
    """V3-Task11: 不存在的 doc_id 返回空串。"""
    from hermes_kb.recipe_crud import get_recipe_author

    assert get_recipe_author("doc-no-such") == ""


# ---------------------------------------------------------------------------
# V3-Task11: API 端点测试
# ---------------------------------------------------------------------------


def test_api_create_recipe_records_author_anonymous(client):
    """V3-Task11: POST /api/lab/recipes 未启用认证时 author="anonymous"。"""
    from hermes_kb.recipe_crud import _read_meta
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    resp = client.post("/api/lab/recipes", json={
        "title": "API 作者测试",
        "ingredients": ["金酒"],
        "content": "# API 作者测试",
    })
    assert resp.status_code == 200
    doc_id = resp.json()["doc_id"]

    with get_session() as session:
        doc = session.get(Document, doc_id)
        meta = _read_meta(doc)
        assert meta["author"] == "anonymous"


def test_api_my_recipes_returns_ugc(client):
    """V3-Task11: GET /api/lab/recipes/my 返回当前用户的 UGC 配方。"""
    # 创建 2 个 UGC 配方
    client.post("/api/lab/recipes", json={
        "title": "我的配方 A",
        "ingredients": ["金酒"],
        "content": "# 配方 A",
    })
    client.post("/api/lab/recipes", json={
        "title": "我的配方 B",
        "ingredients": ["朗姆酒"],
        "content": "# 配方 B",
    })

    resp = client.get("/api/lab/recipes/my")
    assert resp.status_code == 200
    data = resp.json()
    assert data["author"] == "anonymous"
    titles = {item["title"] for item in data["items"]}
    assert "我的配方 A" in titles
    assert "我的配方 B" in titles


def test_api_my_recipes_empty(client):
    """V3-Task11: GET /api/lab/recipes/my 无 UGC 配方时返回空列表。"""
    resp = client.get("/api/lab/recipes/my")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_api_resubmit_recipe_rejected_to_draft(client):
    """V3-Task11: POST /api/lab/recipes/{doc_id}/resubmit rejected → draft。"""
    # 创建 → 提交 → 驳回 → 重新提交
    created = client.post("/api/lab/recipes", json={
        "title": "重新提交 API 测试",
        "ingredients": ["金酒"],
        "content": "# 重新提交 API",
    }).json()
    doc_id = created["doc_id"]

    client.post(f"/api/lab/recipes/{doc_id}/submit")
    client.post(f"/api/lab/recipes/{doc_id}/reject", json={"reason": "需修改"})

    resp = client.post(f"/api/lab/recipes/{doc_id}/resubmit")
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


def test_api_resubmit_recipe_wrong_status_returns_400(client):
    """V3-Task11: resubmit 非 rejected 状态返回 400。"""
    created = client.post("/api/lab/recipes", json={
        "title": "状态错误测试",
        "ingredients": ["金酒"],
        "content": "# 状态错误",
    }).json()

    # draft 状态不可 resubmit
    resp = client.post(f"/api/lab/recipes/{created['doc_id']}/resubmit")
    assert resp.status_code == 400
    assert "rejected" in resp.json()["detail"]


def test_api_approve_recipe_records_reviewer(client):
    """V3-Task11: POST /api/lab/recipes/{doc_id}/approve 记录 reviewer。"""
    from hermes_kb.recipe_crud import _read_meta
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    created = client.post("/api/lab/recipes", json={
        "title": "审核人 API 测试",
        "ingredients": ["金酒"],
        "content": "# 审核人 API",
    }).json()
    client.post(f"/api/lab/recipes/{created['doc_id']}/submit")
    client.post(f"/api/lab/recipes/{created['doc_id']}/approve")

    with get_session() as session:
        doc = session.get(Document, created["doc_id"])
        meta = _read_meta(doc)
        assert meta["reviewer"] == "anonymous"
        assert meta["reviewed_at"] is not None


def test_api_reject_recipe_records_reviewer_and_reason(client):
    """V3-Task11: POST /api/lab/recipes/{doc_id}/reject 记录 reviewer 和 reason。"""
    from hermes_kb.recipe_crud import _read_meta
    from hermes_kb.models import Document
    from hermes_kb.database import get_session

    created = client.post("/api/lab/recipes", json={
        "title": "驳回 API 测试",
        "ingredients": ["金酒"],
        "content": "# 驳回 API",
    }).json()
    client.post(f"/api/lab/recipes/{created['doc_id']}/submit")
    client.post(
        f"/api/lab/recipes/{created['doc_id']}/reject",
        json={"reason": "配方不完整"},
    )

    with get_session() as session:
        doc = session.get(Document, created["doc_id"])
        meta = _read_meta(doc)
        assert meta["reviewer"] == "anonymous"
        assert meta["reject_reason"] == "配方不完整"
        assert meta["reviewed_at"] is not None


def test_api_my_recipes_limit_param(client):
    """V3-Task11: GET /api/lab/recipes/my?limit=N 限制返回数量。"""
    # 创建 3 个 UGC 配方
    for i in range(3):
        client.post("/api/lab/recipes", json={
            "title": f"限制测试 {i}",
            "ingredients": ["金酒"],
            "content": f"# 限制 {i}",
        })

    # limit=2 应只返回 2 条
    resp = client.get("/api/lab/recipes/my?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2


def test_api_my_recipes_shows_reject_reason(client):
    """V3-Task11: /api/lab/recipes/my 返回的 rejected 配方包含 reject_reason。"""
    created = client.post("/api/lab/recipes", json={
        "title": "驳回理由展示",
        "ingredients": ["金酒"],
        "content": "# 驳回理由展示",
    }).json()
    client.post(f"/api/lab/recipes/{created['doc_id']}/submit")
    client.post(
        f"/api/lab/recipes/{created['doc_id']}/reject",
        json={"reason": "材料太少"},
    )

    resp = client.get("/api/lab/recipes/my")
    data = resp.json()
    rejected_items = [i for i in data["items"] if i["status"] == "rejected"]
    assert len(rejected_items) >= 1
    target = next(i for i in rejected_items if i["doc_id"] == created["doc_id"])
    assert target["reject_reason"] == "材料太少"
