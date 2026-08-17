"""鸡尾酒智能体编排（V6-Phase 4）。

将 Phase 3 的 5 个 function calling 工具编排为可交互的智能体：

- 意图识别 → 工具调用（function calling，最多 MAX_ROUNDS 轮）→ 综合作答
- 溯源输出：回答内嵌 ``[来源: {source} (authority={n})]`` 式引用
- 年龄门强制前置（未成年拒绝配方类回答；无酒精请求放行）
- 中文优先：系统提示 + 中文回答 + Wikidata 中文别名

无真实 LLM Key（mock 后端）时降级为确定性意图路由 + 工具执行，
保证端到端可用（测试验收覆盖该路径）。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from hermes_kb.agent_tools import TOOLS, get_tool
from hermes_kb.llm import LLMClient

log = logging.getLogger("hermes_kb.agent")

MAX_ROUNDS = 3

# 年龄门：未成年默认拒绝的回复（不调用任何配方工具）
_AGE_GATE_REFUSAL = (
    "很抱歉，根据平台年龄验证规则，未满 18 周岁的用户不能获取鸡尾酒配方、"
    "酒精饮料相关信息。如需了解无酒精饮品（mocktail）或调酒基础知识，请确认年龄后再咨询。"
)

_SYSTEM_PROMPT = (
    "你是「知酒」鸡尾酒智能体，一位专业、耐心的调酒师助手。"
    "你面向中文用户，必须用简体中文回答。\n"
    "你的能力：\n"
    "1. 根据需求查找鸡尾酒配方（search_recipes / get_recipe）；\n"
    "2. 根据用户手头材料推荐可制作的酒（match_by_ingredients）；\n"
    "3. 推荐材料替代品（find_substitute）；\n"
    "4. 讲解调酒技法、鸡尾酒历史与原料知识（get_knowledge）。\n"
    "规则：\n"
    "- 优先调用工具获取真实数据，不要凭空编造配方或数据；\n"
    "- 回答配方时列出材料、用量与步骤，并标注来源（如 [来源: iba_official (authority=5)]）；\n"
    "- 找不到精确匹配时给出最接近的检索结果，并明确说明；\n"
    "- 用户询问无酒精饮品时正常回答；涉及烈酒配方时提醒适量饮酒。\n"
)


@dataclass
class AgentTurn:
    """一次工具调用记录（供前端/审计展示）。"""

    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    call_id: str = ""


@dataclass
class AgentResult:
    """智能体回答结果。"""

    query: str
    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    turns: list[dict[str, Any]] = field(default_factory=list)
    model_used: str = "mock"
    rejected: bool = False
    low_confidence: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "citations": self.citations,
            "turns": self.turns,
            "model_used": self.model_used,
            "rejected": self.rejected,
            "low_confidence": self.low_confidence,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }


def _tool_schemas() -> list[dict[str, Any]]:
    """转为 OpenAI function calling 的 tools 参数格式。"""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in TOOLS
    ]


def _extract_citations(result: dict[str, Any]) -> list[dict[str, Any]]:
    """从工具结果中提取引用（result.citations 或 result.result.citations）。"""
    res = result.get("result")
    if isinstance(res, dict) and res.get("citations"):
        return res["citations"]
    if result.get("citations"):
        return result["citations"]
    return []


def _citation_mark(citation: dict[str, Any]) -> str:
    """把引用项转为 ``[来源: ... (authority=...)]`` 文本。"""
    title = citation.get("title") or citation.get("doc_id") or ""
    return f"[来源: {title}]"


class CocktailAgent:
    """鸡尾酒智能体：工具调用编排 + 年龄门 + 溯源。"""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()
        self._is_mock = self.llm.backend_name.startswith("Mock")

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def ask(
        self,
        query: str,
        history: list[dict[str, str]] | None = None,
        *,
        age_verified: bool = True,
    ) -> AgentResult:
        """同步问答（供单元测试与非流式端点使用）。"""
        q = (query or "").strip()
        if not q:
            return AgentResult(query=q, answer="请提供具体问题。")

        # 年龄门：未验证 → 拒绝（无酒精关键词可放行，见 _age_gate_pass）
        if not age_verified and not _is_non_alcoholic_request(q):
            return AgentResult(
                query=q,
                answer=_AGE_GATE_REFUSAL,
                model_used=self.llm.backend_name,
                rejected=True,
            )

        messages = self._build_messages(q, history)
        if self._is_mock:
            return self._rule_based_answer(q, messages)
        return self._llm_loop_answer(q, messages)

    # ------------------------------------------------------------------
    # SSE 流式：逐事件 yield（tool_call / token / done）
    # ------------------------------------------------------------------
    def ask_events(
        self,
        query: str,
        history: list[dict[str, str]] | None = None,
        *,
        age_verified: bool = True,
    ) -> Any:
        """生成 SSE 事件：``{"type": "tool_call"|"token"|"done"|"error"}``。"""
        q = (query or "").strip()
        if not q:
            yield {"type": "error", "message": "请提供具体问题。"}
            return

        if not age_verified and not _is_non_alcoholic_request(q):
            yield {
                "type": "token",
                "content": _AGE_GATE_REFUSAL,
            }
            yield {"type": "done", "rejected": True}
            return

        messages = self._build_messages(q, history)
        if self._is_mock:
            result = self._rule_based_answer(q, messages)
            for token in _chunk_text(result.answer):
                yield {"type": "token", "content": token}
            yield {"type": "done", **result.to_dict()}
            return

        # 真实 LLM：先跑工具循环（同步），再逐段流式输出最终回答
        result = self._llm_loop_answer(q, messages)
        for turn in result.turns:
            yield {"type": "tool_call", **turn}
        for token in _chunk_text(result.answer):
            yield {"type": "token", "content": token}
        yield {"type": "done", **result.to_dict()}

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _build_messages(
        self, query: str, history: list[dict[str, str]] | None
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
        for item in history or []:
            role = item.get("role")
            content = item.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": str(content)})
        messages.append({"role": "user", "content": query})
        return messages

    def _llm_loop_answer(self, query: str, messages: list[dict[str, str]]) -> AgentResult:
        """真实 LLM function calling 循环。"""
        turns: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        prompt_tokens = 0
        completion_tokens = 0
        answer = ""

        for _ in range(MAX_ROUNDS):
            resp = self.llm.chat(messages, tools=_tool_schemas(), tool_choice="auto")
            prompt_tokens += resp.prompt_tokens
            completion_tokens += resp.completion_tokens
            tool_calls = resp.tool_calls

            if not tool_calls:
                answer = resp.content or ""
                break

            # 执行本轮所有工具调用
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": None}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except (ValueError, TypeError):
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                result = self._execute_tool(name, args)
                turns.append(
                    {
                        "name": name,
                        "arguments": args,
                        "result": result,
                        "call_id": tc.get("id", ""),
                    }
                )
                citations.extend(_extract_citations(result))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        else:
            # 超过最大轮数：基于最后工具结果给出摘要
            answer = self._compose_from_turns(query, turns)

        return AgentResult(
            query=query,
            answer=answer,
            citations=_dedup_citations(citations),
            turns=turns,
            model_used=self.llm.backend_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            low_confidence=not turns and not answer,
        )

    def _execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """执行工具，失败返回错误消息（不抛出）。"""
        tool = get_tool(name)
        if tool is None:
            return {"error": f"未知工具: {name}"}
        try:
            return tool.execute(**args)  # type: ignore[misc]
        except Exception as exc:  # noqa: BLE001 — 工具异常转错误消息
            log.warning("tool %s failed: %s", name, exc)
            return {"error": f"{name} 执行失败: {exc}"}

    # ------------------------------------------------------------------
    # Mock 降级：确定性意图路由 + 工具执行
    # ------------------------------------------------------------------
    def _rule_based_answer(self, query: str, messages: list[dict[str, str]]) -> AgentResult:
        """无 LLM Key 时的确定性回答：识别意图 → 执行工具 → 拼装答案。"""
        turns: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []

        intent, payload = _detect_intent(query)
        if intent == "recipe_detail":
            result = self._execute_tool("get_recipe", {"title": payload})
            turns.append({"name": "get_recipe", "arguments": {"title": payload}, "result": result})
            answer = _render_recipe_answer(result)
            citations.extend(_extract_citations(result))
        elif intent == "ingredient_match":
            ing_list = _parse_ingredient_list(payload)
            args = {"ingredients": ing_list}
            result = self._execute_tool("match_by_ingredients", args)
            turns.append({"name": "match_by_ingredients", "arguments": args, "result": result})
            answer = _render_match_answer(result, ing_list)
            citations.extend(_extract_citations(result))
        elif intent == "substitute":
            ing = payload or query
            result = self._execute_tool("find_substitute", {"ingredient": ing})
            turns.append({"name": "find_substitute", "arguments": {"ingredient": ing}, "result": result})
            answer = _render_substitute_answer(result, ing)
            citations.extend(_extract_citations(result))
        elif intent == "search":
            args = {"query": payload}
            result = self._execute_tool("search_recipes", args)
            turns.append({"name": "search_recipes", "arguments": args, "result": result})
            answer = _render_search_answer(result)
            citations.extend(_extract_citations(result))
        else:
            # 自由问答 / 技法 / 历史 → 知识检索
            result = self._execute_tool("get_knowledge", {"query": query, "top_k": 5})
            turns.append({"name": "get_knowledge", "arguments": {"query": query}, "result": result})
            answer = _render_knowledge_answer(result)
            citations.extend(_extract_citations(result))

        return AgentResult(
            query=query,
            answer=answer,
            citations=_dedup_citations(citations),
            turns=turns,
            model_used=self.llm.backend_name,
            low_confidence=bool(result.get("error")),
        )

    def _compose_from_turns(
        self, query: str, turns: list[dict[str, Any]]
    ) -> str:
        """超过最大轮数后，基于工具结果拼装回答。"""
        if not turns:
            return "抱歉，未能获取到相关信息，请换个问法试试。"
        last = turns[-1]
        result = last.get("result") or {}
        res = result.get("result")
        if isinstance(res, dict):
            return json.dumps(res, ensure_ascii=False, indent=2)
        return str(result)


# ---------------------------------------------------------------------------
# 意图识别（规则）
# ---------------------------------------------------------------------------
# 配方详情：问某款具体酒的做法/配方
_RECIPE_DETAIL_RE = re.compile(
    r"(?:怎么做|如何做|配方|做法|怎么调|如何调|步骤|recipe)\s*(?:的)?\s*(.{1,30})?$",
    re.IGNORECASE,
)
# 材料匹配：我有/手头有/用这些材料
_INGREDIENT_MATCH_RE = re.compile(r"(?:我有|手头有|家里有|用这些|以下材料|用.{0,8}(?:做|调|推荐))")
# 替代品：替代/替换/没有
_SUBSTITUTE_RE = re.compile(r"(?:替代|替换|没有|缺|换掉|substitute)", re.IGNORECASE)
# 配方搜索：找/推荐/有哪些 + 酒
_SEARCH_RE = re.compile(r"(?:推荐|找|有哪些|搜索|帮我找|好喝的|适合)")


def _detect_intent(query: str) -> tuple[str, str]:
    """规则化意图识别（Mock 路径用）。返回 (intent, payload)。"""
    q = (query or "").strip()
    # 1. 替代品优先（明确的关键词）
    if _SUBSTITUTE_RE.search(q) and _looks_like_ingredient(q):
        ing = _extract_ingredient(q)
        return "substitute", ing
    # 2. 材料匹配
    if _INGREDIENT_MATCH_RE.search(q):
        return "ingredient_match", q
    # 3. 配方详情（含"配方/做法/怎么调"且无泛指搜索词）
    if _RECIPE_DETAIL_RE.search(q) and not _SEARCH_RE.search(q):
        title = _extract_recipe_title(q)
        return "recipe_detail", title
    # 4. 配方搜索
    if _SEARCH_RE.search(q) or "酒" in q:
        return "search", q
    # 5. 知识问答
    return "knowledge", q


def _looks_like_ingredient(q: str) -> bool:
    """粗判是否为材料替代问题（含材料名）。"""
    return len(q) <= 24


def _extract_ingredient(q: str) -> str:
    """从替代句提取材料名（去"替代/替换/没有"等词）。"""
    for word in ("用什么替代", "替代品", "可以替代", "替代", "替换", "没有"):
        if word in q:
            return q.replace(word, "").strip("的用怎么？?。 ")
    return q.strip()


def _extract_recipe_title(q: str) -> str:
    """从"XX怎么做/配方"提取配方名。"""
    cleaned = _RECIPE_DETAIL_RE.sub("", q)
    for word in ("配方", "做法", "怎么做", "如何做", "怎么调", "如何调", "步骤"):
        cleaned = cleaned.replace(word, "")
    return cleaned.strip("的：:怎么？?。 ")


def _parse_ingredient_list(payload: str) -> list[str]:
    """从材料匹配句提取材料列表（按顿号/逗号/空格分割，去"我有"等前缀）。"""
    text = payload
    for prefix in ("我有", "手头有", "家里有", "用这些材料", "用这些", "以下材料"):
        text = text.replace(prefix, "")
    parts = re.split(r"[，,、;；\s]+", text)
    parts = [p for p in parts if p and not p.startswith(("做", "调", "推荐", "酒"))]
    return parts[:20]


def _is_non_alcoholic_request(query: str) -> bool:
    """无酒精请求（年龄门放行）：mocktail/无酒精/不含酒精/零度。"""
    return any(
        kw in query.lower()
        for kw in ("无酒精", "不含酒精", "零度", "mocktail", "无醇", "不含乙醇")
    )


# ---------------------------------------------------------------------------
# 回答渲染（Mock 路径）
# ---------------------------------------------------------------------------
def _render_recipe_answer(result: dict[str, Any]) -> str:
    if result.get("error"):
        return f"查询失败：{result['error']}"
    res = result.get("result")
    if res is None:
        return "未找到该配方的详细信息，可尝试其他名称或使用搜索功能。"
    title = res.get("title", "")
    lines = [f"【{title}】"]
    if res.get("base_spirit"):
        lines.append(f"基酒：{res['base_spirit']}")
    if res.get("abv"):
        lines.append(f"估算酒精度：{res['abv'] * 100:.1f}%")
    if res.get("technique"):
        lines.append(f"技法：{res['technique']}")
    if res.get("glassware"):
        lines.append(f"载杯：{res['glassware']}")
    ingredients = res.get("ingredients_json") or []
    if ingredients:
        lines.append("材料：")
        for ing in ingredients:
            name = ing.get("name", "")
            measure = ing.get("measure", "")
            lines.append(f"- {name} {measure}".rstrip())
    content = (res.get("content") or "").strip()
    if content:
        lines.append("\n做法：")
        lines.append(content)
    if res.get("source"):
        authority = res.get("source_authority") or "?"
        lines.append(f"\n{_citation_mark({'title': res['source']})} (authority={authority})")
    return "\n".join(lines)


def _render_match_answer(result: dict[str, Any], ing_list: list[str]) -> str:
    if result.get("error"):
        return f"匹配失败：{result['error']}"
    res = result.get("result") or {}
    full = res.get("full_match") or []
    partial = res.get("partial_match") or []
    if not full and not partial:
        return f"根据材料 {ing_list} 未找到可制作的配方，可尝试用替代品或补充材料。"
    lines = [f"根据你手头的材料（{', '.join(ing_list)}），可以尝试："]
    for item in full[:8]:
        lines.append(f"- {item['title']}（材料齐全）")
    for item in partial[:8]:
        missing = item.get("missing_ingredients") or []
        lines.append(f"- {item['title']}（缺 {', '.join(missing)}）")
    return "\n".join(lines)


def _render_substitute_answer(result: dict[str, Any], ing: str) -> str:
    if result.get("error"):
        return f"替代品查询失败：{result['error']}"
    res = result.get("result") or {}
    subs = res.get("substitutes") or []
    if not subs:
        return f"未找到「{ing}」的替代材料。"
    lines = [f"「{ing}」可以尝试以下替代品："]
    for s in subs:
        note = s.get("note", "")
        lines.append(f"- {s.get('substitute')}（{note}）" if note else f"- {s.get('substitute')}")
    return "\n".join(lines)


def _render_search_answer(result: dict[str, Any]) -> str:
    if result.get("error"):
        return f"搜索失败：{result['error']}"
    res = result.get("result") or {}
    results = res.get("results") or []
    if not results:
        return "未找到相关配方，可调整关键词或换个角度提问。"
    lines = [f"为你找到 {res.get('count', len(results))} 款配方："]
    for r in results[:10]:
        meta = []
        if r.get("base_spirit"):
            meta.append(r["base_spirit"])
        if r.get("abv"):
            meta.append(f"{r['abv'] * 100:.0f}%")
        suffix = f"（{'，'.join(meta)}）" if meta else ""
        lines.append(f"- {r['title']}{suffix}")
    return "\n".join(lines)


def _render_knowledge_answer(result: dict[str, Any]) -> str:
    if result.get("error"):
        return f"知识查询失败：{result['error']}"
    res = result.get("result") or {}
    text = res.get("text") or "（暂无相关内容）"
    citations = res.get("citations") or []
    parts = [text]
    if citations:
        parts.append("\n\n参考来源：")
        for c in citations[:5]:
            parts.append(f"- {_citation_mark(c)}")
    return "\n".join(parts)


def _chunk_text(text: str, size: int = 24) -> list[str]:
    """把回答切成小块，模拟流式输出。"""
    if not text:
        return [""]
    chunks: list[str] = []
    for i in range(0, len(text), size):
        chunks.append(text[i : i + size])
    return chunks


def _dedup_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 doc_id 去重引用。"""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for c in citations:
        key = c.get("doc_id") or c.get("title") or ""
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        result.append(c)
    return result


__all__ = ["AgentResult", "AgentTurn", "CocktailAgent", "detect_intent"]


def detect_intent(query: str) -> tuple[str, str]:
    """公开意图识别入口（内部规则实现见 ``_detect_intent``）。"""
    return _detect_intent(query)
