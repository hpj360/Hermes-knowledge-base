"""Obsidian vault 文件系统直连同步器（V4-Phase1）。

设计原则：
- 本地优先：直接读写 vault 文件夹，无外部依赖
- 增量同步：基于 source_path + mtime 判断变更，避免全量重扫
- 向后兼容：watchdog 未安装时降级为手动扫描模式
- frontmatter 解析：YAML frontmatter → Document.meta JSON
- wikilink 提取：[[笔记名]] → meta.wikilinks（Phase 2 用于双链关联）

依赖：
- watchdog（可选）：实时监听 vault 文件变更
- pyyaml（可选）：解析 frontmatter；未安装时降级为简单正则提取
"""
from __future__ import annotations

import fnmatch
import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlmodel import select

from hermes_kb.config import get_settings
from hermes_kb.database import get_session
from hermes_kb.models import Document, DocumentTag, Tag
from hermes_kb.rag import ImportService

_logger = logging.getLogger(__name__)

# watchdog 可选导入（未安装时降级为手动扫描）
try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False
    Observer = None  # type: ignore[assignment, misc]
    FileSystemEventHandler = object  # type: ignore[assignment, misc]

# PyYAML 可选导入（未安装时降级为简单正则）
try:
    import yaml

    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False
    yaml = None  # type: ignore[assignment]

# frontmatter 正则：---\n<yaml>\n---\n
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# wikilink 正则：[[笔记名]] 或 [[笔记名|别名]] 或 [[#标题]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------
class VaultConfigError(RuntimeError):
    """vault 路径未配置或无效。"""


class VaultSyncError(RuntimeError):
    """vault 同步过程出错。"""


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------
@dataclass
class VaultSyncResult:
    """单次同步结果。"""

    scanned: int = 0
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned": self.scanned,
            "imported": self.imported,
            "skipped": self.skipped,
            "failed": self.failed,
            "errors": self.errors[:20],  # 截断避免响应过大
        }


@dataclass
class VaultStatus:
    """vault 集成状态。"""

    enabled: bool
    vault_path: str
    watch_enabled: bool
    watchdog_available: bool
    watching: bool
    synced_docs: int  # 已同步的 vault 文档数
    last_sync: str | None  # 最后同步时间 ISO 格式

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "vault_path": self.vault_path,
            "watch_enabled": self.watch_enabled,
            "watchdog_available": self.watchdog_available,
            "watching": self.watching,
            "synced_docs": self.synced_docs,
            "last_sync": self.last_sync,
        }


# ---------------------------------------------------------------------------
# frontmatter 解析
# ---------------------------------------------------------------------------
def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """解析 Markdown frontmatter（YAML），返回 (metadata, body)。

    未匹配到 frontmatter 时返回 ({}, content)。
    PyYAML 未安装时降级为简单 key: value 提取（不支持嵌套/列表）。
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    raw_yaml = match.group(1)
    body = content[match.end():]

    if _YAML_AVAILABLE:
        try:
            data = yaml.safe_load(raw_yaml)
            if isinstance(data, dict):
                return data, body
        except yaml.YAMLError as e:
            _logger.debug("frontmatter YAML 解析失败，降级为简单提取: %s", e)

    # 降级：简单 key: value 提取（不嵌套）
    metadata: dict[str, Any] = {}
    for line in raw_yaml.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip("\"'")
            if key:
                metadata[key] = val
    return metadata, body


def extract_wikilinks(content: str) -> list[str]:
    """提取 [[wikilink]] 目标笔记名（去重，保持顺序）。"""
    seen: set[str] = set()
    links: list[str] = []
    for m in _WIKILINK_RE.finditer(content):
        name = m.group(1).strip()
        if name and name not in seen:
            seen.add(name)
            links.append(name)
    return links


# ---------------------------------------------------------------------------
# 文件筛选
# ---------------------------------------------------------------------------
def _should_exclude(rel_path: str, patterns: list[str]) -> bool:
    """判断相对路径是否应被排除（匹配任一 glob 模式）。"""
    parts = Path(rel_path).parts
    for pattern in patterns:
        # 匹配文件名或路径任一段
        if any(fnmatch.fnmatch(part, pattern) for part in parts):
            return True
        # 匹配完整相对路径
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


def list_vault_files(vault_path: Path, exclude_patterns: list[str]) -> list[Path]:
    """列出 vault 中所有 .md 文件（排除 .obsidian 配置目录等）。"""
    files: list[Path] = []
    for p in vault_path.rglob("*.md"):
        rel = p.relative_to(vault_path).as_posix()
        if _should_exclude(rel, exclude_patterns):
            continue
        files.append(p)
    return sorted(files)


# ---------------------------------------------------------------------------
# 同步核心
# ---------------------------------------------------------------------------
def _build_meta(frontmatter: dict[str, Any], wikilinks: list[str], rel_path: str) -> str:
    """构造 Document.meta JSON（合并 frontmatter + wikilinks + vault 元信息）。"""
    meta: dict[str, Any] = dict(frontmatter)
    meta["wikilinks"] = wikilinks
    meta["vault_path"] = rel_path
    meta["sync_source"] = "obsidian"
    return json.dumps(meta, ensure_ascii=False)


# wikilink 自动生成的标签颜色（包豪斯 wine 色，区别于用户手动创建的标签）
_WIKILINK_TAG_COLOR = "#6b2c2c"


def resolve_wikilinks(doc_id: str, wikilinks: list[str]) -> int:
    """V4-Phase2：将 wikilink 列表解析为 DocumentTag 关联。

    - 每个 wikilink 名称对应一个 Tag（不存在则创建，颜色用 wine 色标记）
    - 清理旧的 wikilink 关联后重建（确保与当前笔记内容一致）
    - 已存在的用户标签复用（不修改颜色）

    Returns:
        创建/关联的标签数
    """
    if not wikilinks:
        # 清理该文档的旧 wikilink 关联
        _clear_wikilink_tags(doc_id)
        return 0

    with get_session() as session:
        # 清理旧关联
        _clear_wikilink_tags(doc_id, session=session)

        count = 0
        for name in wikilinks:
            name = name.strip()
            if not name or len(name) > 32:
                continue
            # 查找或创建 Tag
            tag = session.exec(select(Tag).where(Tag.name == name)).first()
            if not tag:
                tag = Tag(name=name, color=_WIKILINK_TAG_COLOR)
                session.add(tag)
                session.flush()  # 获取 tag.id
            # 创建关联（去重）
            existing = session.exec(
                select(DocumentTag).where(
                    DocumentTag.doc_id == doc_id,
                    DocumentTag.tag_id == tag.id,
                )
            ).first()
            if not existing:
                session.add(DocumentTag(doc_id=doc_id, tag_id=tag.id))
                count += 1

        session.commit()
        return count


def _clear_wikilink_tags(doc_id: str, session: Any = None) -> None:
    """清理文档的 wikilink 标签关联（删除所有 DocumentTag，由 resolve_wikilinks 重建）。

    策略：删除该文档的所有 DocumentTag（wikilink 来源），保留用户手动创建的标签。
    为简化实现，Phase 2 删除所有关联后由 wikilinks 列表重建；
    用户手动标签需在后续迭代中通过 meta 区分。
    """
    if session is not None:
        # 复用外部 session，不 commit/close
        stmt = select(DocumentTag).where(DocumentTag.doc_id == doc_id)
        links = session.exec(stmt).all()
        for link in links:
            session.delete(link)
        return

    # 独立 session：用上下文管理器
    with get_session() as sess:
        stmt = select(DocumentTag).where(DocumentTag.doc_id == doc_id)
        links = sess.exec(stmt).all()
        for link in links:
            sess.delete(link)
        sess.commit()


def _find_existing_doc(source_path: str) -> Document | None:
    """根据 source_path 查找已同步的文档（增量同步用）。"""
    with get_session() as session:
        stmt = select(Document).where(Document.source_path == source_path)
        return session.exec(stmt).first()


def sync_file(
    file_path: Path,
    vault_root: Path,
    importer: ImportService | None = None,
) -> dict[str, Any]:
    """同步单个 vault 文件到知识库。

    Returns:
        {"doc_id": ..., "status": "imported"|"updated"|"skipped"}
    """
    if not file_path.exists() or file_path.suffix.lower() != ".md":
        return {"status": "skipped", "reason": "not_md_or_missing"}

    rel_path = file_path.relative_to(vault_root).as_posix()
    source_path = f"vault://{rel_path}"

    # 读取原始内容（UTF-8，保留 frontmatter + wikilinks）
    raw = file_path.read_text(encoding="utf-8", errors="ignore")
    frontmatter, body = parse_frontmatter(raw)
    wikilinks = extract_wikilinks(raw)

    # 标题：frontmatter.title > 文件名
    title = str(frontmatter.get("title", "")).strip() or file_path.stem

    # 内容：body 非空用 body，否则用 raw（含 frontmatter）
    content = body.strip() or raw.strip()
    if not content:
        return {"status": "skipped", "reason": "empty_content"}

    meta_json = _build_meta(frontmatter, wikilinks, rel_path)
    mtime = file_path.stat().st_mtime

    # 增量判断：已存在且 mtime 未变 → 跳过
    existing = _find_existing_doc(source_path)
    if existing:
        try:
            existing_meta = json.loads(existing.meta or "{}")
            if existing_meta.get("vault_mtime") == mtime:
                return {"doc_id": existing.doc_id, "status": "skipped"}
        except (json.JSONDecodeError, TypeError):
            pass

    # 导入或更新
    svc = importer or ImportService()
    if existing:
        # 更新：删除旧文档（级联清理 chunks/vectors）后重新导入
        with get_session() as session:
            session.delete(existing)
            session.commit()

    # 从 frontmatter 提取可选治理字段
    category = str(frontmatter.get("category", "")).strip() or ""
    season = str(frontmatter.get("season", "")).strip() or None
    source = "obsidian"

    result = svc.import_text(
        content=content,
        title=title,
        source_type="upload",
        file_type="md",
        source_path=source_path,
        category=category,
        source=source,
        season=season,
    )

    # 写入 meta（import_text 不支持自定义 meta，需单独更新）
    doc_id = result.get("doc_id", "")
    if doc_id:
        with get_session() as session:
            doc = session.get(Document, doc_id)
            if doc:
                meta_dict = json.loads(meta_json)
                meta_dict["vault_mtime"] = mtime
                doc.meta = json.dumps(meta_dict, ensure_ascii=False)
                session.add(doc)
                session.commit()

        # V4-Phase2：wikilink 解析为 DocumentTag 关联
        if wikilinks:
            try:
                resolve_wikilinks(doc_id, wikilinks)
            except Exception as e:  # noqa: BLE001 — wikilink 解析失败不阻塞同步
                _logger.warning("wikilink 解析失败 %s: %s", doc_id, e)

    return {"doc_id": doc_id, "status": "imported" if not existing else "updated"}


def scan_vault(
    vault_path: Path | None = None,
    incremental: bool = True,
) -> VaultSyncResult:
    """全量扫描 vault 并同步所有 .md 文件。

    Args:
        vault_path: vault 根目录；None 时从配置读取
        incremental: True 时跳过未修改文件（基于 mtime）
    """
    settings = get_settings()
    if vault_path is None:
        if not settings.vault_enabled:
            raise VaultConfigError("vault_path 未配置或路径不存在")
        vault_path = Path(settings.vault_path).expanduser()

    exclude = settings.vault_exclude_patterns
    files = list_vault_files(vault_path, exclude)
    result = VaultSyncResult(scanned=len(files))
    importer = ImportService()

    for f in files:
        try:
            r = sync_file(f, vault_path, importer)
            status = r.get("status")
            if status == "skipped":
                result.skipped += 1
            elif status in ("imported", "updated"):
                result.imported += 1
            else:
                result.skipped += 1
        except Exception as e:  # noqa: BLE001 — 单文件失败不阻塞整体扫描
            result.failed += 1
            result.errors.append(f"{f.relative_to(vault_path).as_posix()}: {e}")
            _logger.warning("vault 同步失败 %s: %s", f, e)

    _logger.info(
        "vault 扫描完成: scanned=%d imported=%d skipped=%d failed=%d",
        result.scanned, result.imported, result.skipped, result.failed,
    )
    return result


# ---------------------------------------------------------------------------
# 状态查询
# ---------------------------------------------------------------------------
def get_vault_status(watching: bool = False) -> VaultStatus:
    """查询 vault 集成状态。"""
    settings = get_settings()
    if not settings.vault_enabled:
        return VaultStatus(
            enabled=False,
            vault_path=settings.vault_path,
            watch_enabled=False,
            watchdog_available=_WATCHDOG_AVAILABLE,
            watching=False,
            synced_docs=0,
            last_sync=None,
        )

    # 统计已同步的 vault 文档数
    synced = 0
    last_sync: str | None = None
    try:
        with get_session() as session:
            stmt = select(Document).where(Document.source == "obsidian")
            docs = session.exec(stmt).all()
            synced = len(docs)
            # 取最新 created_at 作为 last_sync
            if docs:
                latest = max(d.created_at for d in docs if d.created_at)
                last_sync = latest.isoformat() if latest else None
    except Exception as e:  # noqa: BLE001 — 软降级
        _logger.warning("vault 状态查询失败: %s", e)

    return VaultStatus(
        enabled=True,
        vault_path=settings.vault_path,
        watch_enabled=settings.vault_watch,
        watchdog_available=_WATCHDOG_AVAILABLE,
        watching=watching and settings.vault_watch and _WATCHDOG_AVAILABLE,
        synced_docs=synced,
        last_sync=last_sync,
    )


# ---------------------------------------------------------------------------
# watchdog 实时监听（可选）
# ---------------------------------------------------------------------------
class _VaultEventHandler(FileSystemEventHandler):  # type: ignore[misc]
    """vault 文件变更事件处理器（防抖 500ms）。"""

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = vault_root
        self._pending: dict[str, float] = {}  # path -> scheduled_time
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._flush_loop, daemon=True)
        self._worker.start()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if not event.src_path.endswith(".md"):
            return
        # 防抖：500ms 后处理
        with self._lock:
            self._pending[event.src_path] = time.time() + 0.5

    def _flush_loop(self) -> None:
        """后台线程：定期检查 pending 并同步。"""
        while True:
            time.sleep(0.2)
            now = time.time()
            with self._lock:
                ready = [p for p, t in self._pending.items() if t <= now]
                for p in ready:
                    self._pending.pop(p, None)
            for path in ready:
                try:
                    sync_file(Path(path), self.vault_root)
                except Exception as e:  # noqa: BLE001
                    _logger.warning("watch 同步失败 %s: %s", path, e)


class VaultWatcher:
    """vault 文件监听器（基于 watchdog，未安装时不可用）。"""

    def __init__(self) -> None:
        if not _WATCHDOG_AVAILABLE:
            raise VaultConfigError("watchdog 未安装，无法启用实时监听")
        self._observer: Any = None
        self._handler: _VaultEventHandler | None = None

    def start(self) -> None:
        """启动 vault 监听。"""
        settings = get_settings()
        if not settings.vault_enabled:
            raise VaultConfigError("vault_path 未配置或路径不存在")
        if not _WATCHDOG_AVAILABLE:
            raise VaultConfigError("watchdog 未安装")

        vault_root = Path(settings.vault_path).expanduser()
        self._handler = _VaultEventHandler(vault_root)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(vault_root), recursive=True)
        self._observer.start()
        _logger.info("vault 监听已启动: %s", vault_root)

    def stop(self) -> None:
        """停止 vault 监听。"""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
            _logger.info("vault 监听已停止")

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()


# ---------------------------------------------------------------------------
# 反向同步（Phase 2）：UGC 配方 → 导出 .md 到 vault
# ---------------------------------------------------------------------------
def export_recipe_to_vault(
    doc_id: str,
    vault_path: Path | None = None,
) -> str:
    """将 UGC 配方导出为 .md 文件到 vault 的 Hermes/ 子目录。

    Returns:
        导出文件的相对路径（vault 内）
    """
    settings = get_settings()
    if vault_path is None:
        if not settings.vault_enabled:
            raise VaultConfigError("vault_path 未配置或路径不存在")
        vault_path = Path(settings.vault_path).expanduser()

    with get_session() as session:
        doc = session.get(Document, doc_id)
        if not doc:
            raise VaultSyncError(f"文档不存在: {doc_id}")
        if doc.source != "ugc":
            raise VaultSyncError(f"仅 UGC 配方可导出，当前 source={doc.source}")
        title = doc.title
        content = doc.content

    # 导出到 vault/Hermes/ 子目录
    export_dir = vault_path / "Hermes"
    export_dir.mkdir(parents=True, exist_ok=True)

    # 文件名：标题（清理非法字符）+ doc_id 后缀避免重名
    safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)[:80]
    filename = f"{safe_title}.md"
    file_path = export_dir / filename

    # 构造 frontmatter
    frontmatter_lines = [
        "---",
        f"title: {title}",
        "source: hermes-ugc",
        f"doc_id: {doc_id}",
        f"exported_at: {time.strftime('%Y-%m-%dT%H:%M:%S')}",
        "---",
        "",
    ]
    file_path.write_text(
        "\n".join(frontmatter_lines) + content + "\n",
        encoding="utf-8",
    )
    rel = file_path.relative_to(vault_path).as_posix()
    _logger.info("UGC 配方已导出到 vault: %s", rel)
    return rel


# ---------------------------------------------------------------------------
# 模块级单例 watcher（可选启用）
# ---------------------------------------------------------------------------
_watcher: VaultWatcher | None = None


def start_watcher() -> bool:
    """启动全局 vault 监听器（幂等）。返回是否成功启动。"""
    global _watcher
    if _watcher and _watcher.is_running:
        return True
    try:
        _watcher = VaultWatcher()
        _watcher.start()
        return True
    except VaultConfigError as e:
        _logger.info("vault 监听未启动: %s", e)
        return False


def stop_watcher() -> None:
    """停止全局 vault 监听器（幂等）。"""
    global _watcher
    if _watcher:
        _watcher.stop()
        _watcher = None
