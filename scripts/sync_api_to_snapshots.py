#!/usr/bin/env python3
"""将 API 数据源拉取结果保存为本地策划快照。

在互联网可达环境（如 GitHub Actions）中运行，拉取各 API 数据源的最新数据
并保存为 data/sources/<source_id>_sync.json，供 GFW 环境通过 CuratedSourceAdapter 导入。

用法：
    python scripts/sync_api_to_snapshots.py

退出码：0 成功（含部分失败），1 全部失败。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from hermes_kb.data_sources.adapters.api import (
    BarAssistantCocktailsAdapter,
    BarAssistantIngredientsAdapter,
    CrossrefAdapter,
    DBpediaAdapter,
    OpenFoodFactsAdapter,
    USDAFoodDataAdapter,
    WikidataAdapter,
    WikidataCocktailsAdapter,
    WikipediaAdapter,
)

SOURCES_DIR = ROOT / "data" / "sources"

# 需要同步的 API 源（在 GFW 环境不可达，需在海外环境拉取）
API_SOURCES: list[tuple[str, object]] = [
    ("wikipedia_sync", WikipediaAdapter()),
    ("openfoodfacts_sync", OpenFoodFactsAdapter()),
    ("usda_fooddata_sync", USDAFoodDataAdapter()),
    ("dbpedia_sync", DBpediaAdapter()),
    ("wikidata_sync", WikidataAdapter()),
    ("wikidata_cocktails_sync", WikidataCocktailsAdapter()),
    ("crossref_sync", CrossrefAdapter()),
    ("bar_assistant_cocktails_sync", BarAssistantCocktailsAdapter()),
    ("bar_assistant_ingredients_sync", BarAssistantIngredientsAdapter()),
]


def _convert_to_curated(items: list[dict], source_authority: str) -> list[dict]:
    """将 API 适配器返回的 item 格式转换为 CuratedSourceAdapter 所需的格式。

    透传配方结构化字段（glassware/technique/flavor_profile/verified），
    使 IBA / bar-assistant 等配方快照在本地导入时保留结构化元数据。
    """
    converted: list[dict] = []
    for item in items:
        dt = item.get("source_refreshed_at")
        if isinstance(dt, datetime):
            refreshed = dt.strftime("%Y-%m-%d")
        elif isinstance(dt, str):
            refreshed = dt
        else:
            refreshed = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = {
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "source_url": item.get("source_url", ""),
            "refreshed_at": refreshed,
            "license": item.get("license", "CC0"),
            "category": item.get("category", "encyclopedia"),
            "source_authority": item.get("source_authority", source_authority),
        }
        # 配方结构化字段（非空时透传）
        for field in ("glassware", "technique", "flavor_profile", "verified"):
            if item.get(field) not in (None, "", False):
                entry[field] = item.get(field)
        converted.append(entry)
    return converted


def main() -> int:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    success = 0
    failed = 0

    for sync_id, adapter in API_SOURCES:
        try:
            raw = adapter.fetch()
            if not raw:
                print(f"  {sync_id}: 0 items（API 返回空或被拦截）")
                failed += 1
                continue
            items = _convert_to_curated(raw, getattr(adapter, "_SOURCE_AUTHORITY", ""))
            path = SOURCES_DIR / f"{sync_id}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            print(f"  {sync_id}: {len(items)} items -> {path.name}")
            success += 1
        except Exception as e:  # noqa: BLE001
            print(f"  {sync_id}: ERROR - {e}", file=sys.stderr)
            failed += 1

    print(f"\n同步完成: {success} 成功, {failed} 失败")
    return 0 if success > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
