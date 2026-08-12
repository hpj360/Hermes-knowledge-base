"""数据源适配器抽象基类。

每个数据源通过一个 ``DataSourceAdapter`` 子类接入，定义统一的
fetch → validate → import 契约，使收割编排（Task 4）与质量验证（Task 5）
能以一致方式处理所有来源。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hermes_kb.rag import ImportService


class DataSourceAdapter(ABC):
    """数据源适配器抽象基类。

    子类需定义：
    - ``source_id``：对应 registry.json 的 id
    - ``fetch()``：返回原始记录列表（每项为 dict）
    - ``validate(raw)``：校验原始记录符合该源 schema，返回问题列表
    - ``import_data(importer)``：将数据通过 ImportService 导入并写溯源字段
    """

    source_id: str = ""

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """拉取原始数据，返回记录列表。"""

    @abstractmethod
    def validate(self, raw: list[dict[str, Any]]) -> list[str]:
        """校验原始记录，返回问题列表（空则通过）。"""

    @abstractmethod
    def import_data(self, importer: ImportService) -> dict[str, Any]:
        """导入数据，返回 {"imported": N, "skipped": M, "failed": K}。"""

    def run(self, importer: ImportService) -> dict[str, Any]:
        """编排：fetch → validate → import。返回导入汇总。"""
        raw = self.fetch()
        problems = self.validate(raw)
        if problems:
            return {
                "imported": 0,
                "skipped": 0,
                "failed": len(raw),
                "errors": problems,
            }
        return self.import_data(importer)
