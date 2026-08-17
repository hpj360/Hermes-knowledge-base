"""策划精选源适配器：读取 data/sources/<id>.json 快照并幂等导入。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import select

from hermes_kb.data_sources.base import DataSourceAdapter
from hermes_kb.database import get_session
from hermes_kb.models import Document
from hermes_kb.rag import ImportService

_SOURCES_DIR = (
    Path(__file__).resolve().parents[3].parent / "data" / "sources"
)

_REQUIRED_ITEM_FIELDS = {
    "title",
    "content",
    "source_url",
    "refreshed_at",
    "license",
    "category",
    "source_authority",
}


class CuratedSourceAdapter(DataSourceAdapter):
    """读取人工策划快照的适配器。"""

    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        self.snapshot_path = _SOURCES_DIR / f"{source_id}.json"

    # -- fetch ------------------------------------------------------------
    def fetch(self) -> list[dict[str, Any]]:
        if not self.snapshot_path.exists():
            raise FileNotFoundError(f"策划快照不存在: {self.snapshot_path}")
        with open(self.snapshot_path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            # 保持 ValueError 以兼容上层对快照格式错误的统一处理
            raise ValueError(f"策划快照需为列表: {self.snapshot_path}")  # noqa: TRY004
        return data

    # -- validate ---------------------------------------------------------
    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        problems: list[str] = []
        for i, item in enumerate(raw):
            for field in _REQUIRED_ITEM_FIELDS:
                if field not in item or not item.get(field):
                    problems.append(f"item[{i}]: 缺少字段 {field}")
            if "content" in item and len(item["content"].strip()) < 100:
                problems.append(f"item[{i}]: 内容过短（<100 字符）")
        return problems

    # -- import -----------------------------------------------------------
    def import_data(self, importer: ImportService) -> dict[str, Any]:
        raw = self.fetch()
        imported = 0
        skipped = 0
        failed = 0
        errors: list[str] = []
        # 预加载已有标题，幂等去重
        with get_session() as session:
            existing = {
                d.title for d in session.exec(select(Document)).all()
            }
        for item in raw:
            title = item["title"]
            try:
                if title in existing:
                    skipped += 1
                    continue
                refreshed = _parse_date(item.get("refreshed_at"))
                # 可选配方结构化字段（IBA 官方配方快照等）
                is_recipe = item.get("category") == "recipe"
                importer.import_text(
                    content=item["content"],
                    title=title,
                    source_type="seed",
                    file_type="md",
                    category=item.get("category", "encyclopedia"),
                    source=self.source_id,
                    source_authority=item.get("source_authority", ""),
                    source_url=item.get("source_url"),
                    source_refreshed_at=refreshed,
                    source_license=item.get("license"),
                    verified=bool(item.get("verified", False)) if is_recipe else None,
                    glassware=item.get("glassware", "") if is_recipe else "",
                    technique=item.get("technique", "") if is_recipe else "",
                    iba_category=item.get("iba_category", "") if is_recipe else "",
                    flavor_profile=item.get("flavor_profile", "") if is_recipe else "",
                )
                existing.add(title)
                imported += 1
            except Exception as e:  # noqa: BLE001
                failed += 1
                errors.append(f"{title}: {e}")
        return {"imported": imported, "skipped": skipped, "failed": failed, "errors": errors}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
