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
    """从 dict 构造 SQLModel 实例（datetime 字段特殊处理 + 未知字段过滤）。

    M5 兼容性：导出 JSON 可能来自新旧不同 schema 版本（旧版导出缺少新字段，
    新版导出含已删除字段）。未识别字段直接传给 model(**kwargs) 会触发
    TypeError 导致整行失败。这里按 model.__table__.columns 白名单过滤，
    缺失字段由 SQLModel 默认值兜底，多余字段静默丢弃并计入 unknown 统计。
    """
    valid_cols = {c.name for c in model.__table__.columns}
    # Document 模型有 metadata property 映射到 meta 列；导出可能用任一键
    if model is Document:
        valid_cols.update({"metadata"})  # __init__ 会把 metadata 映射到 meta
    kwargs: dict[str, Any] = {}
    unknown: list[str] = []
    for k, v in row.items():
        if k in valid_cols:
            kwargs[k] = v
        else:
            unknown.append(k)
    # datetime 字段从 ISO 字符串恢复
    for col in model.__table__.columns:
        if _is_datetime_col(col) and col.name in kwargs:
            kwargs[col.name] = _parse_dt(kwargs[col.name])
    instance = model(**kwargs)
    # 挂载未知字段统计供调用方记录（不阻塞导入）
    if unknown:
        instance._import_unknown_fields = unknown  # type: ignore[attr-defined]
    return instance


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

    注：
    - 向量表不恢复（导出未包含），需要后续重新向量化。
    - ``audit_logs`` 表不导入（审计日志应为 append-only，导入会破坏审计链完整性）。
    - 单行失败计入 ``failed_counts`` 并记录错误，不阻塞整体导入。
    - 上传文件大小上限 50MB（防 OOM）。
    - M5：导出 JSON 中的未知字段（schema 版本差异）静默丢弃，并在响应
      ``unknown_fields`` 中列出，便于运维识别版本漂移。
    - H3：每 1000 行分批 commit，避免长事务阻塞其他写入者。
    """
    # 大小校验：先读 chunk 累计，超限直接 413
    max_size = 50 * 1024 * 1024  # 50MB
    chunks: list[bytes] = []
    total_read = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"上传文件超过上限 {max_size // 1024 // 1024}MB",
            )
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not raw:
        raise HTTPException(status_code=400, detail="上传文件为空")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {e}") from e
    _validate_import_payload(data)
    tables = data["tables"]

    # 导入顺序：先无 FK 依赖的表，后有依赖的
    # 注：audit_logs 不导入——审计日志应 append-only，导入会覆盖现有审计链。
    # 当前实现的 import 会写一条新的 action=import 审计记录，足够追溯。
    import_order = [
        ("documents", Document),
        ("tags", Tag),
        ("query_logs", QueryLog),
        # ("audit_logs", AuditLog),  # 跳过：保护审计完整性
        ("missing_ingredient_stats", MissingIngredientStats),
        ("ingredient_substitutes", IngredientSubstitute),
        ("chunks", Chunk),
        ("document_tags", DocumentTag),
        ("recipe_stats", RecipeStats),
        ("recipe_variants", RecipeVariant),
    ]

    counts: dict[str, int] = {}
    failed_counts: dict[str, int] = {}
    unknown_fields_seen: dict[str, set[str]] = {}
    errors: list[dict[str, Any]] = []
    # H3：分批 commit 减少长事务持锁时间（每 1000 行提交一次）
    # SQLite WAL 模式下，长事务会阻塞其他写入者并增大 -wal 文件。
    # 分批提交让其他写请求能交错进行，也降低 OOM 风险（merge 对象不累积）。
    _BATCH_SIZE = 1000
    with get_session() as session:
        for name, model in import_order:
            rows = tables.get(name, [])
            inserted = 0
            failed = 0
            for row_idx, row in enumerate(rows):
                # 跳过空行
                if not row:
                    continue
                try:
                    instance = _import_row(model, row)
                    session.merge(instance)
                    inserted += 1
                    # 收集未知字段（M5 兼容性报告）
                    unknown = getattr(instance, "_import_unknown_fields", None)
                    if unknown:
                        unknown_fields_seen.setdefault(name, set()).update(unknown)
                    # H3：每 _BATCH_SIZE 行提交一次，释放锁与内存
                    if inserted % _BATCH_SIZE == 0:
                        session.commit()
                except Exception as e:
                    # 单行失败不阻塞整体导入，但记录失败计数与详情
                    failed += 1
                    if len(errors) < 50:  # 限制错误列表大小
                        errors.append({
                            "table": name,
                            "row_index": row_idx,
                            "reason": str(e)[:200],
                        })
            counts[name] = inserted
            if failed > 0:
                failed_counts[name] = failed
        # 最终提交（剩余未提交的行）
        session.commit()

    # 重建历史 FTS5 索引（触发器只对 INSERT/UPDATE/DELETE 生效，merge 不会
    # 显式触发——补一次 backfill 保证 history_fts 与 querylog 一致）
    backfill_history_fts()

    # 审计导入动作
    unknown_fields_summary = {
        name: sorted(fields) for name, fields in unknown_fields_seen.items()
    }
    log_action(
        action="import",
        target_type="database",
        target_id="all",
        user=extract_user(payload),
        meta={
            "version": data.get("version", "unknown"),
            "counts": counts,
            "failed_counts": failed_counts,
            "errors_count": sum(failed_counts.values()),
            "unknown_fields": unknown_fields_summary,
            "source": "export-import",
        },
    )
    return {
        "status": "imported",
        "version": data.get("version", "unknown"),
        "counts": counts,
        "failed_counts": failed_counts,
        "errors": errors,
        # M5：报告被丢弃的未知字段，帮助运维识别 schema 版本差异
        "unknown_fields": unknown_fields_summary,
        "total": sum(counts.values()),
        "total_failed": sum(failed_counts.values()),
    }
