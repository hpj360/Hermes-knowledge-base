"""V4-Phase1 Obsidian vault 集成测试。

覆盖：
- frontmatter 解析（YAML + 降级模式）
- wikilink 提取
- 文件筛选（排除模式）
- sync_file 增量同步（导入/更新/跳过）
- scan_vault 全量扫描
- get_vault_status 状态查询
- export_recipe_to_vault 反向同步
- API 端点（/api/obsidian/status, /sync, /watch, /export）
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from sqlmodel import select


# ---------------------------------------------------------------------------
# frontmatter 解析
# ---------------------------------------------------------------------------
class TestParseFrontmatter:
    def test_parse_yaml_frontmatter(self):
        """标准 YAML frontmatter 解析。"""
        from hermes_kb.obsidian_sync import parse_frontmatter

        content = "---\ntitle: 测试笔记\ntags: [a, b]\n---\n\n正文内容"
        meta, body = parse_frontmatter(content)
        assert meta["title"] == "测试笔记"
        assert meta["tags"] == ["a", "b"]
        assert body.strip() == "正文内容"

    def test_no_frontmatter(self):
        """无 frontmatter 时返回空 dict + 原文。"""
        from hermes_kb.obsidian_sync import parse_frontmatter

        content = "# 标题\n\n正文"
        meta, body = parse_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_fallback_simple_kv(self, monkeypatch):
        """PyYAML 不可用时降级为简单 key: value 提取。"""
        from hermes_kb import obsidian_sync

        monkeypatch.setattr(obsidian_sync, "_YAML_AVAILABLE", False)
        content = "---\ntitle: 简单笔记\ncategory: encyclopedia\n---\n\n正文"
        meta, body = obsidian_sync.parse_frontmatter(content)
        assert meta["title"] == "简单笔记"
        assert meta["category"] == "encyclopedia"
        assert body.strip() == "正文"


# ---------------------------------------------------------------------------
# wikilink 提取
# ---------------------------------------------------------------------------
class TestExtractWikilinks:
    def test_extract_basic_wikilinks(self):
        from hermes_kb.obsidian_sync import extract_wikilinks

        content = "参见 [[金酒]] 和 [[朗姆酒|朗姆]] 以及 [[#标题]]"
        links = extract_wikilinks(content)
        assert links == ["金酒", "朗姆酒"]

    def test_extract_dedup(self):
        from hermes_kb.obsidian_sync import extract_wikilinks

        content = "[[金酒]] 和 [[金酒]] 和 [[金酒]]"
        links = extract_wikilinks(content)
        assert links == ["金酒"]

    def test_no_wikilinks(self):
        from hermes_kb.obsidian_sync import extract_wikilinks

        assert extract_wikilinks("普通文本无链接") == []


# ---------------------------------------------------------------------------
# 文件筛选
# ---------------------------------------------------------------------------
class TestFileFilter:
    def test_should_exclude_dotobsidian(self):
        from hermes_kb.obsidian_sync import _should_exclude

        assert _should_exclude(".obsidian/app.json", [".obsidian"])
        assert _should_exclude(".obsidian/workspace.json", [".obsidian"])

    def test_should_exclude_glob(self):
        from hermes_kb.obsidian_sync import _should_exclude

        assert _should_exclude("attachments/photo.png", ["*.png"])
        assert _should_exclude("notes/img.jpg", ["*.jpg"])

    def test_should_not_exclude_md(self):
        from hermes_kb.obsidian_sync import _should_exclude

        assert not _should_exclude("notes/recipe.md", [".obsidian", "*.png"])


# ---------------------------------------------------------------------------
# sync_file 增量同步
# ---------------------------------------------------------------------------
class TestSyncFile:
    def test_sync_file_imports_new_md(self, tmp_path: Path):
        """新文件导入并写入 source_path + meta。"""
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "test.md"
        note.write_text("---\ntitle: 测试\ncategory: recipe\n---\n\n# 配方\n- 金酒 50ml", encoding="utf-8")

        result = sync_file(note, vault)
        assert result["status"] == "imported"
        assert result["doc_id"]

        # 验证数据库
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            doc = session.get(Document, result["doc_id"])
            assert doc is not None
            assert doc.title == "测试"
            assert doc.source_path == "vault://test.md"
            assert doc.source == "obsidian"
            assert doc.file_type == "md"
            meta = json.loads(doc.meta)
            assert meta["vault_path"] == "test.md"
            assert meta["sync_source"] == "obsidian"
            assert "vault_mtime" in meta

    def test_sync_file_skips_unchanged(self, tmp_path: Path):
        """mtime 未变时跳过。"""
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "skip.md"
        note.write_text("# 内容\n\n正文", encoding="utf-8")

        # 首次导入
        r1 = sync_file(note, vault)
        assert r1["status"] == "imported"

        # 再次同步（mtime 未变）
        r2 = sync_file(note, vault)
        assert r2["status"] == "skipped"

    def test_sync_file_updates_on_change(self, tmp_path: Path):
        """文件修改后重新导入。"""
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "update.md"
        note.write_text("# 原始\n\n内容", encoding="utf-8")

        r1 = sync_file(note, vault)
        assert r1["status"] == "imported"

        # 修改文件内容 + 确保 mtime 变化
        time.sleep(0.05)
        note.write_text("# 修改后\n\n新内容", encoding="utf-8")

        r2 = sync_file(note, vault)
        assert r2["status"] == "updated"

    def test_sync_file_uses_filename_when_no_frontmatter_title(self, tmp_path: Path):
        """无 frontmatter title 时用文件名作为标题。"""
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "我的笔记.md"
        note.write_text("# 正文标题\n\n内容", encoding="utf-8")

        result = sync_file(note, vault)
        assert result["status"] == "imported"

        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            doc = session.get(Document, result["doc_id"])
            assert doc.title == "我的笔记"

    def test_sync_file_skips_non_md(self, tmp_path: Path):
        """非 .md 文件跳过。"""
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "readme.txt"
        note.write_text("文本内容", encoding="utf-8")

        result = sync_file(note, vault)
        assert result["status"] == "skipped"


# ---------------------------------------------------------------------------
# scan_vault 全量扫描
# ---------------------------------------------------------------------------
class TestScanVault:
    def test_scan_vault_imports_all_md(self, tmp_path: Path, monkeypatch):
        """全量扫描导入所有 .md 文件。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "note1.md").write_text("# 笔记 1", encoding="utf-8")
        (vault / "note2.md").write_text("---\ntitle: 笔记二\n---\n内容", encoding="utf-8")
        (vault / ".obsidian").mkdir()
        (vault / ".obsidian" / "app.json").write_text("{}", encoding="utf-8")
        (vault / "pic.png").write_bytes(b"\x89PNG")

        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        result = obsidian_sync.scan_vault()
        assert result.scanned == 2  # 仅 2 个 .md
        assert result.imported == 2
        assert result.failed == 0

    def test_scan_vault_incremental_skips(self, tmp_path: Path, monkeypatch):
        """增量扫描跳过未修改文件。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "inc.md"
        note.write_text("# 增量测试", encoding="utf-8")

        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        r1 = obsidian_sync.scan_vault()
        assert r1.imported == 1

        r2 = obsidian_sync.scan_vault(incremental=True)
        assert r2.skipped == 1
        assert r2.imported == 0

    def test_scan_vault_handles_empty_dir(self, tmp_path: Path, monkeypatch):
        """空 vault 目录扫描不报错。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "empty_vault"
        vault.mkdir()
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        result = obsidian_sync.scan_vault()
        assert result.scanned == 0
        assert result.imported == 0


# ---------------------------------------------------------------------------
# get_vault_status 状态查询
# ---------------------------------------------------------------------------
class TestVaultStatus:
    def test_status_disabled_when_not_configured(self, monkeypatch):
        """未配置 vault_path 时返回 enabled=False。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        monkeypatch.delenv("KB_VAULT_PATH", raising=False)
        reset_settings()
        status = obsidian_sync.get_vault_status()
        assert status.enabled is False
        assert status.synced_docs == 0

    def test_status_enabled_with_synced_docs(self, tmp_path: Path, monkeypatch):
        """配置并同步后返回 enabled=True + synced_docs。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "a.md").write_text("# A", encoding="utf-8")
        (vault / "b.md").write_text("# B", encoding="utf-8")

        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()
        obsidian_sync.scan_vault()

        status = obsidian_sync.get_vault_status()
        assert status.enabled is True
        assert status.synced_docs == 2
        assert status.vault_path == str(vault)


# ---------------------------------------------------------------------------
# 反向同步：UGC 配方导出
# ---------------------------------------------------------------------------
class TestExportRecipe:
    def test_export_ugc_recipe_to_vault(self, tmp_path: Path, monkeypatch):
        """UGC 配方导出为 .md 到 vault/Hermes/。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings
        from hermes_kb.recipe_crud import create_recipe

        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        # 创建 UGC 配方
        result = create_recipe(
            title="我的特调",
            ingredients=["金酒"],
            content="# 我的特调\n\n## 配方\n- 金酒 50ml",
        )
        doc_id = result["doc_id"]

        # 导出到 vault
        rel_path = obsidian_sync.export_recipe_to_vault(doc_id)
        assert rel_path.startswith("Hermes/")
        assert rel_path.endswith(".md")

        # 验证文件内容
        exported = (vault / rel_path).read_text(encoding="utf-8")
        assert "title: 我的特调" in exported
        assert "source: hermes-ugc" in exported
        assert doc_id in exported
        assert "# 我的特调" in exported

    def test_export_rejects_non_ugc(self, tmp_path: Path, monkeypatch):
        """非 UGC 文档拒绝导出。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings
        from hermes_kb.rag import ImportService

        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        # 创建非 UGC 文档
        svc = ImportService()
        r = svc.import_text(content="内容", title="普通文档", source="local")
        doc_id = r["doc_id"]

        with pytest.raises(obsidian_sync.VaultSyncError, match="仅 UGC"):
            obsidian_sync.export_recipe_to_vault(doc_id)


# ---------------------------------------------------------------------------
# API 端点测试
# ---------------------------------------------------------------------------
class TestObsidianAPI:
    def test_api_status_disabled(self, client):
        """未配置 vault 时 status 返回 enabled=False。"""
        resp = client.get("/api/obsidian/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False

    def test_api_sync_without_vault_returns_400(self, client):
        """未配置 vault 时 sync 返回 400。"""
        resp = client.post("/api/obsidian/sync")
        assert resp.status_code == 400
        assert "vault" in resp.json()["detail"].lower()

    def test_api_sync_with_vault(self, client, tmp_path: Path, monkeypatch):
        """配置 vault 后 sync 成功。"""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "api_test.md").write_text("# API 测试笔记", encoding="utf-8")

        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        from hermes_kb.config import reset_settings

        reset_settings()

        resp = client.post("/api/obsidian/sync")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["scanned"] == 1
        assert data["imported"] == 1

    def test_api_status_with_vault(self, client, tmp_path: Path, monkeypatch):
        """配置 vault 并同步后 status 返回 enabled + synced_docs。"""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "s1.md").write_text("# S1", encoding="utf-8")
        (vault / "s2.md").write_text("# S2", encoding="utf-8")

        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        from hermes_kb.config import reset_settings

        reset_settings()

        client.post("/api/obsidian/sync")
        resp = client.get("/api/obsidian/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["synced_docs"] == 2

    def test_api_watch_without_vault_returns_400(self, client):
        """未配置 vault 时 watch 返回 400。"""
        resp = client.post("/api/obsidian/watch?enable=true")
        assert resp.status_code == 400

    def test_api_export_without_vault_returns_400(self, client):
        """未配置 vault 时 export 返回 400。"""
        resp = client.post("/api/obsidian/export", json={"doc_id": "doc_test"})
        assert resp.status_code == 400

    def test_api_export_ugc_to_vault(self, client, tmp_path: Path, monkeypatch):
        """UGC 配方导出到 vault。"""
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        from hermes_kb.config import reset_settings

        reset_settings()

        from hermes_kb.recipe_crud import create_recipe

        result = create_recipe(
            title="导出测试",
            ingredients=["金酒"],
            content="# 导出测试\n\n配方内容",
        )

        resp = client.post("/api/obsidian/export", json={"doc_id": result["doc_id"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["path"].startswith("Hermes/")
        assert (vault / data["path"]).exists()


# ---------------------------------------------------------------------------
# 集成：wikilink 存入 meta
# ---------------------------------------------------------------------------
class TestWikilinkIntegration:
    def test_wikilinks_stored_in_meta(self, tmp_path: Path):
        """wikilink 提取后存入 Document.meta.wikilinks。"""
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "links.md"
        note.write_text(
            "# 双链笔记\n\n参见 [[金酒]] 和 [[朗姆酒]] 以及 [[金酒]]",
            encoding="utf-8",
        )

        result = sync_file(note, vault)
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            doc = session.get(Document, result["doc_id"])
            meta = json.loads(doc.meta)
            assert meta["wikilinks"] == ["金酒", "朗姆酒"]


# ---------------------------------------------------------------------------
# V4-Phase2：wikilink → DocumentTag 关联
# ---------------------------------------------------------------------------
class TestWikilinkResolution:
    def test_resolve_wikilinks_creates_tags_and_links(self, tmp_path: Path):
        """resolve_wikilinks 创建 Tag + DocumentTag 关联。"""
        from hermes_kb.obsidian_sync import resolve_wikilinks

        # 先导入一个文档
        from hermes_kb.rag import ImportService

        svc = ImportService()
        r = svc.import_text(content="测试内容", title="测试文档")
        doc_id = r["doc_id"]

        # 解析 wikilinks
        count = resolve_wikilinks(doc_id, ["金酒", "朗姆酒"])
        assert count == 2

        from hermes_kb.database import get_session
        from hermes_kb.models import DocumentTag, Tag

        with get_session() as session:
            # 验证 Tag 创建
            tags = session.exec(select(Tag)).all()
            tag_names = {t.name for t in tags}
            assert "金酒" in tag_names
            assert "朗姆酒" in tag_names

            # 验证 DocumentTag 关联
            links = session.exec(
                select(DocumentTag).where(DocumentTag.doc_id == doc_id)
            ).all()
            assert len(links) == 2

    def test_resolve_wikilinks_dedup_tags(self, tmp_path: Path):
        """已存在的 Tag 不重复创建，仅创建关联。"""
        from hermes_kb.obsidian_sync import resolve_wikilinks
        from hermes_kb.rag import ImportService

        svc = ImportService()
        r1 = svc.import_text(content="文档 1", title="文档 1")
        r2 = svc.import_text(content="文档 2", title="文档 2")

        # 两个文档都引用 [[金酒]]
        resolve_wikilinks(r1["doc_id"], ["金酒"])
        resolve_wikilinks(r2["doc_id"], ["金酒"])

        from hermes_kb.database import get_session
        from hermes_kb.models import Tag

        with get_session() as session:
            gin_tags = session.exec(select(Tag).where(Tag.name == "金酒")).all()
            assert len(gin_tags) == 1  # 只创建一个 Tag

    def test_resolve_wikilinks_clears_old_links(self, tmp_path: Path):
        """重新解析时清理旧关联，避免残留。"""
        from hermes_kb.obsidian_sync import resolve_wikilinks
        from hermes_kb.rag import ImportService

        svc = ImportService()
        r = svc.import_text(content="文档", title="文档")
        doc_id = r["doc_id"]

        # 首次解析 3 个 wikilink
        resolve_wikilinks(doc_id, ["A", "B", "C"])

        # 修改为 1 个 wikilink
        resolve_wikilinks(doc_id, ["A"])

        from hermes_kb.database import get_session
        from hermes_kb.models import DocumentTag

        with get_session() as session:
            links = session.exec(
                select(DocumentTag).where(DocumentTag.doc_id == doc_id)
            ).all()
            assert len(links) == 1  # 仅保留 A

    def test_resolve_empty_wikilinks_clears_all(self, tmp_path: Path):
        """空 wikilink 列表清理所有关联。"""
        from hermes_kb.obsidian_sync import resolve_wikilinks
        from hermes_kb.rag import ImportService

        svc = ImportService()
        r = svc.import_text(content="文档", title="文档")
        doc_id = r["doc_id"]

        resolve_wikilinks(doc_id, ["A", "B"])
        count = resolve_wikilinks(doc_id, [])
        assert count == 0

        from hermes_kb.database import get_session
        from hermes_kb.models import DocumentTag

        with get_session() as session:
            links = session.exec(
                select(DocumentTag).where(DocumentTag.doc_id == doc_id)
            ).all()
            assert len(links) == 0

    def test_sync_file_auto_resolves_wikilinks(self, tmp_path: Path):
        """sync_file 同步时自动调用 resolve_wikilinks 创建标签关联。"""
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "auto_wiki.md"
        note.write_text(
            "# 自动双链\n\n参见 [[威士忌]] 和 [[苦精]]",
            encoding="utf-8",
        )

        result = sync_file(note, vault)
        from hermes_kb.database import get_session
        from hermes_kb.models import DocumentTag

        with get_session() as session:
            links = session.exec(
                select(DocumentTag).where(DocumentTag.doc_id == result["doc_id"])
            ).all()
            assert len(links) == 2

    def test_wikilink_tag_color(self, tmp_path: Path):
        """wikilink 创建的 Tag 使用 wine 色标记。"""
        from hermes_kb.obsidian_sync import resolve_wikilinks
        from hermes_kb.rag import ImportService

        svc = ImportService()
        r = svc.import_text(content="文档", title="文档")
        resolve_wikilinks(r["doc_id"], ["新标签"])

        from hermes_kb.database import get_session
        from hermes_kb.models import Tag

        with get_session() as session:
            tag = session.exec(select(Tag).where(Tag.name == "新标签")).first()
            assert tag is not None
            assert tag.color == "#6b2c2c"
