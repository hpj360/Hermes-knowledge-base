"""bar-assistant 替代材料同步器（B4）。

从 karlomikus/bar-assistant 仓库（MIT License）拉取替代材料关系。
支持传入 mock data 用于测试。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text as sa_text
from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import IngredientSubstitute

_logger = logging.getLogger(__name__)

# bar-assistant 仓库基础 URL（用于真实拉取）
BAR_ASSISTANT_REPO = "karlomikus/bar-assistant"
BAR_ASSISTANT_RAW_BASE = f"https://raw.githubusercontent.com/{BAR_ASSISTANT_REPO}/main"


def sync_bar_assistant_substitutes(
    data: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """从 bar-assistant 同步替代材料关系。

    Args:
        data: 替代关系列表，每项 {"canonical": "...", "substitute": "..."}
              若为 None，尝试从 GitHub 拉取（需网络）

    Returns:
        {"imported": N, "skipped": N, "failed": N}
    """
    if data is None:
        data = _fetch_remote_data()

    if not data:
        return {"imported": 0, "skipped": 0, "failed": 0}

    now = datetime.now(timezone.utc)
    failed = 0
    items: list[tuple[str, str]] = []
    for item in data:
        try:
            canonical = (item.get("canonical") or "").strip()
            substitute = (item.get("substitute") or "").strip()
        except (AttributeError, TypeError):
            failed += 1
            continue
        if not canonical or not substitute:
            failed += 1
            continue
        items.append((canonical, substitute))

    if not items:
        return {"imported": 0, "skipped": 0, "failed": failed}

    pending_imported = 0
    pending_skipped = 0
    try:
        with get_session() as session:
            for canonical, substitute in items:
                result = session.execute(
                    sa_text(
                        "INSERT INTO ingredientsubstitute "
                        "(canonical, substitute, source, created_at) "
                        "VALUES (:canonical, :substitute, 'bar_assistant', :now) "
                        "ON CONFLICT(canonical, substitute) DO NOTHING"
                    ),
                    {"canonical": canonical, "substitute": substitute, "now": now},
                )
                if result.rowcount > 0:
                    pending_imported += 1
                else:
                    pending_skipped += 1
            session.commit()
    except Exception as e:
        _logger.warning("bar-assistant batch insert failed: %s", e)
        return {"imported": 0, "skipped": 0, "failed": failed + len(items)}

    return {"imported": pending_imported, "skipped": pending_skipped, "failed": failed}


def _fetch_remote_data() -> list[dict[str, str]]:
    """从 bar-assistant 仓库拉取替代材料数据。

    实际拉取逻辑：解析仓库的 seed 数据文件。
    若网络不可用或解析失败，返回空列表。
    """
    try:
        # bar-assistant 的成分数据通常在 database/seed 目录
        # 这里尝试拉取成分替代关系
        url = f"{BAR_ASSISTANT_RAW_BASE}/database/seed/ingredients.json"
        resp = httpx.get(url, timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        # 解析为统一格式
        data: list[dict[str, str]] = []
        for ing in raw if isinstance(raw, list) else []:
            canonical = ing.get("name", "")
            # bar-assistant 的 substitute 字段可能是列表或字符串
            subs = ing.get("substitutes", [])
            if isinstance(subs, str):
                subs = [s.strip() for s in subs.split(",") if s.strip()]
            for sub in subs:
                if canonical and sub:
                    data.append({"canonical": canonical, "substitute": sub})
        return data
    except (httpx.HTTPError, ValueError, KeyError, TypeError, OSError) as e:
        _logger.warning("bar-assistant remote data fetch failed: %s", e)
        return []
