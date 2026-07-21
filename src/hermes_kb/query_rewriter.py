"""查询改写（Query Rewriting，M2-02）。

策略：
- LLM 可用时：调用 LLM 把口语化 query 改写为检索友好的关键词组合
- LLM 不可用（mock）：跳过，返回原 query
- 失败降级：返回原 query，不阻塞检索

设计：
- 同步调用（在 retrieve 之前），独立于 RAG 生成阶段
- 改写结果作为检索 query，原 query 仍传给 LLM 生成（保持语义）
- 不缓存（每条 query 独立改写，避免歧义）
- P1 修复：LLM 调用加超时保护，超时/异常回退启发式
"""

from __future__ import annotations

import logging
import re
from typing import Any

from hermes_kb.config import get_settings
from hermes_kb.llm import LLMClient

logger = logging.getLogger(__name__)

# 改写 LLM 超时（秒），避免拖慢检索
_REWRITE_TIMEOUT_SEC = 5.0


_REWRITE_SYSTEM_PROMPT = (
    "你是检索查询改写器。任务：把用户口语化问题改写为检索友好的关键词组合。\n\n"
    "规则：\n"
    "1. 输出 3-6 个关键词，用空格分隔\n"
    "2. 保留核心实体（酒名、产地、工艺、原料）\n"
    "3. 去除语气词（的、是、呢、啊）\n"
    "4. 补充同义词（如「金酒」补「杜松子」）\n"
    "5. 不输出解释，只输出关键词\n\n"
    "示例：\n"
    "输入：金酒啥味\n"
    "输出：金酒 杜松子 风味 香料 松木\n"
    "输入：茅台的工艺\n"
    "输出：茅台 酱香 工艺 制曲 下沙 蒸煮\n"
)


# 简单启发式（mock 模式或 LLM 失败时用）
def _heuristic_rewrite(query: str) -> str:
    """启发式改写：去语气词 + 补酒类常见同义词。"""
    if not query:
        return query
    # 去常见语气词
    q = re.sub(r"[的了吗呢啊吧呀]+", "", query)
    # 同义词补充（命中即在末尾追加）
    syn_map = {
        "金酒": "杜松子",
        "威士忌": "谷物 橡木桶",
        "葡萄酒": "葡萄 发酵",
        "白酒": "中国 曲 发酵",
        "朗姆": "甘蔗 糖蜜",
        "龙舌兰": "Tequila 蓝色",
        "茅台": "酱香",
        "五粮液": "浓香",
        "汾酒": "清香",
    }
    extras: list[str] = []
    for k, v in syn_map.items():
        if k in q and v not in q:
            extras.append(v)
    if extras:
        return f"{q} {' '.join(extras)}"
    return q


class QueryRewriter:
    """查询改写器。"""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()
        self.enabled = get_settings().llm_available and get_settings().query_rewrite_enabled

    def rewrite(self, query: str) -> str:
        """改写 query。

        - LLM 可用且启用：调用 LLM 改写（带超时保护）
        - 否则：启发式改写（无外部依赖）
        - 任何异常/超时：回退启发式，不阻塞检索
        """
        if not query or not query.strip():
            return query
        if not self.enabled:
            # LLM 不可用：用启发式（不调用 LLM，零成本）
            return _heuristic_rewrite(query)
        try:
            # P1 修复：用线程池 + 超时保护，避免 LLM 卡死拖慢检索
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self._llm_rewrite, query)
                try:
                    rewritten = future.result(timeout=_REWRITE_TIMEOUT_SEC)
                except concurrent.futures.TimeoutError:
                    logger.warning("查询改写 LLM 超时（%ss），回退启发式", _REWRITE_TIMEOUT_SEC)
                    return _heuristic_rewrite(query)
            if rewritten and len(rewritten) <= max(50, len(query) * 5):
                return rewritten
            logger.warning("查询改写结果长度异常，回退原 query")
            return query
        except Exception as e:
            logger.warning("查询改写异常: %s", e)
            return _heuristic_rewrite(query)

    def _llm_rewrite(self, query: str) -> str:
        """实际调用 LLM 改写（同步阻塞）。"""
        resp = self.llm.chat([
            {"role": "system", "content": _REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ])
        return (resp.content or "").strip()
