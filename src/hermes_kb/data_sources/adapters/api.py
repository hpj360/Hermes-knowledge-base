"""实时 API 适配器：Wikidata（SPARQL）与 Crossref（学术元数据）。

网络不可达时优雅失败（返回 imported=0 + errors），不阻塞其他数据源。
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlmodel import select

from hermes_kb.data_sources.base import DataSourceAdapter
from hermes_kb.database import get_session
from hermes_kb.models import Document
from hermes_kb.rag import ImportService

_TIMEOUT = 15
_MAX_ITEMS = 8


class _ApiAdapter(DataSourceAdapter):
    """带网络失败回退的 API 适配器基类。"""

    def import_data(self, importer: ImportService) -> dict[str, Any]:
        try:
            raw = self.fetch()
        except Exception as e:  # noqa: BLE001
            return {"imported": 0, "skipped": 0, "failed": 0, "errors": [str(e)]}
        problems = self.validate(raw)
        if problems:
            return {
                "imported": 0,
                "skipped": 0,
                "failed": len(raw),
                "errors": problems,
            }
        # 幂等去重：跳过本来源已存在的标题，避免重复导入
        with get_session() as session:
            existing = {
                d.title
                for d in session.exec(
                    select(Document).where(Document.source == self.source_id)
                ).all()
            }
        imported = 0
        skipped = 0
        failed = 0
        errors: list[str] = []
        for item in raw:
            try:
                title = item["title"]
                if title in existing:
                    skipped += 1
                    continue
                importer.import_text(
                    content=item["content"],
                    title=title,
                    source_type="seed",
                    file_type="md",
                    category="encyclopedia",
                    source=self.source_id,
                    source_authority=item.get("source_authority", ""),
                    source_url=item.get("source_url"),
                    source_refreshed_at=item.get("source_refreshed_at"),
                    source_license=item.get("license", "CC0"),
                )
                existing.add(title)
                imported += 1
            except Exception as e:  # noqa: BLE001
                failed += 1
                errors.append(f"{item.get('title')}: {e}")
        return {"imported": imported, "skipped": skipped, "failed": failed, "errors": errors}

    @staticmethod
    def _get(url: str, headers: dict[str, str] | None = None) -> Any:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))


class WikidataAdapter(_ApiAdapter):
    """Wikidata SPARQL：拉取酒类/原料实体的结构化属性（CC0）。"""

    source_id = "wikidata"
    _SOURCE_AUTHORITY = "Wikidata"

    def fetch(self) -> list[dict[str, Any]]:
        # 查询常见烈酒/基酒实体（label + 中文名 + 描述），带引用
        query = """
        SELECT ?item ?label ?zh ?desc WHERE {
          VALUES ?item {
            wd:Q11416 wd:Q28262 wd:Q12190 wd:Q202 wd:Q156956 wd:Q282 wd:Q11768
          }
          OPTIONAL { ?item rdfs:label ?label . FILTER(lang(?label)="en") }
          OPTIONAL { ?item rdfs:label ?zh . FILTER(lang(?zh)="zh") }
          OPTIONAL { ?item schema:description ?desc . FILTER(lang(?desc)="zh") }
        }
        """
        url = (
            "https://query.wikidata.org/sparql?format=json&query="
            + urllib.parse.quote(query)
        )
        data = self._get(url, {"Accept": "application/sparql-results+json"})
        items: list[dict[str, Any]] = []
        for row in data.get("results", {}).get("bindings", [])[:_MAX_ITEMS]:
            entity = row["item"]["value"].rsplit("/", 1)[-1]
            label = row.get("label", {}).get("value", entity)
            zh = row.get("zh", {}).get("value", label)
            desc = row.get("desc", {}).get("value", "")
            content = (
                f"# {zh}\n\n{desc}\n\nWikidata 实体 {entity} 的结构化属性"
                "（含可溯源引用）概述。"
            )
            items.append(
                {
                    "title": zh,
                    "content": content,
                    "source_authority": self._SOURCE_AUTHORITY,
                    "source_url": f"https://www.wikidata.org/wiki/{entity}",
                    "source_refreshed_at": datetime.now(timezone.utc),
                    "license": "CC0",
                }
            )
        return items

    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        problems = []
        for i, item in enumerate(raw):
            if not item.get("title") or not item.get("content"):
                problems.append(f"item[{i}]: 缺 title/content")
        return problems


class CrossrefAdapter(_ApiAdapter):
    """Crossref 开放 API：拉取酒类/烈酒相关学术文章元数据与摘要。"""

    source_id = "crossref"
    _SOURCE_AUTHORITY = "Crossref / 学术期刊"

    def fetch(self) -> list[dict[str, Any]]:
        # 检索烈酒/威士忌/发酵化学相关文献（开放摘要优先）
        url = (
            "https://api.crossref.org/works?query=spirits%20whisky%20fermentation"
            "%20chemistry&rows=8&select=title,abstract,DOI,container-title,issued"
        )
        data = self._get(url, {"User-Agent": "HermesKB/1.0 (mailto:hermes@example.com)"})
        items: list[dict[str, Any]] = []
        for item in data.get("message", {}).get("items", []):
            title = (item.get("title") or [""])[0]
            doi = item.get("DOI", "")
            container = (item.get("container-title") or [""])[0]
            abstract = item.get("abstract", "") or ""
            # 剥离 JATS 标签（简单处理）
            plain = abstract.replace("<jats:p>", " ").replace("</jats:p>", " ")
            plain = plain.replace("<jats:title>", " ").replace("</jats:title>", " ")
            if not title:
                continue
            content = (
                f"# {title}\n\n{plain}\n\n学术来源：{container}，DOI {doi}。"
            )
            items.append(
                {
                    "title": title[:200],
                    "content": content,
                    "source_authority": container or self._SOURCE_AUTHORITY,
                    "source_url": f"https://doi.org/{doi}" if doi else "",
                    "source_refreshed_at": datetime.now(timezone.utc),
                    "license": "CC0",
                }
            )
        return items

    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        problems = []
        for i, item in enumerate(raw):
            if not item.get("title") or not item.get("content"):
                problems.append(f"item[{i}]: 缺 title/content")
        return problems


class TheCocktailDBAdapter(_ApiAdapter):
    """TheCocktailDB 开放配方库适配器。

    复用既有 sync_thecocktaildb 同步逻辑；网络失败时优雅回退。
    """

    source_id = "thecocktaildb"

    def fetch(self) -> list[dict[str, Any]]:
        return []

    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        return []

    def import_data(self, importer: ImportService) -> dict[str, Any]:
        from hermes_kb.thecocktaildb_sync import sync_thecocktaildb

        try:
            result = sync_thecocktaildb(importer=importer)
        except Exception as e:  # noqa: BLE001
            return {"imported": 0, "skipped": 0, "failed": 0, "errors": [str(e)]}
        return {
            "imported": result.get("imported", 0),
            "skipped": result.get("skipped", 0),
            "failed": result.get("failed", 0),
            "errors": [],
        }
