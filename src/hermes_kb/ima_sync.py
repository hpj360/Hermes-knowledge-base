"""腾讯 IMA 知识库 OpenAPI 同步器（B6）。

接入文档：https://ima.qq.com/agent-interface
鉴权坑：不是标准 Authorization，而是两个自定义头：
  - ima-openapi-clientid: <CLIENT_ID>
  - ima-openapi-apikey: <API_KEY>
且 Content-Type 必须显式 application/json；路径前缀 /openapi/wiki/v1/。

主要端点：
  - POST /openapi/wiki/v1/search_knowledge_base  列出/搜索知识库
  - POST /openapi/wiki/v1/search_knowledge       在指定知识库中检索片段

同步流程：
  1. list_knowledge_bases() → 拿到 kb_id（用户未配置时）
  2. sync_knowledge_base(kb_id, query) → 在 IMA 中检索 → 写入本地 ImportService
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlmodel import select

from hermes_kb.config import get_settings
from hermes_kb.database import get_session
from hermes_kb.models import Document
from hermes_kb.rag import ImportService

_logger = logging.getLogger(__name__)

# IMA OpenAPI 基址（注意路径前缀 /openapi/wiki/v1/，写成 /api/v1/ 会 401）
_API_BASE = "https://ima.qq.com"
_LIST_KB_PATH = "/openapi/wiki/v1/search_knowledge_base"
_SEARCH_KB_PATH = "/openapi/wiki/v1/search_knowledge"

# 同步请求超时（秒）
_HTTP_TIMEOUT = 30.0


class IMAConfigError(RuntimeError):
    """IMA 凭证未配置或无效。"""


class IMAAPIError(RuntimeError):
    """IMA OpenAPI 调用失败（非 0 返回码或网络异常）。"""


def _headers() -> dict[str, str]:
    """构造 IMA OpenAPI 鉴权头。

    注意：Content-Type 必须显式 application/json，缺失会被拒。
    """
    s = get_settings()
    if not s.ima_enabled:
        raise IMAConfigError(
            "IMA 未配置：请设置 KB_IMA_CLIENT_ID 与 KB_IMA_API_KEY 环境变量"
        )
    return {
        "ima-openapi-clientid": s.ima_client_id.strip(),
        "ima-openapi-apikey": s.ima_api_key.strip(),
        "Content-Type": "application/json; charset=utf-8",
    }


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    """统一 POST + 错误处理。

    返回 data 字段（已脱壳）。code != 0 抛 IMAAPIError，携带 IMA 返回的 msg。
    """
    try:
        resp = httpx.post(
            f"{_API_BASE}{path}",
            json=body,
            headers=_headers(),
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError as e:
        raise IMAAPIError(f"IMA HTTP 请求失败 ({path}): {e}") from e
    except ValueError as e:
        raise IMAAPIError(f"IMA 响应非 JSON ({path}): {e}") from e

    if not isinstance(payload, dict):
        raise IMAAPIError(f"IMA 响应结构异常: {payload!r}")
    # IMA 返回格式：{ code: 0, msg: "...", data: {...} }
    if payload.get("code") != 0:
        raise IMAAPIError(
            f"IMA API 错误 ({path}): code={payload.get('code')} "
            f"msg={payload.get('msg')}"
        )
    return payload.get("data") or {}


def list_knowledge_bases(query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """列出/搜索当前账号下的所有知识库。

    Args:
        query: 关键词过滤（空串返回全部）
        limit: 最多返回条数

    Returns:
        [{kb_id, kb_name, content_count, ...}, ...]
    """
    s = get_settings()
    data = _post(
        _LIST_KB_PATH,
        {
            "query": query or "",
            "cursor": "",
            "limit": max(1, min(limit, s.ima_page_size or limit)),
        },
    )
    info_list = data.get("info_list") or []
    return info_list[:limit] if limit else info_list


def resolve_kb_id(kb_id: str | None = None) -> str:
    """解析 kb_id：显式传入 > 配置 KB_IMA_KB_ID > list 第一个。"""
    if kb_id and kb_id.strip():
        return kb_id.strip()
    s = get_settings()
    if s.ima_kb_id:
        return s.ima_kb_id.strip()
    kbs = list_knowledge_bases(limit=1)
    if not kbs:
        raise IMAConfigError("IMA 账号下未找到任何知识库")
    return kbs[0]["kb_id"]


def search_knowledge(
    query: str,
    kb_id: str | None = None,
    limit: int = 20,
    cursor: str = "",
) -> dict[str, Any]:
    """在指定知识库中检索片段。

    Returns:
        {info_list: [{title, content, url, ...}], cursor, has_more}
    """
    kb_id = resolve_kb_id(kb_id)
    data = _post(
        _SEARCH_KB_PATH,
        {
            "knowledge_base_id": kb_id,
            "query": query,
            "cursor": cursor or "",
            "limit": max(1, min(limit, 50)),
        },
    )
    return {
        "info_list": data.get("info_list") or [],
        "cursor": data.get("cursor") or "",
        "has_more": bool(data.get("has_more")),
    }


def _build_content(item: dict[str, Any]) -> str:
    """把 IMA 检索片段构造为本地 Markdown content。

    IMA search_knowledge 响应每条含 title / content / url（可能为空）。
    """
    title = (item.get("title") or "").strip() or "未命名"
    content = (item.get("content") or "").strip()
    url = (item.get("url") or "").strip()
    lines = [f"# {title}\n"]
    if content:
        lines.append(content)
    if url:
        lines.append(f"\n原文链接：{url}")
    return "\n".join(lines).strip()


def sync_knowledge_base(
    query: str = "",
    kb_id: str | None = None,
    limit: int = 50,
    category: str = "资料",
    importer: ImportService | None = None,
) -> dict[str, Any]:
    """把 IMA 知识库内容同步到本地（去重 source_id=ima:<kb_id>:<item_id>）。

    Args:
        query: 检索关键词（空串则用通配 "*" 拉取，IMA 行为是返回热门/全部）
        kb_id: 目标知识库 ID（None 走 resolve_kb_id）
        limit: 最多同步条数
        category: 本地文档分类，默认 "资料"
        importer: 导入器（None 时新建）

    Returns:
        {kb_id, imported, skipped, failed, items}
    """
    kb_id = resolve_kb_id(kb_id)
    importer = importer or ImportService()
    # 用 query 或 "*" 让 IMA 返回尽量多条目；分页拉满 limit
    fetched = 0
    cursor = ""
    imported = 0
    skipped = 0
    failed = 0
    items: list[dict[str, Any]] = []
    page_size = max(1, min(get_settings().ima_page_size, 50))

    while fetched < limit:
        page_limit = min(page_size, limit - fetched)
        try:
            page = search_knowledge(
                query=query or "*",
                kb_id=kb_id,
                limit=page_limit,
                cursor=cursor,
            )
        except IMAAPIError as e:
            _logger.warning("IMA search_knowledge 失败: %s", e)
            failed += 1
            break
        info_list = page.get("info_list") or []
        if not info_list:
            break
        for item in info_list:
            fetched += 1
            title = (item.get("title") or "").strip() or "未命名"
            # IMA item_id：优先 item_id / doc_id / url hash 兜底
            item_id = (
                item.get("item_id")
                or item.get("doc_id")
                or item.get("id")
                or str(hash(item.get("url") or title))
            )
            source_id = f"ima:{kb_id}:{item_id}"
            # 去重
            try:
                with get_session() as session:
                    existing = session.exec(
                        select(Document).where(
                            Document.source == "ima",
                            Document.source_id == source_id,
                        )
                    ).first()
                    if existing:
                        skipped += 1
                        items.append({
                            "title": title,
                            "doc_id": existing.doc_id,
                            "status": "skipped",
                        })
                        continue
            except Exception as e:
                _logger.warning("IMA 去重查询失败: %s", e)
                failed += 1
                continue
            # 导入
            try:
                content = _build_content(item)
                result = importer.import_text(
                    content=content,
                    title=title,
                    category=category,
                    source="ima",
                    source_id=source_id,
                    verified=False,  # 外部源默认待审核
                    source_type="url" if item.get("url") else "local",
                    file_type="md",
                )
                doc_id = result.get("doc_id") if isinstance(result, dict) else result
                if doc_id:
                    imported += 1
                    items.append({
                        "title": title,
                        "doc_id": doc_id,
                        "status": "imported",
                    })
                else:
                    failed += 1
            except Exception as e:
                _logger.warning("IMA 导入失败 (%s): %s", title, e)
                failed += 1
        cursor = page.get("cursor") or ""
        if not page.get("has_more") or not cursor:
            break

    return {
        "kb_id": kb_id,
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
        "items": items,
    }
