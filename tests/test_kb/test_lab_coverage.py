"""lab.py 端点覆盖率补强：sync-all / IMA / recipe_stats / translate-titles / substitutes。

覆盖 lab.py 中未被现有测试触及的端点与错误路径：
- /api/lab/sync-all：三数据源聚合同步（含单源失败容错）
- /api/lab/ima/*：IMA 知识库同步（未配置/列表/同步/搜索/参数校验）
- /api/lab/recipes/{doc_id}/stats：配方 ABV/卡路里（frontmatter/estimated/404/非配方）
- /api/lab/translate-titles：批量翻译（Mock 后端 + 已中文跳过 + 按源筛选）
- /api/lab/substitutes：查询替代关系（单个/全部）
- /api/lab/recipes/{doc_id}/variant：变体创建错误路径
- /api/lab/recipes/{doc_id}/approve|reject|submit：状态机错误路径
"""
from __future__ import annotations


# ===========================================================================
# /api/lab/sync-all
# ===========================================================================
class TestSyncAll:
    """一键同步全部 P0 数据源。"""

    def test_sync_all_success(self, client, monkeypatch):
        """三数据源全部成功。"""
        from hermes_kb import bar_assistant_sync, iba_dataset_importer, thecocktaildb_sync

        monkeypatch.setattr(
            iba_dataset_importer, "sync_iba_dataset",
            lambda importer=None: {"imported": 5, "skipped": 0, "failed": 0},
        )
        monkeypatch.setattr(
            thecocktaildb_sync, "sync_thecocktaildb",
            lambda limit=50, importer=None: {"imported": 10, "skipped": 1, "failed": 0},
        )
        monkeypatch.setattr(
            bar_assistant_sync, "sync_bar_assistant_substitutes",
            lambda: {"imported": 3, "skipped": 0, "failed": 0},
        )

        resp = client.post("/api/lab/sync-all")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert set(body["results"].keys()) == {"iba_dataset", "thecocktaildb", "bar_assistant"}
        assert body["results"]["iba_dataset"]["imported"] == 5
        assert body["results"]["thecocktaildb"]["imported"] == 10
        assert body["results"]["bar_assistant"]["imported"] == 3

    def test_sync_all_partial_failure(self, client, monkeypatch):
        """单数据源失败时其他源仍同步。"""
        from hermes_kb import bar_assistant_sync, iba_dataset_importer, thecocktaildb_sync

        def iba_fail(importer=None):
            raise RuntimeError("IBA 网络故障")

        monkeypatch.setattr(iba_dataset_importer, "sync_iba_dataset", iba_fail)
        monkeypatch.setattr(
            thecocktaildb_sync, "sync_thecocktaildb",
            lambda limit=50, importer=None: {"imported": 7, "skipped": 0, "failed": 0},
        )
        monkeypatch.setattr(
            bar_assistant_sync, "sync_bar_assistant_substitutes",
            lambda: {"imported": 2, "skipped": 0, "failed": 0},
        )

        resp = client.post("/api/lab/sync-all")
        assert resp.status_code == 200
        body = resp.json()
        # 失败的源应含 error 字段
        assert "error" in body["results"]["iba_dataset"]
        assert body["results"]["iba_dataset"]["imported"] == 0
        # 其他源仍成功
        assert body["results"]["thecocktaildb"]["imported"] == 7
        assert body["results"]["bar_assistant"]["imported"] == 2

    def test_sync_all_all_fail(self, client, monkeypatch):
        """三数据源全部失败仍返回 200（容错设计）。"""
        from hermes_kb import bar_assistant_sync, iba_dataset_importer, thecocktaildb_sync

        monkeypatch.setattr(
            iba_dataset_importer, "sync_iba_dataset",
            lambda importer=None: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        monkeypatch.setattr(
            thecocktaildb_sync, "sync_thecocktaildb",
            lambda limit=50, importer=None: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        monkeypatch.setattr(
            bar_assistant_sync, "sync_bar_assistant_substitutes",
            lambda: (_ for _ in ()).throw(RuntimeError("fail")),
        )

        resp = client.post("/api/lab/sync-all")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        for src in ["iba_dataset", "thecocktaildb", "bar_assistant"]:
            assert "error" in body["results"][src]


# ===========================================================================
# /api/lab/ima/*
# ===========================================================================
class TestIMAEndpoints:
    """IMA 知识库同步端点。"""

    def test_ima_list_kbs_not_configured(self, client):
        """未配置 IMA 凭证 → 400。"""
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="", ima_api_key="")
        resp = client.get("/api/lab/ima/knowledge-bases")
        assert resp.status_code == 400
        assert "IMA 未配置" in resp.json()["detail"]

    def test_ima_list_kbs_success(self, client, monkeypatch):
        """配置后返回知识库列表。"""
        from hermes_kb import ima_sync
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")
        monkeypatch.setattr(
            ima_sync, "list_knowledge_bases",
            lambda query="", limit=50: [{"id": "kb1", "name": "测试库"}],
        )

        resp = client.get("/api/lab/ima/knowledge-bases")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == "kb1"

    def test_ima_list_kbs_config_error(self, client, monkeypatch):
        """IMAConfigError → 400。"""
        from hermes_kb import ima_sync
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")

        class IMAConfigError(Exception):
            pass

        monkeypatch.setattr(ima_sync, "IMAConfigError", IMAConfigError)
        monkeypatch.setattr(
            ima_sync, "list_knowledge_bases",
            lambda query="", limit=50: (_ for _ in ()).throw(IMAConfigError("凭证无效")),
        )

        resp = client.get("/api/lab/ima/knowledge-bases")
        assert resp.status_code == 400
        assert "凭证无效" in resp.json()["detail"]

    def test_ima_list_kbs_api_error(self, client, monkeypatch):
        """其他异常 → 502。"""
        from hermes_kb import ima_sync
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")

        class IMAConfigError(Exception):
            pass

        monkeypatch.setattr(ima_sync, "IMAConfigError", IMAConfigError)
        monkeypatch.setattr(
            ima_sync, "list_knowledge_bases",
            lambda query="", limit=50: (_ for _ in ()).throw(RuntimeError("网络故障")),
        )

        resp = client.get("/api/lab/ima/knowledge-bases")
        assert resp.status_code == 502

    def test_ima_sync_not_configured(self, client):
        """未配置 → 400。"""
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="", ima_api_key="", ima_kb_id="")
        resp = client.post("/api/lab/ima/sync", json={"query": "鸡尾酒", "limit": 10})
        assert resp.status_code == 400

    def test_ima_sync_success(self, client, monkeypatch):
        """成功同步。"""
        from hermes_kb import ima_sync
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")
        monkeypatch.setattr(
            ima_sync, "sync_knowledge_base",
            lambda query, kb_id, limit, category, importer: {
                "imported": 5,
                "skipped": 0,
                "failed": 0,
            },
        )

        resp = client.post("/api/lab/ima/sync", json={"query": "鸡尾酒", "limit": 10})
        assert resp.status_code == 200
        body = resp.json()
        assert body["source"] == "ima"
        assert body["imported"] == 5

    def test_ima_sync_config_error(self, client, monkeypatch):
        """IMAConfigError → 400。"""
        from hermes_kb import ima_sync
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")

        class IMAConfigError(Exception):
            pass

        class IMAAPIError(Exception):
            pass

        monkeypatch.setattr(ima_sync, "IMAConfigError", IMAConfigError)
        monkeypatch.setattr(ima_sync, "IMAAPIError", IMAAPIError)
        monkeypatch.setattr(
            ima_sync, "sync_knowledge_base",
            lambda **kwargs: (_ for _ in ()).throw(IMAConfigError("bad")),
        )

        resp = client.post("/api/lab/ima/sync", json={"query": "x"})
        assert resp.status_code == 400

    def test_ima_sync_api_error(self, client, monkeypatch):
        """IMAAPIError → 502。"""
        from hermes_kb import ima_sync
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")

        class IMAConfigError(Exception):
            pass

        class IMAAPIError(Exception):
            pass

        monkeypatch.setattr(ima_sync, "IMAConfigError", IMAConfigError)
        monkeypatch.setattr(ima_sync, "IMAAPIError", IMAAPIError)
        monkeypatch.setattr(
            ima_sync, "sync_knowledge_base",
            lambda **kwargs: (_ for _ in ()).throw(IMAAPIError("upstream")),
        )

        resp = client.post("/api/lab/ima/sync", json={"query": "x"})
        assert resp.status_code == 502

    def test_ima_search_not_configured(self, client):
        """未配置 → 400。"""
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="", ima_api_key="")
        resp = client.get("/api/lab/ima/search?query=gin")
        assert resp.status_code == 400

    def test_ima_search_empty_query(self, client, monkeypatch):
        """空 query → 400。"""
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")
        resp = client.get("/api/lab/ima/search?query=%20%20")
        assert resp.status_code == 400
        assert "query 必填" in resp.json()["detail"]

    def test_ima_search_success(self, client, monkeypatch):
        """搜索成功。"""
        from hermes_kb import ima_sync
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")
        monkeypatch.setattr(
            ima_sync, "search_knowledge",
            lambda query, kb_id, limit: {"items": [{"title": "Gin Tonic"}], "total": 1},
        )

        resp = client.get("/api/lab/ima/search?query=gin")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1

    def test_ima_search_config_error(self, client, monkeypatch):
        """IMAConfigError → 400。"""
        from hermes_kb import ima_sync
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")

        class IMAConfigError(Exception):
            pass

        class IMAAPIError(Exception):
            pass

        monkeypatch.setattr(ima_sync, "IMAConfigError", IMAConfigError)
        monkeypatch.setattr(ima_sync, "IMAAPIError", IMAAPIError)
        monkeypatch.setattr(
            ima_sync, "search_knowledge",
            lambda query, kb_id, limit: (_ for _ in ()).throw(IMAConfigError("bad")),
        )

        resp = client.get("/api/lab/ima/search?query=gin")
        assert resp.status_code == 400

    def test_ima_search_api_error(self, client, monkeypatch):
        """IMAAPIError → 502。"""
        from hermes_kb import ima_sync
        from hermes_kb.config import override_settings

        override_settings(ima_client_id="test-id", ima_api_key="test-key")

        class IMAConfigError(Exception):
            pass

        class IMAAPIError(Exception):
            pass

        monkeypatch.setattr(ima_sync, "IMAConfigError", IMAConfigError)
        monkeypatch.setattr(ima_sync, "IMAAPIError", IMAAPIError)
        monkeypatch.setattr(
            ima_sync, "search_knowledge",
            lambda query, kb_id, limit: (_ for _ in ()).throw(IMAAPIError("upstream")),
        )

        resp = client.get("/api/lab/ima/search?query=gin")
        assert resp.status_code == 502


# ===========================================================================
# /api/lab/recipes/{doc_id}/stats
# ===========================================================================
class TestRecipeStats:
    """配方统计端点。"""

    def test_recipe_stats_404(self, client):
        """配方不存在 → 404。"""
        resp = client.get("/api/lab/recipes/doc_nonexistent/stats")
        assert resp.status_code == 404

    def test_recipe_stats_not_recipe(self, client):
        """非配方文档 → 400。"""
        # 导入普通文档（category 默认为空，非 recipe）
        r = client.post(
            "/api/documents/import-text",
            json={"title": "普通文档", "content": "内容"},
        )
        doc_id = r.json()["doc_id"]
        resp = client.get(f"/api/lab/recipes/{doc_id}/stats")
        assert resp.status_code == 400
        assert "not a recipe" in resp.json()["detail"]

    def test_recipe_stats_with_frontmatter(self, client):
        """配方 content 含 abv/calories frontmatter 注释。"""
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            doc = Document(
                doc_id="test_recipe_stats_001",
                title="测试配方",
                content="<!-- abv: 0.18 -->\n<!-- calories: 120 -->\n配方内容",
                file_type="md",
                chunk_count=0,
                category="recipe",
            )
            session.add(doc)
            session.commit()

        resp = client.get("/api/lab/recipes/test_recipe_stats_001/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["abv"] == 0.18
        assert body["calories"] == 120.0
        assert body["source"] == "frontmatter"

    def test_recipe_stats_estimated(self, client):
        """配方无 frontmatter 但含 ingredients 注释 → 估算。"""
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            doc = Document(
                doc_id="test_recipe_stats_002",
                title="估算配方",
                content="<!-- ingredients: 金酒|味美思|苦精 -->\n配方内容",
                file_type="md",
                chunk_count=0,
                category="recipe",
            )
            session.add(doc)
            session.commit()

        resp = client.get("/api/lab/recipes/test_recipe_stats_002/stats")
        assert resp.status_code == 200
        body = resp.json()
        # 估算值应非 None
        assert body["abv"] is not None
        assert body["calories"] is not None
        assert body["source"] == "estimated"

    def test_recipe_stats_no_data(self, client):
        """配方无任何统计数据 → 全 None。"""
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            doc = Document(
                doc_id="test_recipe_stats_003",
                title="空配方",
                content="只有普通内容，无注释",
                file_type="md",
                chunk_count=0,
                category="recipe",
            )
            session.add(doc)
            session.commit()

        resp = client.get("/api/lab/recipes/test_recipe_stats_003/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["abv"] is None
        assert body["calories"] is None


# ===========================================================================
# /api/lab/translate-titles
# ===========================================================================
class TestTranslateTitles:
    """批量翻译配方标题。"""

    def test_translate_titles_no_data(self, client):
        """无配方数据 → 翻译 0 条。"""
        resp = client.post("/api/lab/translate-titles", json={"limit": 10})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["translated"] == 0

    def test_translate_titles_with_english(self, client):
        """含英文标题的配方被翻译（用不在 Mock 词典中的标题）。"""
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        # 用不在 _COMMON_TRANSLATIONS 中的虚构标题，确保走 LLM 翻译路径
        with get_session() as session:
            for i, title in enumerate([
                "Custom Cocktail Recipe XYZ",
                "Special Drink ABC",
                "Mystery Mix DEF",
            ]):
                session.add(Document(
                    doc_id=f"test_trans_{i}",
                    title=title,
                    content="content",
                    file_type="md",
                    chunk_count=0,
                    category="recipe",
                    source="iba",
                ))
            session.commit()

        resp = client.post("/api/lab/translate-titles", json={"limit": 10})
        assert resp.status_code == 200
        body = resp.json()
        # Mock 后端对未知标题返回原标题，仍计入 translated（尝试翻译）
        assert body["translated"] + body["skipped"] >= 1

    def test_translate_titles_skips_chinese(self, client):
        """已含中文的标题被跳过。"""
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            session.add(Document(
                doc_id="test_trans_zh",
                title="金汤力",
                content="content",
                file_type="md",
                chunk_count=0,
                category="recipe",
                source="iba",
            ))
            session.commit()

        resp = client.post("/api/lab/translate-titles", json={"limit": 10})
        assert resp.status_code == 200
        body = resp.json()
        # 已是中文，不翻译
        assert body["translated"] == 0

    def test_translate_titles_by_source(self, client):
        """按数据源筛选：只翻译 iba 源，thecocktaildb 源不被触及。"""
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            session.add(Document(
                doc_id="test_trans_src_iba",
                title="Custom IBA Drink XYZ",
                content="x",
                file_type="md",
                chunk_count=0,
                category="recipe",
                source="iba",
            ))
            session.add(Document(
                doc_id="test_trans_src_tctdb",
                title="Custom TCTDB Drink XYZ",
                content="x",
                file_type="md",
                chunk_count=0,
                category="recipe",
                source="thecocktaildb",
            ))
            session.commit()

        # 只翻译 iba 源
        resp = client.post("/api/lab/translate-titles", json={"source": "iba", "limit": 10})
        assert resp.status_code == 200
        body = resp.json()
        # iba 源有 1 条候选，translated + skipped 应为 1
        assert body["translated"] + body["skipped"] == 1


# ===========================================================================
# /api/lab/substitutes
# ===========================================================================
class TestSubstitutesEndpoint:
    """替代关系查询端点。"""

    def test_list_substitutes_all(self, client):
        """不传 canonical 返回全部。"""
        resp = client.get("/api/lab/substitutes")
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "items" in body
        assert body["total"] == len(body["items"])

    def test_list_substitutes_by_canonical(self, client):
        """传 canonical 返回单个材料的替代列表。"""
        # 先添加一个替代关系
        client.post("/api/lab/substitute", json={"canonical": "金酒", "substitute": "伏特加"})

        resp = client.get("/api/lab/substitutes?canonical=金酒")
        assert resp.status_code == 200
        body = resp.json()
        assert body["canonical"] == "金酒"
        assert "伏特加" in body["substitutes"]

    def test_list_substitutes_empty_canonical(self, client):
        """canonical 为空字符串走全部路径。"""
        resp = client.get("/api/lab/substitutes?canonical=")
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body

    def test_save_substitute_missing_fields(self, client):
        """canonical 或 substitute 缺失 → 400。"""
        resp = client.post("/api/lab/substitute", json={"canonical": "", "substitute": "x"})
        assert resp.status_code == 400

        resp = client.post("/api/lab/substitute", json={"canonical": "x", "substitute": ""})
        assert resp.status_code == 400

        resp = client.post("/api/lab/substitute", json={})
        assert resp.status_code == 400


# ===========================================================================
# /api/lab/recipes/{doc_id}/variant 错误路径
# ===========================================================================
class TestVariantErrorPaths:
    """变体创建错误路径。"""

    def test_create_variant_missing_variant_doc_id(self, client):
        """未传 variant_doc_id → 400。"""
        # 先创建一个配方
        r = client.post("/api/lab/recipes", json={
            "title": "基础配方",
            "content": "内容",
            "ingredients": ["金酒"],
        })
        doc_id = r.json()["doc_id"]

        resp = client.post(f"/api/lab/recipes/{doc_id}/variant", json={})
        assert resp.status_code == 400
        assert "variant_doc_id 必填" in resp.json()["detail"]

    def test_create_variant_nonexistent_base(self, client):
        """基础配方不存在 → 400。"""
        resp = client.post(
            "/api/lab/recipes/doc_nonexistent/variant",
            json={"variant_doc_id": "variant_1"},
        )
        assert resp.status_code == 400


# ===========================================================================
# /api/lab/sync-status
# ===========================================================================
class TestSyncStatus:
    """同步状态查询。"""

    def test_sync_status_empty(self, client):
        """空数据库返回零值。"""
        resp = client.get("/api/lab/sync-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_recipes"] == 0
        assert body["substitutes"] == 0
        assert isinstance(body["by_source"], dict)

    def test_sync_status_with_data(self, client):
        """有数据时正确统计。"""
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            for i in range(3):
                session.add(Document(
                    doc_id=f"test_status_{i}",
                    title=f"配方{i}",
                    content="x",
                    file_type="md",
                    chunk_count=0,
                    category="recipe",
                    source="iba",
                ))
            session.commit()

        resp = client.get("/api/lab/sync-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_recipes"] == 3
        assert body["by_source"].get("iba") == 3


# ===========================================================================
# 状态机错误路径补强
# ===========================================================================
class TestRecipeStateMachineErrors:
    """submit/approve/reject 错误路径。"""

    def test_submit_nonexistent_recipe(self, client):
        """提交不存在的配方 → 400。"""
        resp = client.post("/api/lab/recipes/doc_nonexistent/submit")
        assert resp.status_code == 400

    def test_approve_nonexistent_recipe(self, client):
        """审核不存在的配方 → 400。"""
        resp = client.post("/api/lab/recipes/doc_nonexistent/approve")
        assert resp.status_code == 400

    def test_reject_nonexistent_recipe(self, client):
        """驳回不存在的配方 → 400。"""
        resp = client.post(
            "/api/lab/recipes/doc_nonexistent/reject",
            json={"reason": "测试"},
        )
        assert resp.status_code == 400

    def test_approve_draft_recipe_fails(self, client):
        """审核 draft 状态配方（未 submit）→ 400。"""
        r = client.post("/api/lab/recipes", json={
            "title": "Draft",
            "content": "x",
            "ingredients": ["金酒"],
        })
        doc_id = r.json()["doc_id"]

        resp = client.post(f"/api/lab/recipes/{doc_id}/approve")
        assert resp.status_code == 400

    def test_reject_draft_recipe_fails(self, client):
        """驳回 draft 状态配方 → 400。"""
        r = client.post("/api/lab/recipes", json={
            "title": "Draft",
            "content": "x",
            "ingredients": ["金酒"],
        })
        doc_id = r.json()["doc_id"]

        resp = client.post(
            f"/api/lab/recipes/{doc_id}/reject",
            json={"reason": "测试"},
        )
        assert resp.status_code == 400

    def test_submit_already_submitted_fails(self, client):
        """重复提交 pending 状态配方 → 400。"""
        r = client.post("/api/lab/recipes", json={
            "title": "Draft",
            "content": "x",
            "ingredients": ["金酒"],
        })
        doc_id = r.json()["doc_id"]

        # 第一次提交成功
        resp = client.post(f"/api/lab/recipes/{doc_id}/submit")
        assert resp.status_code == 200

        # 第二次提交失败
        resp = client.post(f"/api/lab/recipes/{doc_id}/submit")
        assert resp.status_code == 400
