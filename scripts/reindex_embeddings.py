#!/usr/bin/env python3
"""Embedding 重建脚本（切换 provider 后重建所有 chunk 的向量索引）。

用法：
    python scripts/reindex_embeddings.py [--batch-size N] [--dry-run]

工作流：
1. 读取所有 chunk（id, doc_id, text）
2. 用 EmbeddingService 批量生成新向量
3. 清空 chunk_vec 表
4. 如 sqlite-vec 可用：
   - DROP TABLE chunk_vec_ann
   - 用新维度 CREATE VIRTUAL TABLE chunk_vec_ann USING vec0(embedding float[新维度])
   - 重建触发器 chunk_ad_vec
5. 批量插入新向量到 chunk_vec（JSON 格式）+ chunk_vec_ann（二进制格式）
6. 输出统计：总 chunk 数 / 成功数 / 失败数 / 耗时

注意：
- 切换 provider 后向量维度可能变化（hash=256, bge-small-zh-v1.5=512）
- sqlite-vec 可能不可用（_SQLITE_VEC_AVAILABLE=False），此时只更新 chunk_vec
- 需先在 .env 配置好新的 KB_EMBEDDING_PROVIDER 等变量再运行
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path

# Windows UTF-8 输出（避免中文/特殊字符在 cp936 下报错）
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

# 让脚本无需安装即可运行
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# 项目记忆：config.py 不自动加载 .env，需手动加载
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from sqlalchemy import text as sa_text  # noqa: E402

from hermes_kb.config import get_settings  # noqa: E402
from hermes_kb.database import (  # noqa: E402
    _SQLITE_VEC_AVAILABLE,
    get_engine,
)
from hermes_kb.embedding import EmbeddingService  # noqa: E402


def _serialize_vec(vec: list[float]) -> bytes:
    """将 float 列表序列化为 sqlite-vec 二进制格式（float32）。"""
    return struct.pack(f"{len(vec)}f", *vec)


def _detect_old_dim(conn) -> int | None:
    """检测现有 chunk_vec 表中的向量维度。

    返回 None 表示表为空或不存在（用于报告中的 "was X" 字段）。
    """
    try:
        row = conn.execute(sa_text("SELECT vec FROM chunk_vec LIMIT 1")).fetchone()
    except Exception:  # noqa: BLE001 — 表不存在或 schema 异常，统一视为无旧维度
        return None
    if not row:
        return None
    try:
        vec = json.loads(row[0])
        return len(vec) if isinstance(vec, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _provider_model_name(settings) -> str:
    """根据 provider 返回对应模型名（用于报告输出）。"""
    provider = settings.embedding_provider.lower()
    if provider == "sentence_transformers":
        return settings.embedding_st_model
    if provider == "openai":
        return settings.embedding_model
    return "hash"


def _recreate_ann_table(conn, new_dim: int) -> None:
    """DROP + CREATE chunk_vec_ann + 重建触发器。

    维度变化或 schema 重置时调用。DROP TABLE IF EXISTS 保证幂等（旧表残留也安全）。
    """
    conn.execute(sa_text("DROP TABLE IF EXISTS chunk_vec_ann"))
    conn.execute(
        sa_text(
            f"CREATE VIRTUAL TABLE chunk_vec_ann USING vec0(embedding float[{new_dim}])"
        )
    )
    # 重建删除触发器：vec0 不支持 INSERT OR REPLACE，必须随 chunk 删除清理 rowid，
    # 否则 SQLite 复用 rowid 时触发 UNIQUE 冲突，破坏后续导入。
    conn.execute(
        sa_text(
            "CREATE TRIGGER IF NOT EXISTS chunk_ad_vec "
            "AFTER DELETE ON chunk BEGIN "
            "DELETE FROM chunk_vec_ann WHERE rowid = old.id; "
            "END"
        )
    )


def _embed_with_fallback(embedding: EmbeddingService, texts: list[str], new_dim: int) -> tuple[list[list[float]], int]:
    """批量生成向量，失败时逐条降级。

    返回 (fixed_vectors, failed_count)。fixed_vectors 长度恒等于 len(texts)，
    生成失败或维度不匹配的项填充为零向量，并计入 failed_count。
    """
    failed = 0
    try:
        raw = embedding.embed(texts)
    except Exception as exc:  # noqa: BLE001 — 单批失败不阻塞整批，逐条降级
        print(f"[warn] batch embed 失败（{len(texts)} 条），逐条降级: {exc}", file=sys.stderr)
        raw = []
        for t in texts:
            try:
                v = embedding.embed([t])
                raw.extend(v)
            except Exception as exc2:  # noqa: BLE001
                print(f"[warn] 单条 embed 失败: {exc2}", file=sys.stderr)
                raw.append([])  # 占位空向量，后续兜底为零向量

    # 维度兜底：返回向量数不足或维度不匹配时填充零向量
    fixed: list[list[float]] = []
    for i, v in enumerate(raw):
        if v and len(v) == new_dim:
            fixed.append(v)
        else:
            fixed.append([0.0] * new_dim)
            # 仅当原始返回不为空（即确实生成失败而非数量不足）时计为失败；
            # 数量不足的占位项 [] 上面已 append，这里统一计为失败
            failed += 1
    # 数量不足时补齐
    while len(fixed) < len(texts):
        fixed.append([0.0] * new_dim)
        failed += 1
    return fixed, failed


def _write_batch(
    engine,
    ids: list[int],
    doc_ids: list[str],
    vectors: list[list[float]],
    ann_ready: bool,
) -> tuple[int, int]:
    """写入一批向量到 chunk_vec + chunk_vec_ann。

    策略：整批一个事务（性能优先）；任意行失败则整批回滚，逐条降级重试。
    返回 (success_count, failed_count)。
    """
    if not ids:
        return 0, 0
    try:
        with engine.begin() as conn:
            for rid, doc_id, vec in zip(ids, doc_ids, vectors):
                conn.execute(
                    sa_text(
                        "INSERT INTO chunk_vec (chunk_rowid, doc_id, vec) "
                        "VALUES (:rowid, :doc_id, :vec)"
                    ),
                    {"rowid": rid, "doc_id": doc_id, "vec": json.dumps(vec)},
                )
                if _SQLITE_VEC_AVAILABLE and ann_ready:
                    # ANN 写入失败不阻塞 chunk_vec（读路径可降级 Python 余弦扫描）
                    try:
                        conn.execute(
                            sa_text(
                                "INSERT INTO chunk_vec_ann (rowid, embedding) "
                                "VALUES (:rowid, :embedding)"
                            ),
                            {"rowid": rid, "embedding": _serialize_vec(vec)},
                        )
                    except Exception as ann_exc:  # noqa: BLE001
                        print(
                            f"[warn] chunk_vec_ann 写入失败 rowid={rid}: {ann_exc}",
                            file=sys.stderr,
                        )
        return len(ids), 0
    except Exception as exc:  # noqa: BLE001 — 整批事务失败，逐条降级
        print(f"[warn] 批次事务失败，逐条降级: {exc}", file=sys.stderr)
        success = 0
        failed = 0
        for rid, doc_id, vec in zip(ids, doc_ids, vectors):
            try:
                with engine.begin() as conn:
                    conn.execute(
                        sa_text(
                            "INSERT INTO chunk_vec (chunk_rowid, doc_id, vec) "
                            "VALUES (:rowid, :doc_id, :vec)"
                        ),
                        {"rowid": rid, "doc_id": doc_id, "vec": json.dumps(vec)},
                    )
                    if _SQLITE_VEC_AVAILABLE and ann_ready:
                        try:
                            conn.execute(
                                sa_text(
                                    "INSERT INTO chunk_vec_ann (rowid, embedding) "
                                    "VALUES (:rowid, :embedding)"
                                ),
                                {"rowid": rid, "embedding": _serialize_vec(vec)},
                            )
                        except Exception as ann_exc:  # noqa: BLE001
                            print(
                                f"[warn] chunk_vec_ann 写入失败 rowid={rid}: {ann_exc}",
                                file=sys.stderr,
                            )
                success += 1
            except Exception as exc2:  # noqa: BLE001
                failed += 1
                print(f"[warn] chunk rowid={rid} 写入失败: {exc2}", file=sys.stderr)
        return success, failed


def main() -> int:
    parser = argparse.ArgumentParser(description="重建所有 chunk 的向量索引")
    parser.add_argument(
        "--batch-size", type=int, default=32, help="批大小（默认 32）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅测试 embedding 生成，不写入数据库",
    )
    args = parser.parse_args()

    batch_size = max(1, args.batch_size)
    dry_run = args.dry_run

    settings = get_settings()
    engine = get_engine()
    embedding = EmbeddingService()
    new_dim = embedding.dim

    # 读取所有 chunk + 检测旧维度（非破坏性 SELECT）
    with engine.connect() as conn:
        old_dim = _detect_old_dim(conn)
        rows = conn.execute(
            sa_text("SELECT id, doc_id, text FROM chunk ORDER BY id")
        ).fetchall()

    total = len(rows)
    print(f"[reindex] 共 {total} 个 chunk", file=sys.stderr)
    print(
        f"[reindex] provider={settings.embedding_provider} "
        f"model={_provider_model_name(settings)} dim={new_dim}"
        f"{f' (was {old_dim})' if old_dim is not None else ''}",
        file=sys.stderr,
    )
    if dry_run:
        print("[reindex] dry-run 模式：仅测试 embedding 生成，不写入数据库", file=sys.stderr)

    # 准备数据库：清空 chunk_vec + 重建 ANN 表（独立事务，重建失败不回滚清空）
    ann_ready = False
    if not dry_run:
        with engine.begin() as conn:
            conn.execute(sa_text("DELETE FROM chunk_vec"))
        if _SQLITE_VEC_AVAILABLE:
            try:
                with engine.begin() as conn:
                    _recreate_ann_table(conn, new_dim)
                ann_ready = True
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[warn] chunk_vec_ann 重建失败，将仅写入 chunk_vec: {exc}",
                    file=sys.stderr,
                )
                ann_ready = False

    # 分批生成 + 写入
    success = 0
    failed = 0
    t_start = time.perf_counter()
    last_progress = 0

    for start in range(0, total, batch_size):
        batch = rows[start : start + batch_size]
        ids = [int(r[0]) for r in batch]
        doc_ids = [r[1] for r in batch]
        texts = [r[2] or "" for r in batch]

        # 批量生成向量（含逐条降级）
        vectors, gen_failed = _embed_with_fallback(embedding, texts, new_dim)

        if dry_run:
            # dry-run：仅统计生成成功/失败
            success += len(ids) - gen_failed
            failed += gen_failed
        else:
            # 写入 DB（整批事务，失败逐条降级）
            ok, fail = _write_batch(engine, ids, doc_ids, vectors, ann_ready)
            success += ok
            failed += fail

        # 进度提示：每 100 条或最后一批输出
        processed = min(start + batch_size, total)
        if processed - last_progress >= 100 or processed == total:
            print(f"[reindex] 进度 {processed}/{total}", file=sys.stderr)
            last_progress = processed

    elapsed = time.perf_counter() - t_start

    # 报告
    print("Embedding Reindex Report")
    print("=" * 24)
    print(f"Provider: {settings.embedding_provider}")
    print(f"Model: {_provider_model_name(settings)}")
    dim_line = f"Dimension: {new_dim}"
    if old_dim is not None and old_dim != new_dim:
        dim_line += f" (was {old_dim})"
    print(dim_line)
    print(f"Total chunks: {total}")
    print(f"Successfully indexed: {success}")
    print(f"Failed: {failed}")
    print(f"Batch size: {batch_size}")
    print(f"Time: {elapsed:.1f}s")
    print(
        f"sqlite-vec: {'available' if _SQLITE_VEC_AVAILABLE else 'unavailable'}"
    )
    if dry_run:
        print("(dry-run: 未写入数据库)")
    elif not ann_ready and _SQLITE_VEC_AVAILABLE:
        print("(chunk_vec_ann 重建失败，仅 chunk_vec 已更新)")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
