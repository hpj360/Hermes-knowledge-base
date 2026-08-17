"""实时 API 适配器：Wikidata（SPARQL）与 Crossref（学术元数据）。

网络不可达时优雅失败（返回 imported=0 + errors），不阻塞其他数据源。
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlmodel import select

from hermes_kb.data_sources.base import DataSourceAdapter
from hermes_kb.database import get_session
from hermes_kb.models import Document
from hermes_kb.rag import ImportService

_logger = logging.getLogger(__name__)

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
        import os

        req = urllib.request.Request(url, headers=headers or {})
        # 代理支持：读取 HTTPS_PROXY / HTTP_PROXY 环境变量
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        if proxy:
            proxy_handler = urllib.request.ProxyHandler(
                {"http": proxy, "https": proxy}
            )
            opener = urllib.request.build_opener(proxy_handler)
        else:
            opener = urllib.request.build_opener()
        with opener.open(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))


class WikidataAdapter(_ApiAdapter):
    """Wikidata SPARQL：拉取酒类/原料实体的结构化属性（CC0）。"""

    source_id = "wikidata"
    _SOURCE_AUTHORITY = "Wikidata"

    def fetch(self) -> list[dict[str, Any]]:
        # 查询酒类/原料/产区/鸡尾酒实体（label + 中文名 + 描述），带引用
        query = """
        SELECT ?item ?label ?zh ?desc WHERE {
          VALUES ?item {
            wd:Q11416 wd:Q28262 wd:Q12190 wd:Q202 wd:Q156956 wd:Q282 wd:Q11768
            wd:Q18427 wd:Q7335 wd:Q7374 wd:Q7432 wd:Q82108 wd:Q82109 wd:Q82106
            wd:Q9738 wd:Q18101 wd:Q676 wd:Q7673 wd:Q1206 wd:Q7486
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


class WikidataCocktailsAdapter(_ApiAdapter):
    """Wikidata SPARQL：拉取鸡尾酒实体（Q134768）含中文别名（CC0）。

    Phase 1.3：鸡尾酒智能体数据源。通过 SPARQL 批量拉取 instance of
    (P31) = cocktail (Q134768) 及其子类的实体，再用 wbgetentities 批量
    补全中文 label/别名/描述，用于提升中文检索召回并反哺 Phase 2 配方元数据。

    网络不可达时优雅失败（返回空列表），不阻塞其他数据源。
    """

    source_id = "wikidata_cocktails"
    _SOURCE_AUTHORITY = "Wikidata"
    _MAX_ITEMS = 600
    _COCKTAIL_QID = "Q134768"  # cocktail（含酒精混合饮品）
    # wbgetentities 语言覆盖简体/繁体变体，提升中文覆盖率
    _ZH_LANGS = ("zh", "zh-hans", "zh-cn", "zh-tw", "zh-hant")
    _BATCH = 50  # wbgetentities 单次上限 50 个 QID

    _QUERY = """
    SELECT ?item WHERE {
      ?item wdt:P31/wdt:P279* wd:%(qid)s .
    }
    LIMIT %(limit)d
    """

    def fetch(self) -> list[dict[str, Any]]:
        query = self._QUERY % {
            "qid": self._COCKTAIL_QID,
            "limit": self._MAX_ITEMS,
        }
        url = (
            "https://query.wikidata.org/sparql?format=json&query="
            + urllib.parse.quote(query)
        )
        data = self._get(
            url,
            {
                "Accept": "application/sparql-results+json",
                "User-Agent": "HermesKB/1.0 (hermes@example.com)",
            },
        )
        qids = [
            row["item"]["value"].rsplit("/", 1)[-1]
            for row in data.get("results", {}).get("bindings", [])
            if row.get("item", {}).get("value")
        ]

        # 分批 wbgetentities 补全中文 label/别名/描述
        details: dict[str, dict[str, Any]] = {}
        for i in range(0, len(qids), self._BATCH):
            batch = qids[i : i + self._BATCH]
            try:
                ent_data = self._get(
                    "https://www.wikidata.org/w/api.php?"
                    + urllib.parse.urlencode(
                        {
                            "action": "wbgetentities",
                            "ids": "|".join(batch),
                            "props": "labels|aliases|descriptions",
                            "languages": "|".join((*self._ZH_LANGS, "en")),
                            "format": "json",
                        }
                    ),
                    {"User-Agent": "HermesKB/1.0 (hermes@example.com)"},
                )
            except Exception as e:  # noqa: BLE001
                _logger.debug("wbgetentities failed: %s", e)
                continue
            for qid, ent in ent_data.get("entities", {}).items():
                details[qid] = ent

        return self._build_items(qids, details)

    def _build_items(
        self, qids: list[str], details: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        # 内置鸡尾酒中文词典（补全 Wikidata 缺失的中文名）
        from hermes_kb.translation import _COMMON_TRANSLATIONS

        items: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for qid in qids:
            ent = details.get(qid, {})
            zh_labels = self._pick_zh(ent, "labels")
            zh_aliases = self._pick_zh(ent, "aliases")
            zh_desc = self._pick_zh(ent, "descriptions")
            en_label = ent.get("labels", {}).get("en", {}).get("value", "")

            # 标题：优先中文 label，其次内部词典翻译，最后英文
            title = zh_labels[0] if zh_labels else ""
            if not title and en_label:
                title = _COMMON_TRANSLATIONS.get(en_label.lower(), "")
            if not title:
                title = en_label
            if not title:
                title = qid
            # 词典命中补充为别名
            if en_label:
                dict_zh = _COMMON_TRANSLATIONS.get(en_label.lower(), "")
                if dict_zh and dict_zh not in zh_aliases and dict_zh != title:
                    zh_aliases.insert(0, dict_zh)
            if title in seen_titles:
                continue
            seen_titles.add(title)

            parts: list[str] = [f"# {title}"]
            if en_label and en_label != title:
                parts.append(f"英文名：{en_label}")
            if zh_aliases:
                parts.append(f"中文别名：{'、'.join(zh_aliases)}")
            if zh_desc:
                parts.append(zh_desc[0])
            parts.append(
                f"Wikidata 实体 {qid} 的结构化属性（含可溯源引用）概述。"
            )
            items.append(
                {
                    "title": title,
                    "content": "\n\n".join(parts),
                    "source_authority": self._SOURCE_AUTHORITY,
                    "source_url": f"https://www.wikidata.org/wiki/{qid}",
                    "source_refreshed_at": datetime.now(timezone.utc),
                    "license": "CC0",
                    "category": "encyclopedia",
                }
            )
        return items

    @staticmethod
    def _pick_zh(ent: dict[str, Any], field: str) -> list[str]:
        """按语言优先级取中文 label/别名/描述（去重保序）。"""
        out: list[str] = []
        for lang in WikidataCocktailsAdapter._ZH_LANGS:
            values = ent.get(field, {}).get(lang)
            if field == "aliases":
                values = [a.get("value", "") for a in values or []]
            else:
                values = [values.get("value", "")] if isinstance(values, dict) else []
            for v in values:
                v = v.strip()
                if v and v not in out:
                    out.append(v)
        return out

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
        # 多主题检索：烈酒/威士忌/发酵化学 + 葡萄酒/风味 + 鸡尾酒/调酒 + 清酒/啤酒
        queries = [
            "spirits whisky fermentation chemistry",
            "wine sensory phenolic compounds",
            "cocktail mixology beverage",
            "sake brewing rice fermentation",
        ]
        items: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for q in queries:
            url = (
                f"https://api.crossref.org/works?query={urllib.parse.quote(q)}"
                f"&rows=4&select=title,abstract,DOI,container-title,issued"
            )
            try:
                data = self._get(
                    url, {"User-Agent": "HermesKB/1.0 (mailto:hermes@example.com)"}
                )
            except Exception:  # noqa: BLE001, S112
                continue
            for item in data.get("message", {}).get("items", []):
                title = (item.get("title") or [""])[0]
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                doi = item.get("DOI", "")
                container = (item.get("container-title") or [""])[0]
                abstract = item.get("abstract", "") or ""
                # 剥离 JATS 标签（简单处理）
                plain = abstract.replace("<jats:p>", " ").replace("</jats:p>", " ")
                plain = plain.replace("<jats:title>", " ").replace("</jats:title>", " ")
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
                if len(items) >= _MAX_ITEMS * 2:
                    break
            if len(items) >= _MAX_ITEMS * 2:
                break
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


# ---------------------------------------------------------------------------
# 扩展数据源适配器（Wikipedia / Open Food Facts / USDA / DBpedia）
# ---------------------------------------------------------------------------

class WikipediaAdapter(_ApiAdapter):
    """Wikipedia API：按分类批量拉取酒类百科条目（CC BY-SA）。

    使用 MediaWiki API 的 generator=categorymembers + prop=extracts
    一次性获取分类下页面正文，过滤过短条目后导入。
    """

    source_id = "wikipedia"
    _SOURCE_AUTHORITY = "Wikipedia"
    _MAX_PER_SOURCE = 40

    # 中文维基百科中覆盖面较广的酒类分类
    _CATEGORIES = (
        "鸡尾酒",
        "葡萄酒",
        "啤酒",
        "蒸馏酒",
        "利口酒",
        "白兰地",
        "威士忌",
        "伏特加",
    )

    def fetch(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for cat in self._CATEGORIES:
            url = (
                "https://zh.wikipedia.org/w/api.php?action=query"
                "&generator=categorymembers"
                f"&gcmtitle=Category:{urllib.parse.quote(cat)}"
                "&gcmtype=page&gcmlimit=20"
                "&prop=extracts&explaintext=true&exsectionformat=plain"
                "&format=json"
            )
            try:
                data = self._get(url, {"User-Agent": "HermesKB/1.0"})
            except Exception:  # noqa: BLE001, S112
                continue
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                title = page.get("title", "")
                extract = page.get("extract", "")
                if not title or not extract or title in seen_titles:
                    continue
                if len(extract) < 200:
                    continue
                seen_titles.add(title)
                items.append(
                    {
                        "title": title[:200],
                        "content": f"# {title}\n\n{extract[:3000]}",
                        "source_authority": self._SOURCE_AUTHORITY,
                        "source_url": (
                            f"https://zh.wikipedia.org/wiki/"
                            f"{urllib.parse.quote(title)}"
                        ),
                        "source_refreshed_at": datetime.now(timezone.utc),
                        "license": "CC BY-SA",
                    }
                )
                if len(items) >= self._MAX_PER_SOURCE:
                    break
            if len(items) >= self._MAX_PER_SOURCE:
                break
        return items

    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        problems = []
        for i, item in enumerate(raw):
            if not item.get("title") or not item.get("content"):
                problems.append(f"item[{i}]: 缺 title/content")
        return problems


class OpenFoodFactsAdapter(_ApiAdapter):
    """Open Food Facts API：酒类产品成分与营养数据（CC BY-SA）。

    按分类标签搜索含酒精饮料，提取产品名/品牌/酒精度/配料/营养成分。
    """

    source_id = "openfoodfacts"
    _SOURCE_AUTHORITY = "Open Food Facts"
    _MAX_PER_SOURCE = 50

    def fetch(self) -> list[dict[str, Any]]:
        url = (
            "https://world.openfoodfacts.org/cgi/search.pl?action=process"
            "&tagtype_0=categories&tag_contains_0=contains"
            "&tag_0=alcoholic%20beverages"
            "&fields=product_name,ingredients_text,nutriments,alcohol,"
            "brands,categories,code"
            "&page_size=80&json=1"
        )
        data = self._get(url)
        items: list[dict[str, Any]] = []
        for product in data.get("products", [])[: self._MAX_PER_SOURCE]:
            name = product.get("product_name", "").strip()
            if not name:
                continue
            brands = product.get("brands", "")
            alcohol = product.get("alcohol", "")
            ingredients = product.get("ingredients_text", "").strip()
            nutriments = product.get("nutriments", {})
            code = product.get("code", "")

            parts: list[str] = [f"# {name}"]
            if brands:
                parts.append(f"品牌：{brands}")
            if alcohol:
                parts.append(f"酒精度：{alcohol}%")
            if ingredients:
                parts.append(f"配料：{ingredients[:500]}")
            energy = nutriments.get("energy-kcal_100g", "")
            if energy:
                parts.append(f"热量：{energy} kcal/100ml")
            carbs = nutriments.get("carbohydrates_100g", "")
            if carbs:
                parts.append(f"碳水化合物：{carbs} g/100ml")
            sugar = nutriments.get("sugars_100g", "")
            if sugar:
                parts.append(f"糖分：{sugar} g/100ml")
            fat = nutriments.get("fat_100g", "")
            if fat:
                parts.append(f"脂肪：{fat} g/100ml")

            content = "\n\n".join(parts)
            if len(content) < 100:
                continue
            source_url = (
                f"https://world.openfoodfacts.org/product/{code}"
                if code
                else "https://world.openfoodfacts.org/"
            )
            items.append(
                {
                    "title": name[:200],
                    "content": content,
                    "source_authority": self._SOURCE_AUTHORITY,
                    "source_url": source_url,
                    "source_refreshed_at": datetime.now(timezone.utc),
                    "license": "CC BY-SA",
                }
            )
        return items

    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        problems = []
        for i, item in enumerate(raw):
            if not item.get("title") or not item.get("content"):
                problems.append(f"item[{i}]: 缺 title/content")
        return problems


class USDAFoodDataAdapter(_ApiAdapter):
    """USDA FoodData Central API：酒类营养数据（Public Domain）。

    使用 DEMO_KEY（限 50 次/小时），按关键词搜索 SR Legacy 数据库中的
    含酒精食品，提取营养成分。
    """

    source_id = "usda_fooddata"
    _SOURCE_AUTHORITY = "USDA FoodData Central"
    _API_KEY = "DEMO_KEY"
    _MAX_PER_SOURCE = 30

    _QUERIES = ("alcohol", "beer", "wine", "whiskey", "rum", "vodka")

    def fetch(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for q in self._QUERIES:
            url = (
                f"https://api.nal.usda.gov/fdc/v1/foods/list"
                f"?dataType=SR%20Legacy&query={urllib.parse.quote(q)}"
                f"&api_key={self._API_KEY}&pageSize=10"
            )
            try:
                data = self._get(url)
            except Exception:  # noqa: BLE001, S112
                continue
            for food in data:
                fdc_id = str(food.get("fdcId", ""))
                desc = food.get("description", "").strip()
                if not desc or fdc_id in seen_ids:
                    continue
                seen_ids.add(fdc_id)
                nutrients = food.get("foodNutrients", [])
                parts: list[str] = [f"# {desc}"]
                for n in nutrients:
                    nname = n.get("nutrientName", "")
                    amount = n.get("amount", "")
                    unit = n.get("unitName", "")
                    if nname and amount:
                        parts.append(f"{nname}: {amount} {unit}")
                content = "\n".join(parts)
                if len(content) < 100:
                    continue
                items.append(
                    {
                        "title": f"USDA: {desc}"[:200],
                        "content": content,
                        "source_authority": self._SOURCE_AUTHORITY,
                        "source_url": (
                            f"https://fdc.nal.usda.gov/fdc-app.html"
                            f"#/food-details/{fdc_id}"
                        ),
                        "source_refreshed_at": datetime.now(timezone.utc),
                        "license": "public-domain",
                    }
                )
                if len(items) >= self._MAX_PER_SOURCE:
                    break
            if len(items) >= self._MAX_PER_SOURCE:
                break
        return items

    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        problems = []
        for i, item in enumerate(raw):
            if not item.get("title") or not item.get("content"):
                problems.append(f"item[{i}]: 缺 title/content")
        return problems


class DBpediaAdapter(_ApiAdapter):
    """DBpedia SPARQL：酒类实体结构化知识（CC BY-SA）。

    查询 dbo:Beverage 类型中与酒精相关的实体，获取英文标签与摘要。
    """

    source_id = "dbpedia"
    _SOURCE_AUTHORITY = "DBpedia"
    _MAX_PER_SOURCE = 30

    def fetch(self) -> list[dict[str, Any]]:
        query = """
        SELECT ?entity ?label ?abstract WHERE {
          ?entity a dbo:Beverage .
          ?entity rdfs:label ?label .
          ?entity dbo:abstract ?abstract .
          FILTER(lang(?label) = "en")
          FILTER(lang(?abstract) = "en")
          FILTER(
            CONTAINS(LCASE(?abstract), "alcohol")
            || CONTAINS(LCASE(?abstract), "wine")
            || CONTAINS(LCASE(?abstract), "beer")
            || CONTAINS(LCASE(?abstract), "spirit")
            || CONTAINS(LCASE(?abstract), "whisk")
            || CONTAINS(LCASE(?abstract), "cocktail")
          )
        }
        LIMIT 50
        """
        url = (
            "https://dbpedia.org/sparql?format=json&query="
            + urllib.parse.quote(query)
        )
        data = self._get(url, {"Accept": "application/sparql-results+json"})
        items: list[dict[str, Any]] = []
        for row in (
            data.get("results", {}).get("bindings", [])[: self._MAX_PER_SOURCE]
        ):
            label = row.get("label", {}).get("value", "")
            abstract = row.get("abstract", {}).get("value", "")
            entity = row.get("entity", {}).get("value", "")
            if not label or not abstract:
                continue
            items.append(
                {
                    "title": label[:200],
                    "content": f"# {label}\n\n{abstract[:3000]}",
                    "source_authority": self._SOURCE_AUTHORITY,
                    "source_url": entity,
                    "source_refreshed_at": datetime.now(timezone.utc),
                    "license": "CC BY-SA",
                }
            )
        return items

    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        problems = []
        for i, item in enumerate(raw):
            if not item.get("title") or not item.get("content"):
                problems.append(f"item[{i}]: 缺 title/content")
        return problems


class BarAssistantCocktailsAdapter(_ApiAdapter):
    """bar-assistant/data 鸡尾酒数据（CD-1.2，MIT）。

    通过 bar_assistant_sync.fetch_bar_assistant_cocktails() 拉取全量结构化鸡尾酒
    （含用料表/技法/杯型/酒精度），供 GitHub Actions 海外生成快照后本地导入。
    """

    source_id = "bar_assistant_cocktails"
    _SOURCE_AUTHORITY = "bar-assistant"

    def fetch(self) -> list[dict[str, Any]]:
        from hermes_kb.bar_assistant_sync import fetch_bar_assistant_cocktails

        items = fetch_bar_assistant_cocktails()
        # 转为 API 适配器 item 格式（补齐 source_refreshed_at 等字段）
        return [
            {
                "title": it["title"],
                "content": it["content"],
                "source_authority": it["source_authority"],
                "source_url": it["source_url"],
                "source_refreshed_at": it.get("refreshed_at"),
                "license": it["license"],
                "category": it.get("category", "recipe"),
                "glassware": it.get("glassware", ""),
                "technique": it.get("technique", ""),
                "flavor_profile": it.get("flavor_profile", ""),
                "verified": it.get("verified", False),
            }
            for it in items
        ]

    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        problems = []
        for i, item in enumerate(raw):
            if not item.get("title") or not item.get("content"):
                problems.append(f"item[{i}]: 缺 title/content")
        return problems

    def import_data(self, importer: ImportService) -> dict[str, Any]:
        # 复用 _ApiAdapter 通用导入（幂等 title 去重）
        return super().import_data(importer)


class BarAssistantIngredientsAdapter(_ApiAdapter):
    """bar-assistant/data 原料档案（CD-1.2，MIT）。"""

    source_id = "bar_assistant_ingredients"
    _SOURCE_AUTHORITY = "bar-assistant"

    def fetch(self) -> list[dict[str, Any]]:
        from hermes_kb.bar_assistant_sync import fetch_bar_assistant_ingredients

        items = fetch_bar_assistant_ingredients()
        return [
            {
                "title": it["title"],
                "content": it["content"],
                "source_authority": it["source_authority"],
                "source_url": it["source_url"],
                "source_refreshed_at": it.get("refreshed_at"),
                "license": it["license"],
                "category": it.get("category", "ingredient_profile"),
                "verified": it.get("verified", False),
            }
            for it in items
        ]

    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        problems = []
        for i, item in enumerate(raw):
            if not item.get("title") or not item.get("content"):
                problems.append(f"item[{i}]: 缺 title/content")
        return problems

    def import_data(self, importer: ImportService) -> dict[str, Any]:
        return super().import_data(importer)
