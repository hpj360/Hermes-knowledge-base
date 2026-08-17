"""数据源适配器注册表：按 source_id 返回适配器实例。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from hermes_kb.data_sources import DataSourcesError, get_source

if TYPE_CHECKING:
    from hermes_kb.data_sources.base import DataSourceAdapter


def get_adapter(source_id: str) -> DataSourceAdapter:
    """按注册表 import_adapter 返回适配器实例。

    - 注册表 access=curated 且无专属 adapter 时，回退到 CuratedSourceAdapter
    - 注册表 access=api 时，映射到对应实时适配器
    """
    from hermes_kb.data_sources.adapters.api import (
        BarAssistantCocktailsAdapter,
        BarAssistantIngredientsAdapter,
        CrossrefAdapter,
        DBpediaAdapter,
        OpenFoodFactsAdapter,
        TheCocktailDBAdapter,
        USDAFoodDataAdapter,
        WikidataAdapter,
        WikidataCocktailsAdapter,
        WikipediaAdapter,
    )
    from hermes_kb.data_sources.adapters.curated import CuratedSourceAdapter

    entry = get_source(source_id)

    # 显式声明的适配器优先
    adapter_id = entry.get("import_adapter")
    if adapter_id == "wikidata":
        return WikidataAdapter()
    if adapter_id == "crossref":
        return CrossrefAdapter()
    if adapter_id == "thecocktaildb":
        return TheCocktailDBAdapter()
    if adapter_id == "wikipedia":
        return WikipediaAdapter()
    if adapter_id == "openfoodfacts":
        return OpenFoodFactsAdapter()
    if adapter_id == "usda_fooddata":
        return USDAFoodDataAdapter()
    if adapter_id == "dbpedia":
        return DBpediaAdapter()
    if adapter_id == "bar_assistant_cocktails":
        return BarAssistantCocktailsAdapter()
    if adapter_id == "bar_assistant_ingredients":
        return BarAssistantIngredientsAdapter()
    if adapter_id == "wikidata_cocktails":
        return WikidataCocktailsAdapter()

    # curated 源统一走策划快照适配器
    if entry.get("access") == "curated":
        return CuratedSourceAdapter(source_id)

    raise DataSourcesError(f"数据源 {source_id} 无可用适配器（access={entry.get('access')}）")
