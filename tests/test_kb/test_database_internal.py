"""database.py 内部函数专项测试（H1 补充）。

覆盖路径：
1. init_db：无参调用（eng=None → get_engine 已完成初始化）
2. init_db：alembic 迁移失败 → 回退 create_all
3. run_migrations：alembic.ini 未找到 → FileNotFoundError
4. run_migrations：alembic command.upgrade 抛异常 → 上抛
5. _find_alembic_ini：找不到返回 None
6. _migrate_vec_to_ann：增量迁移（含跳过无效 JSON / 维度不符）
7. _load_sqlite_vec：加载异常时软降级（logger.warning）
8. reset_engine：重置引擎单例
9. get_engine：并发初始化安全（双重检查锁）
10. get_session：正常产出会话
"""
from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text as sa_text

from hermes_kb import database as db_mod


def test_init_db_no_engine_uses_get_engine(monkeypatch):
    """eng=None 时复用 get_engine（已初始化），不重复执行。"""
    calls: list[str] = []

    def fake_get_engine():
        calls.append("get_engine")
        return MagicMock()

    monkeypatch.setattr(db_mod, "get_engine", fake_get_engine)
    db_mod.init_db()
    assert calls == ["get_engine"]


def test_init_db_falls_back_to_create_all(tmp_db, monkeypatch):
    """alembic 迁移失败 → 回退 create_all + FTS/向量表初始化。"""
    from sqlalchemy import inspect

    # 强制 run_migrations 抛异常
    monkeypatch.setattr(
        db_mod, "run_migrations",
        lambda: (_ for _ in ()).throw(RuntimeError("alembic down")),
    )
    # 重置引擎单例，触发 init_db 重新执行
    db_mod.reset_engine()
    eng2 = db_mod.get_engine()
    # 表应存在（create_all fallback）
    tables = inspect(eng2).get_table_names()
    assert "document" in tables
    assert "chunk" in tables


def test_run_migrations_ini_not_found(monkeypatch):
    """alembic.ini 未找到 → FileNotFoundError。"""
    monkeypatch.setattr(db_mod, "_find_alembic_ini", lambda: None)
    with pytest.raises(FileNotFoundError, match="alembic.ini"):
        db_mod.run_migrations()


def test_run_migrations_upgrade_error(tmp_db, monkeypatch):
    """command.upgrade 失败 → 异常上抛（由 init_db 捕获降级）。"""
    import alembic.command

    def boom(cfg, rev):
        raise RuntimeError("upgrade failed")

    monkeypatch.setattr(alembic.command, "upgrade", boom)
    with pytest.raises(RuntimeError, match="upgrade failed"):
        db_mod.run_migrations()


def test_find_alembic_ini_returns_none(tmp_path, monkeypatch):
    """向上查找无结果 → None。"""
    # 所有候选目录的 alembic.ini 都被视为不存在
    def fake_is_file(self):
        return False

    monkeypatch.setattr(Path, "is_file", fake_is_file)
    assert db_mod._find_alembic_ini() is None


def test_reset_engine_clears_singleton():
    """reset_engine 后 _ENGINE 为 None，dispose 被调用。"""
    db_mod.reset_engine()
    eng = db_mod.get_engine()
    assert db_mod._ENGINE is eng
    db_mod.reset_engine()
    assert db_mod._ENGINE is None


def test_get_engine_concurrent_init(tmp_db):
    """并发 get_engine 仅初始化一次引擎。"""
    db_mod.reset_engine()
    engines = []

    def worker():
        engines.append(db_mod.get_engine())

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len({id(e) for e in engines}) == 1


def test_get_session_yields_session(tmp_db):
    """get_session 正常产出可用的会话。"""
    with db_mod.get_session() as session:
        assert session is not None
        # 可执行查询
        session.execute(sa_text("SELECT 1"))


def test_load_sqlite_vec_when_unavailable(monkeypatch):
    """_SQLITE_VEC_AVAILABLE=False 时直接返回。"""
    monkeypatch.setattr(db_mod, "_SQLITE_VEC_AVAILABLE", False)
    # 不应抛异常
    db_mod._load_sqlite_vec(MagicMock())


def test_load_sqlite_vec_load_failure(monkeypatch):
    """扩展加载失败 → logger.warning 软降级。"""
    monkeypatch.setattr(db_mod, "_SQLITE_VEC_AVAILABLE", True)

    class BoomConn:
        def enable_load_extension(self, flag):
            raise RuntimeError("no extension support")

    with patch.object(db_mod.log, "warning") as mock_warn:
        db_mod._load_sqlite_vec(BoomConn())
    assert mock_warn.called


def test_migrate_vec_to_ann_skips_bad_rows(tmp_db, monkeypatch):
    """_migrate_vec_to_ann 跳过无效 JSON / 维度不符行，正常行迁移。"""
    if not db_mod._SQLITE_VEC_AVAILABLE:
        pytest.skip("sqlite-vec 不可用，跳过 ANN 迁移测试")

    db_mod.reset_engine()
    eng = db_mod.get_engine()
    dim = db_mod.get_settings().embedding_dim

    # 手工插入 chunk_vec 行（bad JSON / 维度不符 / 正常）
    with eng.begin() as conn:
        conn.execute(sa_text(
            "INSERT INTO chunk_vec(chunk_rowid, doc_id, vec) VALUES (9001, 'd1', 'not json')"
        ))
        conn.execute(sa_text(
            "INSERT INTO chunk_vec(chunk_rowid, doc_id, vec) VALUES (9002, 'd2', '[]')"
        ))
        conn.execute(sa_text(
            "INSERT INTO chunk_vec(chunk_rowid, doc_id, vec) "
            "VALUES (9003, 'd3', '[1.0]')"
        ))
        good = "[" + ",".join(["0.1"] * dim) + "]"
        conn.execute(sa_text(
            "INSERT INTO chunk_vec(chunk_rowid, doc_id, vec) "
            "VALUES (9004, 'd4', :v)"
        ), {"v": good})

    with patch.object(db_mod.log, "info") as mock_info:
        db_mod._migrate_vec_to_ann(eng, dim)

    # 9004 应被迁移；其余被跳过
    with eng.connect() as conn:
        rows = conn.execute(sa_text(
            "SELECT rowid FROM chunk_vec_ann ORDER BY rowid"
        )).fetchall()
    rowids = [r[0] for r in rows]
    assert 9004 in rowids
    assert 9001 not in rowids
    assert 9002 not in rowids
    assert 9003 not in rowids
    # 迁移日志只记录有成功迁移的情况
    assert mock_info.called


def test_migrate_vec_to_ann_no_rows(tmp_db):
    """无待迁移行时静默返回。"""
    if not db_mod._SQLITE_VEC_AVAILABLE:
        pytest.skip("sqlite-vec 不可用，跳过 ANN 迁移测试")

    db_mod.reset_engine()
    eng = db_mod.get_engine()
    dim = db_mod.get_settings().embedding_dim
    with patch.object(db_mod.log, "info") as mock_info:
        db_mod._migrate_vec_to_ann(eng, dim)
    assert not mock_info.called
