"""Obsidian vault 集成 API 端点（V4-Phase1）。

提供：
- GET  /api/obsidian/status   查询 vault 集成状态
- POST /api/obsidian/sync      触发全量/增量扫描同步
- POST /api/obsidian/watch     启动/停止实时监听
- POST /api/obsidian/export    反向同步：UGC 配方导出到 vault
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hermes_kb.api.deps import require_age_gate, require_auth
from hermes_kb.config import get_settings
from hermes_kb.obsidian_sync import (
    VaultConfigError,
    VaultSyncError,
    export_doc_to_vault,
    get_vault_status,
    list_synced_docs,
    scan_vault,
    start_watcher,
    stop_watcher,
)

router = APIRouter(prefix="/api/obsidian", tags=["obsidian"])


class ExportRequest(BaseModel):
    """反向同步请求体。"""

    doc_id: str


@router.get("/status", dependencies=[Depends(require_age_gate)])
async def obsidian_status() -> dict[str, Any]:
    """查询 Obsidian vault 集成状态。"""
    from hermes_kb.obsidian_sync import _watcher

    watching = _watcher is not None and _watcher.is_running
    status = get_vault_status(watching=watching)
    return status.to_dict()


@router.get("/docs", dependencies=[Depends(require_age_gate)])
async def obsidian_docs(limit: int = 200) -> dict[str, Any]:
    """列出已同步的 Obsidian vault 文档（source=obsidian）。"""
    docs = list_synced_docs(limit=limit)
    return {"total": len(docs), "items": docs}


@router.post("/sync", dependencies=[Depends(require_age_gate)])
async def obsidian_sync(
    incremental: bool = True,
    payload: dict[str, Any] | None = Depends(require_auth),
) -> dict[str, Any]:
    """触发 vault 全量/增量扫描同步。

    Args:
        incremental: True=仅同步变更文件（基于 mtime）；False=全量重扫
    """
    settings = get_settings()
    if not settings.vault_enabled:
        raise HTTPException(
            status_code=400,
            detail=f"vault 未启用：KB_VAULT_PATH 未配置或路径不存在（当前值：{settings.vault_path!r}）",
        )
    try:
        result = scan_vault(incremental=incremental)
        return {"status": "ok", **result.to_dict()}
    except VaultConfigError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败：{e}") from e


@router.post("/watch", dependencies=[Depends(require_age_gate)])
async def obsidian_watch(
    enable: bool = True,
    payload: dict[str, Any] | None = Depends(require_auth),
) -> dict[str, Any]:
    """启动/停止 vault 实时监听（需 watchdog）。

    Args:
        enable: True=启动监听；False=停止
    """
    settings = get_settings()
    if enable and not settings.vault_enabled:
        raise HTTPException(
            status_code=400,
            detail="vault 未启用，无法启动监听",
        )
    if enable:
        ok = start_watcher()
        if not ok:
            raise HTTPException(
                status_code=400,
                detail="监听启动失败：watchdog 未安装或 vault 路径无效",
            )
        return {"status": "watching", "watching": True}
    else:
        stop_watcher()
        return {"status": "stopped", "watching": False}


@router.post("/export", dependencies=[Depends(require_age_gate)])
async def obsidian_export(
    req: ExportRequest,
    payload: dict[str, Any] | None = Depends(require_auth),
) -> dict[str, Any]:
    """V4-Phase2+：将任意文档导出为 .md 到 vault/Hermes/ 子目录（不再限 UGC）。"""
    settings = get_settings()
    if not settings.vault_enabled:
        raise HTTPException(
            status_code=400,
            detail="vault 未启用，无法导出",
        )
    try:
        rel_path = export_doc_to_vault(req.doc_id)
        return {"status": "ok", "path": rel_path, "doc_id": req.doc_id}
    except VaultConfigError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except VaultSyncError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败：{e}") from e
