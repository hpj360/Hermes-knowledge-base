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

    def test_sync_file_preserves_doc_id_on_update(self, tmp_path: Path):
        """P1 修复：更新时 doc_id 保持不变（引用/收藏/评分不失效）。"""
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "stable.md"
        note.write_text("# 第一版\n\n内容 A", encoding="utf-8")

        r1 = sync_file(note, vault)
        doc_id1 = r1["doc_id"]

        # 修改内容后再次同步
        time.sleep(0.05)
        note.write_text("# 第二版\n\n内容 B", encoding="utf-8")
        r2 = sync_file(note, vault)

        # doc_id 必须保持一致
        assert r2["doc_id"] == doc_id1
        assert r2["status"] == "updated"

        # 数据库中仍是同一个文档，且内容已更新
        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            docs = session.exec(select(Document)).all()
            assert len(docs) == 1  # 没有产生重复文档
            doc = docs[0]
            assert doc.doc_id == doc_id1
            assert "内容 B" in doc.content

    def test_remove_synced_doc_removes_document(self, tmp_path: Path):
        """P0 修复：remove_synced_doc 删除 vault 文件后清理对应文档。"""
        from hermes_kb.obsidian_sync import remove_synced_doc, sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "del.md"
        note.write_text("# 待删除\n\n内容", encoding="utf-8")

        r = sync_file(note, vault)
        assert r["status"] == "imported"

        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        # 删除前存在
        with get_session() as session:
            assert session.get(Document, r["doc_id"]) is not None

        # 移除同步文档
        removed = remove_synced_doc("vault://del.md")
        assert removed is True

        # 删除后文档被清理
        with get_session() as session:
            assert session.get(Document, r["doc_id"]) is None

        # 幂等：再次删除返回 False
        assert remove_synced_doc("vault://del.md") is False

    def test_remove_synced_doc_noop_for_unsynced(self, tmp_path: Path):
        """P0 修复：未同步过的路径移除返回 False，不报错。"""
        from hermes_kb.obsidian_sync import remove_synced_doc

        assert remove_synced_doc("vault://nonexistent.md") is False

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
        assert "source: ugc" in exported
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


# ---------------------------------------------------------------------------
# P0 修复：事件处理器（删除 / 重命名）
# ---------------------------------------------------------------------------
class TestEventHandler:
    def _make_handler(self, tmp_path: Path):
        from hermes_kb import obsidian_sync

        vault = tmp_path / "vault"
        vault.mkdir()
        return vault, obsidian_sync._VaultEventHandler(vault)

    def test_on_deleted_removes_doc(self, tmp_path: Path):
        """P0 修复：on_deleted 移除被删除文件对应的文档。"""
        from watchdog.events import FileDeletedEvent

        from hermes_kb.obsidian_sync import sync_file

        vault, handler = self._make_handler(tmp_path)
        note = vault / "gone.md"
        note.write_text("# 将删除\n\n内容", encoding="utf-8")
        r = sync_file(note, vault)
        assert r["status"] == "imported"

        # 模拟文件删除事件
        handler.on_deleted(FileDeletedEvent(str(note)))

        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        with get_session() as session:
            assert session.get(Document, r["doc_id"]) is None

    def test_on_moved_removes_old_and_pending_new(self, tmp_path: Path):
        """P0 修复：on_moved 移除旧文档并调度新路径同步。"""
        from watchdog.events import FileMovedEvent

        from hermes_kb.obsidian_sync import sync_file

        vault, handler = self._make_handler(tmp_path)
        old = vault / "old.md"
        old.write_text("# 旧名\n\n内容", encoding="utf-8")
        r = sync_file(old, vault)
        assert r["status"] == "imported"

        new = vault / "new.md"
        # 模拟重命名事件
        handler.on_moved(FileMovedEvent(str(old), str(new)))

        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        # 旧文档已移除，新路径已进入 pending 待同步
        with get_session() as session:
            assert session.get(Document, r["doc_id"]) is None
        with handler._lock:
            assert str(new) in handler._pending


# ---------------------------------------------------------------------------
# 补充覆盖：缺失分支
# ---------------------------------------------------------------------------
class TestObsidianCoverage:
    def test_should_exclude_full_relpath(self):
        """完整相对路径匹配模式（非段匹配）。"""
        from hermes_kb.obsidian_sync import _should_exclude

        assert _should_exclude("notes/recipe.md", ["notes/*.md"])

    def test_list_vault_files_excludes_md_in_private(self, tmp_path: Path):
        """排除模式覆盖目录下的 .md 文件也被过滤。"""
        from hermes_kb.obsidian_sync import list_vault_files

        vault = tmp_path / "vault"
        private = vault / ".obsidian" / "plugins"
        private.mkdir(parents=True)
        (private / "conf.md").write_text("# 内部", encoding="utf-8")
        (vault / "ok.md").write_text("# 公开", encoding="utf-8")

        files = list_vault_files(vault, [".obsidian"])
        assert [f.name for f in files] == ["ok.md"]

    def test_parse_frontmatter_yaml_error_falls_back(self, monkeypatch):
        """YAML 解析异常降级为简单 key: value 提取。"""
        import yaml

        from hermes_kb import obsidian_sync

        def boom(stream):
            raise yaml.YAMLError("bad yaml")

        monkeypatch.setattr(yaml, "safe_load", boom)
        meta, body = obsidian_sync.parse_frontmatter(
            "---\ntitle: 回退\n# 注释行\n\n---\n正文"
        )
        assert meta["title"] == "回退"
        assert body.strip() == "正文"

    def test_sync_file_skips_empty_content(self, tmp_path: Path):
        """内容为空白时跳过。"""
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "blank.md"
        note.write_text("   \n\n  ", encoding="utf-8")
        result = sync_file(note, vault)
        assert result["status"] == "skipped"
        assert result["reason"] == "empty_content"

    def test_sync_file_meta_decode_error_then_updates(self, tmp_path: Path):
        """存量 meta 非 JSON 时忽略并继续更新。"""
        from hermes_kb.database import get_session
        from hermes_kb.models import Document
        from hermes_kb.obsidian_sync import sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "badmeta.md"
        note.write_text("# 第一版", encoding="utf-8")
        r1 = sync_file(note, vault)
        assert r1["status"] == "imported"

        # 破坏 meta
        with get_session() as session:
            doc = session.get(Document, r1["doc_id"])
            doc.meta = "{not json"
            session.add(doc)
            session.commit()

        time.sleep(0.05)
        note.write_text("# 第二版", encoding="utf-8")
        r2 = sync_file(note, vault)
        assert r2["status"] == "updated"

    def test_sync_file_wikilink_resolve_error_logged(self, tmp_path: Path, monkeypatch):
        """wikilink 解析异常不阻塞同步。"""
        from hermes_kb import obsidian_sync

        def boom(doc_id, wikilinks):
            raise RuntimeError("tag db down")

        monkeypatch.setattr(obsidian_sync, "resolve_wikilinks", boom)
        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "wiki_err.md"
        note.write_text("# 笔记\n\n参见 [[金酒]]", encoding="utf-8")
        result = obsidian_sync.sync_file(note, vault)
        assert result["status"] == "imported"

    def test_resolve_wikilinks_skips_empty_and_long(self, tmp_path: Path):
        """跳过空名称与超长名称。"""
        from hermes_kb.obsidian_sync import resolve_wikilinks
        from hermes_kb.rag import ImportService

        svc = ImportService()
        r = svc.import_text(content="内容", title="文档")
        count = resolve_wikilinks(r["doc_id"], ["", "x" * 40, "有效标签"])
        assert count == 1

    def test_remove_synced_doc_doc_missing_in_get(self, monkeypatch):
        """_find_existing_doc 命中但 get 缺失 → False。"""
        from hermes_kb import obsidian_sync

        class FakeDoc:
            doc_id = "ghost"

        monkeypatch.setattr(
            obsidian_sync, "_find_existing_doc", lambda sp: FakeDoc()
        )
        assert obsidian_sync.remove_synced_doc("vault://ghost") is False

    def test_scan_vault_raises_when_disabled(self, monkeypatch):
        """vault 未配置时 scan_vault 抛 VaultConfigError。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        monkeypatch.delenv("KB_VAULT_PATH", raising=False)
        reset_settings()
        with pytest.raises(obsidian_sync.VaultConfigError):
            obsidian_sync.scan_vault()

    def test_scan_vault_counts_failed_on_exception(self, tmp_path, monkeypatch):
        """单文件同步异常计入 failed + errors。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "bad.md").write_text("# 会失败", encoding="utf-8")
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        def boom(f, vault_root, importer):
            raise RuntimeError("boom")

        monkeypatch.setattr(obsidian_sync, "sync_file", boom)
        result = obsidian_sync.scan_vault()
        assert result.scanned == 1
        assert result.failed == 1
        assert len(result.errors) == 1

    def test_scan_vault_unknown_status_skipped(self, tmp_path, monkeypatch):
        """sync_file 返回未知状态时计入 skipped。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "weird.md").write_text("# 未知", encoding="utf-8")
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        def unknown(f, vault_root, importer):
            return {"status": "weird"}

        monkeypatch.setattr(obsidian_sync, "sync_file", unknown)
        result = obsidian_sync.scan_vault()
        assert result.scanned == 1
        assert result.skipped == 1

    def test_list_synced_docs(self, tmp_path: Path):
        """list_synced_docs 返回 obsidian 文档详情。"""
        from hermes_kb.database import get_session
        from hermes_kb.models import Document
        from hermes_kb.obsidian_sync import list_synced_docs, sync_file

        vault = tmp_path / "vault"
        vault.mkdir()
        n1 = vault / "a.md"
        n1.write_text("---\ntitle: A\ncategory: encyclopedia\n---\n\n内容A", encoding="utf-8")
        n2 = vault / "b.md"
        n2.write_text("# B", encoding="utf-8")
        sync_file(n1, vault)
        sync_file(n2, vault)

        items = list_synced_docs()
        assert len(items) == 2
        titles = {i["title"] for i in items}
        assert titles == {"A", "b"}
        assert all(i["vault_path"] for i in items)
        assert all(i["chunk_count"] is not None for i in items)

        # 破坏一个 meta 验证 JSON 解码降级
        with get_session() as session:
            doc = session.exec(
                select(Document).where(Document.source == "obsidian")
            ).first()
            doc.meta = "{oops"
            session.add(doc)
            session.commit()
        items = list_synced_docs()
        assert len(items) == 2

    def test_get_vault_status_query_error(self, tmp_path, monkeypatch):
        """状态查询异常时软降级。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        def boom():
            raise RuntimeError("db down")

        monkeypatch.setattr(obsidian_sync, "get_session", boom)
        status = obsidian_sync.get_vault_status()
        assert status.enabled is True
        assert status.synced_docs == 0

    def test_export_doc_to_vault_missing(self, tmp_path, monkeypatch):
        """导出不存在的文档抛 VaultSyncError。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()
        with pytest.raises(obsidian_sync.VaultSyncError, match="文档不存在"):
            obsidian_sync.export_doc_to_vault("nonexistent")

    def test_export_doc_to_vault_not_configured(self, monkeypatch):
        """vault 未配置时导出抛 VaultConfigError。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        monkeypatch.delenv("KB_VAULT_PATH", raising=False)
        reset_settings()
        with pytest.raises(obsidian_sync.VaultConfigError):
            obsidian_sync.export_doc_to_vault("any")

    def test_export_recipe_to_vault_missing(self, tmp_path, monkeypatch):
        """导出不存在的 UGC 配方抛 VaultSyncError。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()
        with pytest.raises(obsidian_sync.VaultSyncError, match="文档不存在"):
            obsidian_sync.export_recipe_to_vault("nonexistent")


class TestEventHandlerCoverage:
    def _make_handler(self, tmp_path: Path):
        from hermes_kb import obsidian_sync

        vault = tmp_path / "vault"
        vault.mkdir()
        return vault, obsidian_sync._VaultEventHandler(vault)

    def test_on_any_event_schedules_md(self, tmp_path: Path):
        """created/modified .md 事件进入防抖队列。"""
        from watchdog.events import FileCreatedEvent, FileModifiedEvent

        vault, handler = self._make_handler(tmp_path)
        handler.on_any_event(FileCreatedEvent(str(vault / "n.md")))
        handler.on_any_event(FileModifiedEvent(str(vault / "m.md")))
        with handler._lock:
            assert str(vault / "n.md") in handler._pending
            assert str(vault / "m.md") in handler._pending

    def test_on_any_event_ignores_dir_non_md_moved(self, tmp_path: Path):
        """目录 / 非 md / moved 事件忽略。"""
        from watchdog.events import FileCreatedEvent, FileMovedEvent

        vault, handler = self._make_handler(tmp_path)

        dir_ev = FileCreatedEvent(str(vault / "dir"))
        dir_ev.is_directory = True
        handler.on_any_event(dir_ev)

        handler.on_any_event(FileCreatedEvent(str(vault / "a.txt")))
        handler.on_any_event(FileMovedEvent(str(vault / "a.md"), str(vault / "b.md")))

        with handler._lock:
            assert handler._pending == {}

    def test_on_deleted_ignores_dir_and_non_md(self, tmp_path: Path):
        from watchdog.events import FileDeletedEvent

        vault, handler = self._make_handler(tmp_path)
        dir_ev = FileDeletedEvent(str(vault / "dir"))
        dir_ev.is_directory = True
        handler.on_deleted(dir_ev)
        handler.on_deleted(FileDeletedEvent(str(vault / "x.txt")))  # 不报错即可
        assert handler._pending == {}

    def test_on_moved_ignores_directory(self, tmp_path: Path):
        from watchdog.events import FileMovedEvent

        vault, handler = self._make_handler(tmp_path)
        ev = FileMovedEvent(str(vault / "a"), str(vault / "b"))
        ev.is_directory = True
        handler.on_moved(ev)
        assert handler._pending == {}

    def test_remove_by_path_outside_vault(self, tmp_path: Path):
        """路径不在 vault 内时静默忽略。"""
        _, handler = self._make_handler(tmp_path)
        handler._remove_by_path(Path("C:/outside/x.md"))  # 不抛异常即可

    def test_remove_by_path_error_logged(self, tmp_path: Path, monkeypatch):
        """移除文档异常被捕获。"""
        from hermes_kb import obsidian_sync

        vault, handler = self._make_handler(tmp_path)

        def boom(source_path):
            raise RuntimeError("db down")

        monkeypatch.setattr(obsidian_sync, "remove_synced_doc", boom)
        handler._remove_by_path(vault / "gone.md")  # 不抛异常即可

    def test_flush_loop_syncs_pending(self, tmp_path: Path):
        """防抖线程按计划同步 pending 文件。"""
        from sqlmodel import select

        from hermes_kb.database import get_session
        from hermes_kb.models import Document

        vault, handler = self._make_handler(tmp_path)
        note = vault / "flush.md"
        note.write_text("# 防抖同步", encoding="utf-8")
        with handler._lock:
            handler._pending[str(note)] = time.time() - 1
        # 防抖线程首次同步会触发引擎初始化（alembic 迁移约 1-2s），
        # 固定 sleep 不可靠，改为轮询等待文档入库（上限 5s，提前出现即返回）
        deadline = time.time() + 5
        doc = None
        while time.time() < deadline:
            with get_session() as session:
                doc = session.exec(
                    select(Document).where(Document.source == "obsidian")
                ).first()
            if doc is not None:
                break
            time.sleep(0.2)
        assert doc is not None

    def test_flush_loop_error_logged(self, tmp_path: Path, monkeypatch):
        """防抖同步异常被捕获。"""
        from hermes_kb import obsidian_sync

        vault, handler = self._make_handler(tmp_path)
        note = vault / "boom.md"
        note.write_text("# 失败", encoding="utf-8")

        def boom(path, vault_root):
            raise RuntimeError("boom")

        monkeypatch.setattr(obsidian_sync, "sync_file", boom)
        with handler._lock:
            handler._pending[str(note)] = time.time() - 1
        time.sleep(0.7)  # 线程内异常应被捕获，不向上抛出


class TestVaultWatcher:
    def test_init_raises_without_watchdog(self, monkeypatch):
        """watchdog 不可用时构造抛 VaultConfigError。"""
        from hermes_kb import obsidian_sync

        monkeypatch.setattr(obsidian_sync, "_WATCHDOG_AVAILABLE", False)
        with pytest.raises(obsidian_sync.VaultConfigError):
            obsidian_sync.VaultWatcher()

    def test_start_requires_enabled(self, monkeypatch):
        """vault 未启用时 start 抛 VaultConfigError。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        monkeypatch.delenv("KB_VAULT_PATH", raising=False)
        reset_settings()
        watcher = obsidian_sync.VaultWatcher()
        with pytest.raises(obsidian_sync.VaultConfigError):
            watcher.start()

    def test_start_stop_roundtrip(self, tmp_path: Path, monkeypatch):
        """启用后 start → is_running=True，stop → False。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        watcher = obsidian_sync.VaultWatcher()
        assert watcher.is_running is False
        watcher.start()
        assert watcher.is_running is True
        watcher.stop()
        assert watcher.is_running is False

    def test_start_watcher_singleton(self, tmp_path: Path, monkeypatch):
        """全局 start_watcher 幂等，stop_watcher 清理。"""
        from hermes_kb import obsidian_sync
        from hermes_kb.config import reset_settings

        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("KB_VAULT_PATH", str(vault))
        reset_settings()

        obsidian_sync._watcher = None
        try:
            assert obsidian_sync.start_watcher() is True
            assert obsidian_sync.start_watcher() is True  # 幂等
            obsidian_sync.stop_watcher()
            assert obsidian_sync._watcher is None
        finally:
            obsidian_sync.stop_watcher()
            obsidian_sync._watcher = None

    def test_start_watcher_fails_gracefully(self, monkeypatch):
        """start 失败返回 False。"""
        from hermes_kb import obsidian_sync

        class _FakeWatcher:
            def start(self):
                raise obsidian_sync.VaultConfigError("no vault")

        monkeypatch.setattr(obsidian_sync, "VaultWatcher", _FakeWatcher)
        obsidian_sync._watcher = None
        try:
            assert obsidian_sync.start_watcher() is False
        finally:
            obsidian_sync._watcher = None

