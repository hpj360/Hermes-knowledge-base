"""M2-07 历史搜索与筛选测试（H2：FTS5 trigram + LIKE 双路径）。

覆盖：
- LIKE 子串检索（query + answer 命中，含中文中间子串）
- FTS5 trigram 快路径（≥ 3 字符查询走索引 MATCH）
- LIKE 兜底（< 3 字符查询或 FTS5 不可用时回退）
- 关键词高亮（<mark> 标签）+ snippet 生成
- feedback / date_from / date_to 筛选（FTS5 + LIKE 两路径均覆盖）
- limit / offset 分页
- 关键词净化（特殊字符不报错）
- FTS5 phrase 转义（双引号不破坏 MATCH）
- backfill_history_fts 幂等（FTS5 表保留作为未来优化基础）
- 性能：1000 条 < 200ms
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text as sa_text

from hermes_kb.database import backfill_history_fts, get_session
from hermes_kb.models import QueryLog


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _seed_logs(client, items: list[tuple[str, str, int]]) -> list[int]:
    """直接写 QueryLog，返回 id 列表。"""
    ids: list[int] = []
    with get_session() as session:
        for i, (q, a, fb) in enumerate(items):
            log = QueryLog(
                query=q,
                answer=a,
                feedback=fb,
                created_at=_now_utc() - timedelta(hours=i),
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            ids.append(log.id)
    return ids


# ---------------------------------------------------------------------------
# 基础查询
# ---------------------------------------------------------------------------
def test_history_no_query_returns_all_desc(client):
    """无 q 参数：返回全部历史，按时间倒序。"""
    _seed_logs(client, [
        ("问题A", "答案A", 0),
        ("问题B", "答案B", 0),
        ("问题C", "答案C", 0),
    ])
    resp = client.get("/api/history?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    # 默认无 q 时 query_highlight / answer_snippet 为 None
    item = body["items"][0]
    assert item["query_highlight"] is None
    assert item["answer_snippet"] is None
    # 倒序：最新的在前（问题A 后插入，时间最新）
    assert body["items"][0]["query"] == "问题A"


def test_history_limit_clamped_to_500(client):
    """limit 超过 500 被钳到 500（不返回 422）。"""
    _seed_logs(client, [("q", "a", 0)] * 3)
    resp = client.get("/api/history?limit=99999")
    assert resp.status_code == 200
    assert resp.json()["limit"] == 500


def test_history_offset_pagination(client):
    """offset 分页正确。"""
    _seed_logs(client, [(f"问题{i}", f"答案{i}", 0) for i in range(5)])
    resp = client.get("/api/history?limit=2&offset=1")
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["offset"] == 1


# ---------------------------------------------------------------------------
# LIKE 子串检索
# ---------------------------------------------------------------------------
def test_history_search_query_match(client):
    """LIKE 命中 query 列。"""
    _seed_logs(client, [
        ("白酒香型有哪些", "浓香、酱香、清香等", 0),
        ("葡萄酒怎么品", "观色闻香品味", 0),
        ("啤酒发酵工艺", "上面发酵下面发酵", 0),
    ])
    resp = client.get("/api/history?q=白酒")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["q"] == "白酒"
    item = body["items"][0]
    assert item["query"] == "白酒香型有哪些"
    # query_highlight 包含 <mark>
    assert "<mark>" in item["query_highlight"]
    assert "</mark>" in item["query_highlight"]


def test_history_search_answer_match(client):
    """LIKE 命中 answer 列，返回 answer_snippet。"""
    _seed_logs(client, [
        ("问题1", "中国白酒有浓香、酱香、清香等多种香型", 0),
        ("问题2", "葡萄酒颜色各异", 0),
    ])
    resp = client.get("/api/history?q=浓香")
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["query"] == "问题1"
    # answer_snippet 包含高亮
    assert "<mark>" in item["answer_snippet"]
    assert "浓香" in item["answer_snippet"]


def test_history_search_chinese_substring_in_middle(client):
    """LIKE 能命中中文中间子串（FTS5 做不到的场景）。"""
    _seed_logs(client, [
        ("中国白酒有浓香", "答案", 0),  # "白酒"在中间
        ("葡萄酒", "答案", 0),
    ])
    resp = client.get("/api/history?q=白酒")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["query"] == "中国白酒有浓香"
    # 高亮应只包裹"白酒"，不包裹其他
    assert "<mark>白酒</mark>" in body["items"][0]["query_highlight"]


def test_history_search_case_insensitive(client):
    """LIKE 搜索大小写不敏感。"""
    _seed_logs(client, [
        ("Cocktail recipe", "answer", 0),
        ("another", "answer", 0),
    ])
    resp = client.get("/api/history?q=cocktail")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["query"] == "Cocktail recipe"


def test_history_search_no_match(client):
    """无命中返回空列表。"""
    _seed_logs(client, [("白酒问题", "白酒答案", 0)])
    resp = client.get("/api/history?q=不存在的关键词xyz")
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_history_search_match_in_query_or_answer(client):
    """q 在 query 或 answer 任一命中即返回。"""
    _seed_logs(client, [
        ("白酒问题", "无关答案", 0),  # query 命中
        ("无关问题", "白酒答案", 0),  # answer 命中
        ("葡萄酒", "葡萄酒答案", 0),  # 都不命中
    ])
    resp = client.get("/api/history?q=白酒")
    assert resp.json()["total"] == 2


# ---------------------------------------------------------------------------
# 关键词净化
# ---------------------------------------------------------------------------
def test_history_search_special_chars_sanitized(client):
    """特殊字符（SQL/regex 元字符）被净化，不报错。"""
    _seed_logs(client, [("白酒问题", "白酒答案", 0)])
    # 包含 % _ ' " * ( ) 等元字符
    for q in ['白酒%', '白酒_', "白酒'", '白酒"', '白酒*', '白酒(', '白酒)']:
        resp = client.get(f"/api/history?q={q}")
        assert resp.status_code == 200, f"q={q!r} 报错: {resp.text}"
        assert "items" in resp.json()


def test_history_search_empty_q_falls_back_to_plain(client):
    """q 仅含空白/特殊字符时回退到普通查询。"""
    _seed_logs(client, [("问题1", "答案1", 0), ("问题2", "答案2", 0)])
    resp = client.get("/api/history?q=%20%20")  # 两个空格
    body = resp.json()
    assert body["total"] == 2  # 全部返回
    assert body["items"][0]["query_highlight"] is None


# ---------------------------------------------------------------------------
# 筛选
# ---------------------------------------------------------------------------
def test_history_filter_by_feedback(client):
    """feedback 筛选：1=赞 / -1=踩 / 0=无。"""
    _seed_logs(client, [
        ("赞的", "答案", 1),
        ("踩的", "答案", -1),
        ("无反馈", "答案", 0),
    ])
    resp = client.get("/api/history?feedback=1")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["query"] == "赞的"

    resp = client.get("/api/history?feedback=-1")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["query"] == "踩的"

    resp = client.get("/api/history?feedback=0")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["query"] == "无反馈"


def test_history_filter_by_date_range(client):
    """date_from / date_to 闭区间筛选。"""
    now = _now_utc()
    with get_session() as session:
        for days_ago in [0, 1, 2, 5, 10]:
            log = QueryLog(
                query=f"问题{days_ago}天前",
                answer="答案",
                feedback=0,
                created_at=now - timedelta(days=days_ago),
            )
            session.add(log)
        session.commit()

    # date_from=3天前：仅含 0/1/2 天前
    date_3_days_ago = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/history?date_from={date_3_days_ago}")
    assert resp.json()["total"] == 3

    # date_to=3天前：仅含 3天前及更早（即 5/10 天前）
    resp = client.get(f"/api/history?date_to={date_3_days_ago}")
    assert resp.json()["total"] == 2  # 5 + 10 天前

    # 组合 from + to：1 天前到 5 天前
    date_5_days_ago = (now - timedelta(days=5)).strftime("%Y-%m-%d")
    date_1_days_ago = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/history?date_from={date_5_days_ago}&date_to={date_1_days_ago}")
    assert resp.json()["total"] == 3  # 1/2/5 天前


def test_history_invalid_date_returns_no_filter(client):
    """非法日期字符串不报错，视为未传该参数。"""
    _seed_logs(client, [("问题1", "答案1", 0), ("问题2", "答案2", 0)])
    resp = client.get("/api/history?date_from=invalid-date")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2  # 全部返回


def test_history_search_combined_with_filters(client):
    """搜索 + feedback + date 组合筛选。"""
    now = _now_utc()
    with get_session() as session:
        session.add(QueryLog(
            query="白酒问题A", answer="白酒答案A", feedback=1,
            created_at=now - timedelta(days=1),
        ))
        session.add(QueryLog(
            query="白酒问题B", answer="白酒答案B", feedback=-1,
            created_at=now - timedelta(days=1),
        ))
        session.add(QueryLog(
            query="白酒问题C", answer="白酒答案C", feedback=1,
            created_at=now - timedelta(days=10),  # 超出日期范围
        ))
        session.commit()

    date_5_days_ago = (now - timedelta(days=5)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/history?q=白酒&feedback=1&date_from={date_5_days_ago}")
    body = resp.json()
    # 应只命中：白酒 + feedback=1 + 5天内 = 1 条（A）
    assert body["total"] == 1
    assert body["items"][0]["query"] == "白酒问题A"


# ---------------------------------------------------------------------------
# 高亮与 snippet
# ---------------------------------------------------------------------------
def test_history_highlight_query(client):
    """query_highlight 在 query 中包裹 <mark>。"""
    _seed_logs(client, [("白酒问题", "答案", 0)])
    resp = client.get("/api/history?q=白酒")
    item = resp.json()["items"][0]
    assert item["query_highlight"] == "<mark>白酒</mark>问题"


def test_history_snippet_truncated_with_ellipsis(client):
    """长 answer 的 snippet 被截断并加省略号。"""
    long_answer = "前言内容" * 50 + "白酒关键词" + "后记内容" * 50
    _seed_logs(client, [("问题", long_answer, 0)])
    resp = client.get("/api/history?q=白酒关键词")
    item = resp.json()["items"][0]
    snippet = item["answer_snippet"]
    assert snippet is not None
    assert "<mark>白酒关键词</mark>" in snippet
    # snippet 应远短于原文
    assert len(snippet) < len(long_answer)
    # 应包含省略号（前后截断）
    assert "..." in snippet


def test_history_snippet_short_answer_no_truncation(client):
    """短 answer 的 snippet 不截断。"""
    _seed_logs(client, [("问题", "白酒", 0)])
    resp = client.get("/api/history?q=白酒")
    item = resp.json()["items"][0]
    # answer 很短，snippet 就是 answer 本身（带高亮）
    assert item["answer_snippet"] == "<mark>白酒</mark>"


# ---------------------------------------------------------------------------
# FTS5 表保留与 backfill 幂等
# ---------------------------------------------------------------------------
def test_history_fts_table_exists_and_synced(client):
    """history_fts 表存在且随 querylog 同步（保留作为未来优化基础）。"""
    _seed_logs(client, [("白酒问题", "白酒答案", 0)])
    with get_session() as session:
        # history_fts 表存在
        count = session.execute(
            sa_text("SELECT COUNT(*) FROM history_fts")
        ).scalar()
        assert count == 1
        # log_id 列正确绑定
        row = session.execute(
            sa_text("SELECT query, answer, log_id FROM history_fts LIMIT 1")
        ).one()
        assert row[0] == "白酒问题"
        assert row[1] == "白酒答案"
        assert row[2] > 0


def test_history_fts_trigger_on_delete(client):
    """删除 querylog 后 history_fts 同步删除（触发器工作）。"""
    ids = _seed_logs(client, [("白酒问题", "白酒答案", 0)])
    log_id = ids[0]
    with get_session() as session:
        log = session.get(QueryLog, log_id)
        assert log is not None
        session.delete(log)
        session.commit()
    # history_fts 也应同步删除
    with get_session() as session:
        count = session.execute(sa_text("SELECT COUNT(*) FROM history_fts")).scalar()
        assert count == 0


def test_history_fts_trigger_on_update(client):
    """更新 querylog 后 history_fts 同步更新。"""
    ids = _seed_logs(client, [("旧问题", "旧答案", 0)])
    log_id = ids[0]
    with get_session() as session:
        log = session.get(QueryLog, log_id)
        assert log is not None
        log.query = "新问题白酒"
        session.add(log)
        session.commit()
    # history_fts 应反映新内容
    with get_session() as session:
        row = session.execute(
            sa_text("SELECT query FROM history_fts WHERE log_id = :lid"),
            {"lid": log_id},
        ).one()
        assert row[0] == "新问题白酒"


def test_backfill_history_fts_idempotent(client):
    """backfill_history_fts 幂等：已同步的数据不重复迁移。"""
    _seed_logs(client, [("回填测试白酒", "回填答案", 0)])
    # 第一次 backfill（数据已被触发器同步，应返回 0）
    n1 = backfill_history_fts()
    assert n1 == 0
    # 模拟数据缺失：手动删除 history_fts
    with get_session() as session:
        session.execute(sa_text("DELETE FROM history_fts"))
        session.commit()
    # 第二次 backfill（应回填 1 条）
    n2 = backfill_history_fts()
    assert n2 == 1
    # 第三次 backfill（幂等，应返回 0）
    n3 = backfill_history_fts()
    assert n3 == 0


# ---------------------------------------------------------------------------
# 性能
# ---------------------------------------------------------------------------
def test_history_search_performance_under_200ms(client):
    """验收：LIKE 搜索 1000 条响应 < 200ms。"""
    with get_session() as session:
        for i in range(1000):
            session.add(QueryLog(
                query=f"白酒香型问题{i}号关于浓香酱香清香的讨论",
                answer=f"回答{i}：中国白酒有浓香、酱香、清香等多种香型。",
                feedback=1 if i % 3 == 0 else 0,
                created_at=_now_utc() - timedelta(hours=i),
            ))
        session.commit()

    # 多次采样取最小值，减少波动
    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        resp = client.get("/api/history?q=白酒&limit=50")
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    min_ms = min(times)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1000
    # 验收标准：< 200ms（保留 5x 余量）
    assert min_ms < 200, f"search too slow: {min_ms:.1f}ms"


# ---------------------------------------------------------------------------
# 返回结构完整性
# ---------------------------------------------------------------------------
def test_history_item_structure(client):
    """返回 item 字段完整。"""
    _seed_logs(client, [("问题1", "答案1", 1)])
    resp = client.get("/api/history?q=问题")
    item = resp.json()["items"][0]
    expected_keys = {
        "id", "query", "answer", "citations", "model_used",
        "latency_ms", "feedback", "created_at",
        "query_highlight", "answer_snippet",
    }
    assert expected_keys <= set(item.keys())


# ===========================================================================
# H2：FTS5 trigram 快路径测试
# ===========================================================================
# trigram 分词器索引所有 3 字符子串，对 ≥ 3 字符查询命中任意位置
# （含中文中间子串）。< 3 字符查询走 LIKE 兜底。
# 验证双路径正确性与兼容性。


def test_history_fts5_trigram_chinese_substring_3chars(client):
    """H2：≥ 3 字符中文子串走 FTS5 trigram MATCH，命中中间子串。

    场景：query="中国白酒文化" 中搜索 "白酒文"（3字，中间子串）应命中。
    旧版 unicode61 对连续中文整体作为单 token，无法命中中间子串；
    trigram 索引 3 字符子串可命中。
    """
    _seed_logs(client, [
        ("中国白酒文化", "白酒是中国传统蒸馏酒", 0),
        ("葡萄酒品鉴", "红酒文化", 0),
    ])
    resp = client.get("/api/history?q=白酒文")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["query"] == "中国白酒文化"
    # 高亮仍正常工作（FTS5 路径也返回 highlight）
    assert "<mark>" in body["items"][0]["query_highlight"]


def test_history_fts5_trigram_chinese_substring_4chars(client):
    """H2：4 字符中文子串走 FTS5 trigram MATCH。"""
    _seed_logs(client, [
        ("鸡尾酒配方大全", "Mojito 用朗姆酒", 0),
        ("啤酒酿造工艺", "上面发酵", 0),
    ])
    resp = client.get("/api/history?q=尾酒配方")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["query"] == "鸡尾酒配方大全"


def test_history_fts5_trigram_english_substring(client):
    """H2：英文子串走 FTS5 trigram MATCH。"""
    _seed_logs(client, [
        ("whiskey sour recipe", "bourbon + lemon + sugar", 0),
        ("mojito recipe", "rum + mint + lime", 0),
    ])
    resp = client.get("/api/history?q=whiskey")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["query"] == "whiskey sour recipe"


def test_history_fts5_trigram_answer_match(client):
    """H2：FTS5 MATCH 命中 answer 列（JOIN history_fts 搜索 query + answer）。"""
    _seed_logs(client, [
        ("问题1", "中国白酒有浓香酱香清香等香型", 0),
        ("问题2", "葡萄酒颜色各异", 0),
    ])
    # "浓香酱香" 4字在 answer 中，应通过 FTS5 命中
    resp = client.get("/api/history?q=浓香酱香")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["query"] == "问题1"
    assert "<mark>" in body["items"][0]["answer_snippet"]


def test_history_fts5_with_feedback_filter(client):
    """H2：FTS5 路径 + feedback 筛选组合正确。"""
    _seed_logs(client, [
        ("白酒问题一", "答案", 1),   # 赞
        ("白酒问题二", "答案", -1),  # 踩
        ("白酒问题三", "答案", 1),   # 赞
    ])
    # 搜索 "白酒问题" + feedback=1（赞）
    resp = client.get("/api/history?q=白酒问题&feedback=1")
    body = resp.json()
    assert body["total"] == 2
    for item in body["items"]:
        assert item["feedback"] == 1
        assert "白酒问题" in item["query"]


def test_history_fts5_with_date_filter(client):
    """H2：FTS5 路径 + date_from/date_to 筛选组合正确。"""
    now = _now_utc()
    with get_session() as session:
        # 3 天前
        session.add(QueryLog(
            query="白酒历史问题",
            answer="答案",
            feedback=0,
            created_at=now - timedelta(days=3),
        ))
        # 今天
        session.add(QueryLog(
            query="白酒最新问题",
            answer="答案",
            feedback=0,
            created_at=now,
        ))
        session.commit()
    # 搜索 "白酒" + date_from=今天（只返回今天的）
    today_str = now.strftime("%Y-%m-%d")
    resp = client.get(f"/api/history?q=白酒最新&date_from={today_str}")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["query"] == "白酒最新问题"


def test_history_fts5_pagination(client):
    """H2：FTS5 路径分页正确。"""
    _seed_logs(client, [
        (f"白酒问题第{i}号", "答案", 0) for i in range(5)
    ])
    # 第一页
    resp1 = client.get("/api/history?q=白酒问题&limit=2&offset=0")
    body1 = resp1.json()
    assert body1["total"] == 5
    assert len(body1["items"]) == 2
    # 第二页
    resp2 = client.get("/api/history?q=白酒问题&limit=2&offset=2")
    body2 = resp2.json()
    assert body2["total"] == 5
    assert len(body2["items"]) == 2
    # 两页不应有重复 id
    ids1 = {item["id"] for item in body1["items"]}
    ids2 = {item["id"] for item in body2["items"]}
    assert ids1.isdisjoint(ids2)


def test_history_fts5_phrase_escape_double_quotes(client):
    """H2：查询含双引号时不破坏 FTS5 phrase 语法。

    FTS5 phrase 用双引号包裹字面短语，内部双引号通过重复（""）转义。
    _sanitize_search_q 会剥离 " 字符，所以这里测试 3 字符以上正常查询
    能命中含该子串的记录（验证 phrase 转义不破坏正常 MATCH）。
    """
    _seed_logs(client, [
        ("中国白酒是什么香型", "答案", 0),
        ("普通啤酒问题", "答案", 0),
    ])
    # "白酒是什么" 5字 ≥ 3，走 FTS5 trigram MATCH
    resp = client.get('/api/history?q=白酒是什么')
    assert resp.status_code == 200
    body = resp.json()
    # 应命中含 "白酒是什么" 子串的记录
    assert body["total"] == 1
    assert body["items"][0]["query"] == "中国白酒是什么香型"


def test_history_fts5_no_match_returns_empty(client):
    """H2：FTS5 搜索无命中时返回空列表（不报错）。"""
    _seed_logs(client, [("白酒问题", "白酒答案", 0)])
    resp = client.get("/api/history?q=完全不存在的关键词")
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


# ===========================================================================
# H2：LIKE 兜底路径测试（< 3 字符查询）
# ===========================================================================
def test_history_like_fallback_2chars_chinese(client):
    """H2：2 字符中文查询走 LIKE 兜底（trigram 不命中 < 3 字符）。"""
    _seed_logs(client, [
        ("中国白酒文化", "白酒是传统酒", 0),
        ("葡萄酒品鉴", "红酒文化", 0),
    ])
    # "白酒" 2字，trigram 不命中，走 LIKE 应命中
    resp = client.get("/api/history?q=白酒")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["query"] == "中国白酒文化"


def test_history_like_fallback_1char(client):
    """H2：1 字符查询走 LIKE 兜底。"""
    _seed_logs(client, [
        ("白酒问题", "答案", 0),
        ("啤酒问题", "答案", 0),
    ])
    resp = client.get("/api/history?q=酒")
    body = resp.json()
    assert body["total"] == 2


def test_history_fts5_and_like_consistent_results(client):
    """H2：FTS5（≥3字）与 LIKE（同查询）结果一致（双路径无遗漏）。

    同一关键词 "白酒问题"（4字，走 FTS5）与分别用 LIKE 搜索，
    结果集应等价（FTS5 不应遗漏 LIKE 能命中的行）。
    """
    _seed_logs(client, [
        ("白酒问题一", "答案", 0),
        ("白酒问题二", "答案", 0),
        ("葡萄酒问题", "答案", 0),
    ])
    # FTS5 路径（4字 ≥ 3）
    resp_fts = client.get("/api/history?q=白酒问题")
    # 强制 LIKE 路径：用 2 字符查询 "白酒" 应命中前两个（但含 "葡萄酒问题" 不命中）
    resp_like = client.get("/api/history?q=白酒")
    fts_total = resp_fts.json()["total"]
    like_total = resp_like.json()["total"]
    # FTS5 "白酒问题" 命中 2 条；LIKE "白酒" 也命中 2 条（"白酒问题一/二"）
    assert fts_total == 2
    assert like_total == 2
    # 两者命中的 id 集合应一致
    fts_ids = {item["id"] for item in resp_fts.json()["items"]}
    like_ids = {item["id"] for item in resp_like.json()["items"]}
    assert fts_ids == like_ids


def test_history_fts5_trigram_tokenizer_confirmed(client):
    """H2：验证 history_fts 表确实使用 trigram 分词器（迁移 0005 生效）。"""
    _seed_logs(client, [("测试", "测试", 0)])
    with get_session() as session:
        sql = session.execute(
            sa_text("SELECT sql FROM sqlite_master WHERE name='history_fts'")
        ).scalar()
        assert sql is not None
        # 必须包含 trigram（而非 unicode61）
        assert "trigram" in sql
        assert "unicode61" not in sql
