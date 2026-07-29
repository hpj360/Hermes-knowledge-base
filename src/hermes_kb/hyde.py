"""HyDE（Hypothetical Document Embeddings）策略（M2-02 可选）。

策略：
- LLM 可用且 hyde_enabled：调用 LLM 生成假设答案 → 用假设答案做向量检索
- LLM 不可用但 hyde_enabled：用启发式构造伪文档（query + 同义词 + 领域模板）
- 失败降级：返回原始 query，不阻塞检索

设计：
- 与 QueryRewriter 配合：先改写 query，再用 HyDE 生成假设文档做检索
- 启发式伪文档复用 query_rewriter 的同义词知识
- LLM 调用加超时保护，超时/异常回退启发式
"""

from __future__ import annotations

import logging

from hermes_kb.config import get_settings
from hermes_kb.llm import LLMClient

logger = logging.getLogger(__name__)

# HyDE LLM 超时（秒），避免拖慢检索
_HYDE_TIMEOUT_SEC = 8.0


_HYDE_SYSTEM_PROMPT = (
    "你是酒类知识百科生成器。根据用户问题，生成一段假设性的百科文档（100-200字），"
    "内容应包含可能出现在真实文档中的关键词和表述。"
)


# 启发式伪文档模板：酒类关键词 → 百科片段
_HEURISTIC_TEMPLATES = {
    "金酒": "金酒（Gin）是一种以杜松子为主要香料的烈酒。核心风味包括杜松子、松木、柑橘。起源于荷兰，后在英国发扬光大。",
    "威士忌": "威士忌（Whisky）是一种以谷物为原料的烈酒。主要原料包括大麦、玉米。苏格兰威士忌需在橡木桶中陈酿至少3年。",
    "葡萄酒": "葡萄酒（Wine）是以葡萄为原料发酵酿制的酒。按颜色分为红葡萄酒、白葡萄酒和桃红葡萄酒。",
    "白酒": "白酒是中国传统的蒸馏酒，以曲为糖化发酵剂。主要香型包括酱香、浓香、清香等。",
    "朗姆": "朗姆酒（Rum）是以甘蔗或糖蜜为原料的蒸馏酒。主要产地包括加勒比海地区。",
    "龙舌兰": "龙舌兰（Tequila）是墨西哥的国酒，以蓝色龙舌兰植物为原料。",
    "伏特加": "伏特加（Vodka）是一种无色无味的烈酒，以谷物或马铃薯为原料，经多次蒸馏过滤。",
    "白兰地": "白兰地（Brandy）是以水果为原料的蒸馏酒。干邑和雅文邑是著名的白兰地产区。",
    "味美思": "味美思（Vermouth）是一种加香葡萄酒，用苦艾草等植物香料浸泡。",
    "苦精": "苦精（Bitters）是高浓度的香料酊剂，由多种草本植物浸泡而成。安高天娜和佩肖德是经典品牌。",
    "清酒": "清酒（Sake）是日本传统的米酒，以米、米曲和水为原料发酵酿造。精米步合是重要指标。",
    "烧酒": "烧酒（Soju）是韩国的蒸馏酒，以大米、大麦或红薯为原料。酒精度一般在20%左右。",
}


def _heuristic_hyde(query: str) -> str:
    """构造伪文档：模拟一篇关于该 query 的百科文章片段。

    1. 检测 query 中包含的酒类关键词，用模板构造伪文档
    2. 如果没匹配到模板，用通用模板
    """
    if not query:
        return query
    # 1. 检测 query 中包含的酒类关键词，拼接种子模板
    matched: list[str] = []
    for keyword, template in _HEURISTIC_TEMPLATES.items():
        if keyword in query:
            matched.append(template)
    if matched:
        # 前置 query 保留语义，后接模板片段丰富关键词
        return f"{query}。{''.join(matched)}"
    # 2. 没匹配到模板，用通用模板
    return (
        f"{query}。这是一篇关于酒类知识的百科文章。"
        f"{query}涉及酒类的原料、工艺、风味和历史文化。"
    )


class HyDEGenerator:
    """HyDE 假设文档生成器。"""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()
        self.enabled = get_settings().hyde_enabled

    def generate(self, query: str) -> str:
        """生成假设文档。

        - LLM 可用且 hyde_enabled：调用 LLM 生成
        - LLM 不可用但 hyde_enabled：启发式构造
        - hyde_disabled：返回原 query
        """
        if not query or not query.strip():
            return query
        if not self.enabled:
            return query
        # LLM 不可用：用启发式构造伪文档（无外部依赖）
        if not get_settings().llm_available:
            return _heuristic_hyde(query)
        # LLM 可用：调用 LLM 生成（带超时保护）
        try:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self._llm_generate, query)
                try:
                    doc = future.result(timeout=_HYDE_TIMEOUT_SEC)
                except concurrent.futures.TimeoutError:
                    logger.warning(
                        "HyDE LLM 超时（%ss），回退启发式", _HYDE_TIMEOUT_SEC
                    )
                    return _heuristic_hyde(query)
            if doc and doc.strip():
                return doc.strip()
            logger.warning("HyDE LLM 返回空，回退启发式")
            return _heuristic_hyde(query)
        except Exception as e:  # noqa: BLE001 — 软降级，不阻塞主流程
            logger.warning("HyDE 生成异常: %s", e)
            return _heuristic_hyde(query)

    def _llm_generate(self, query: str) -> str:
        """实际调用 LLM 生成假设文档（同步阻塞）。"""
        resp = self.llm.chat([
            {"role": "system", "content": _HYDE_SYSTEM_PROMPT},
            {"role": "user", "content": f"用户问题：{query}\n假设文档："},
        ])
        return (resp.content or "").strip()
