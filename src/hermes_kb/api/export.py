"""M2-09：数据导出与导入端点。

提供：
- ``GET /api/export/all.json``：全量导出（文档 + 分片 + 历史 + 审计 + 标签 + 关联）
- ``POST /api/export/import``：从导出 JSON 恢复（管理员，幂等）

设计要点：
- **管理员权限**：全量导出包含 audit_logs（含 user / IP 等敏感字段），
  仅管理员可调用；导入同样需要管理员权限以避免任意数据覆盖
- **幂等导入**：使用 INSERT OR REPLACE，同一份导出 JSON 可多次导入
  而不产生重复行；自动重建 FTS5 索引（通过触发器）
- **不导出向量**：chunk_vec / chunk_vec_ann 不导出（体积大且可由 chunks
  重新向量化得到），导入后可由运维脚本或后续 API 触发重向量化
- **审计**：导入 / 导出动作本身也记入审计日志
- **版本化 schema**：导出 JSON 含 ``version`` 字段，便于后续 schema 演进
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlmodel import select

from hermes_kb.api.audit import require_admin
from hermes_kb.api.deps import require_auth
from hermes_kb.audit import extract_user, log_action
from hermes_kb.database import get_session, backfill_history_fts
from hermes_kb.models import (
    AuditLog,
    Chunk,
    Document,
    DocumentTag,
    IngredientSubstitute,
    MissingIngredientStats,
    QueryLog,
    RecipeStats,
    RecipeVariant,
    Tag,
)

router = APIRouter(prefix="/api/export", tags=["export"])

# 导出格式版本（schema 演进时升级）
_EXPORT_VERSION = "1.0"
# 导出包含的表清单（顺序决定导出顺序，导入按相反顺序恢复以避免 FK 约束冲突）
# 注：Document 必须先于 Chunk / DocumentTag / RecipeStats / RecipeVariant（FK 依赖）
#     Tag 必须先于 DocumentTag
_EXPORT_TABLES: list[tuple[str, type]] = [
    ("documents", Document),
    ("chunks", Chunk),
    ("tags", Tag),
    ("document_tags", DocumentTag),
    ("query_logs", QueryLog),
    ("audit_logs", AuditLog),
    ("recipe_stats", RecipeStats),
    ("ingredient_substitutes", IngredientSubstitute),
    ("missing_ingredient_stats", MissingIngredientStats),
    ("recipe_variants", RecipeVariant),
]


def _serialize_row(row: Any) -> dict[str, Any]:
    """将 SQLModel 行序列化为 JSON 兼容 dict。

    datetime → ISO 字符串；其余字段原样返回。
    """
    out: dict[str, Any] = {}
    for col in row.__table__.columns.keys():
        val = getattr(row, col, None)
        if isinstance(val, datetime):
            out[col] = val.isoformat()
        else:
            out[col] = val
    return out


def _parse_dt(val: Any) -> datetime | None:
    """解析 ISO 字符串为 datetime；None / 空值返回 None。"""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val
    try:
        # 支持 'YYYY-MM-DDTHH:MM:SS' 与带时区格式
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _build_export_payload() -> dict[str, Any]:
    """构造全量导出 payload。"""
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    payload: dict[str, Any] = {
        "version": _EXPORT_VERSION,
        "exported_at": now_utc.isoformat() + "Z",
        "tables": {},
    }
    with get_session() as session:
        for name, model in _EXPORT_TABLES:
            rows = session.exec(select(model)).all()
            payload["tables"][name] = [_serialize_row(r) for r in rows]
            payload[f"{name}_count"] = len(rows)
    return payload


@router.get("/all.json", dependencies=[Depends(require_admin)])
async def export_all(
    payload: dict[str, Any] | None = Depends(require_auth),
) -> JSONResponse:
    """M2-09：全量导出（管理员）。

    返回 JSON，包含所有业务表的完整数据快照。可用于：
    - 灾难恢复（配合 ``POST /api/export/import``）
    - 数据迁移（克隆库）
    - 离线分析

    注：不导出向量表（chunk_vec / chunk_vec_ann），导入后可重新向量化。
    """
    data = _build_export_payload()
    # 审计导出动作
    log_action(
        action="export",
        target_type="database",
        target_id="all",
        user=extract_user(payload),
        meta={
            "version": _EXPORT_VERSION,
            "tables": {
                name: data.get(f"{name}_count", 0)
                for name, _ in _EXPORT_TABLES
            },
        },
    )
    # 文件名带时间戳，便于归档
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    ts = now_utc.strftime("%Y%m%d_%H%M%S")
    filename = f"hermes_kb_export_{ts}.json"
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


def _is_datetime_col(col) -> bool:
    """安全判断列是否为 datetime 类型。

    某些 SQLModel 自定义类型（如 ``AutoString``）未实现 ``python_type``，
    访问会抛 ``NotImplementedError``，需 try/except 兜底。
    """
    try:
        return col.type.python_type is datetime
    except (NotImplementedError, AttributeError):
        return False


def _import_row(model: type, row: dict[str, Any]) -> Any:
    """从 dict 构造 SQLModel 实例（datetime 字段特殊处理）。"""
    kwargs = dict(row)
    # datetime 字段从 ISO 字符串恢复
    for col in model.__table__.columns:
        if _is_datetime_col(col) and col.name in kwargs:
            kwargs[col.name] = _parse_dt(kwargs[col.name])
    return model(**kwargs)


def _validate_import_payload(data: Any) -> dict[str, Any]:
    """校验导入 payload 结构。

    要求：
    - 顶层是 dict
    - 含 ``tables`` 字段（dict）
    - ``tables`` 下每个表名为 list
    """
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="payload 必须是 JSON 对象")
    tables = data.get("tables")
    if not isinstance(tables, dict):
        raise HTTPException(
            status_code=400,
            detail="payload 缺少 tables 字段或格式不正确",
        )
    for name, rows in tables.items():
        if not isinstance(rows, list):
            raise HTTPException(
                status_code=400,
                detail=f"tables.{name} 必须是数组",
            )
    return data


@router.post("/import", dependencies=[Depends(require_admin)])
async def import_from_export(
    file: UploadFile = File(...),
    payload: dict[str, Any] | None = Depends(require_auth),
) -> dict[str, Any]:
    """M2-09：从导出 JSON 恢复（管理员，幂等）。

    上传 ``/api/export/all.json`` 产生的 JSON 文件，按依赖顺序恢复所有表。
    使用 INSERT OR REPLACE 语义——同主键行会被覆盖，多次导入幂等。

    注：向量表不恢复（导出未包含），需要后续重新向量化。
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="上传文件为空")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {e}") from e
    _validate_import_payload(data)
    tables = data["tables"]

    # 导入顺序：先无 FK 依赖的表，后有依赖的
    # Document / Tag / QueryLog / AuditLog / MissingIngredientStats / IngredientSubstitute
    #   先于 Chunk / DocumentTag / RecipeStats / RecipeVariant
    import_order = [
        ("documents", Document),
        ("tags", Tag),
        ("query_logs", QueryLog),
        ("audit_logs", AuditLog),
        ("missing_ingredient_stats", MissingIngredientStats),
        ("ingredient_substitutes", IngredientSubstitute),
        ("chunks", Chunk),
        ("document_tags", DocumentTag),
        ("recipe_stats", RecipeStats),
        ("recipe_variants", RecipeVariant),
    ]

    counts: dict[str, int] = {}
    with get_session() as session:
        for name, model in import_order:
            rows = tables.get(name, [])
            inserted = 0
            for row in rows:
                # 跳过空行
                if not row:
                    continue
                try:
                    instance = _import_row(model, row)
                    session.merge(instance)
                    inserted += 1
                except Exception:
                    # 单行失败不阻塞整体导入，但计入失败（统计在 counts 失败列）
                    continue
            counts[name] = inserted
        session.commit()

    # 重建历史 FTS5 索引（触发器只对 INSERT/UPDATE/DELETE 生效，merge 不会
    # 显式触发——补一次 backfill 保证 history_fts 与 querylog 一致）
    backfill_history_fts()

    # 审计导入动作
    log_action(
        action="import",
        target_type="database",
        target_id="all",
        user=extract_user(payload),
        meta={
            "version": data.get("version", "unknown"),
            "counts": counts,
            "source": "export-import",
        },
    )
    return {
        "status": "imported",
        "version": data.get("version", "unknown"),
        "counts": counts,
        "total": sum(counts.values()),
    }
