"""鸡尾酒智能体函数调用工具（OpenAI function calling 格式）。

为 LLM agent 提供 5 个可调用工具，包装既有领域模块：

- search_recipes        → retrieval.HybridRetriever + recipe_filter.filter_recipes
- get_recipe            → models.Document 查询 + recipe_variants 变体回退 + HybridRetriever
- match_by_ingredients  → recipe_filter.find_recipes_by_ingredients
- find_substitute       → substitutes.get_substitutes
- get_knowledge         → rag.RAGEngine.answer（回退原始检索）

每个工具由 ``ToolDef`` 描述：name / description / parameters(JSON Schema) / execute。
``execute`` 接收关键字参数，返回 ``{"result": ..., "citations": ...}`` 或 ``{"error": ...}``。
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func
from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.ingredients import canonicalize
from hermes_kb.models import Document
from hermes_kb.recipe_filter import filter_recipes, find_recipes_by_ingredients
from hermes_kb.recipe_variants import get_base_recipe, get_variants
from hermes_kb.retrieval import HybridRetriever
from hermes_kb.substitutes import get_substitutes, get_substitutes_preset


@dataclass
class ToolDef:
    """函数调用工具定义。

    Attributes:
        name: 工具唯一名称（LLM 调用标识）。
        description: 工具用途描述（帮助 LLM 判断何时调用）。
        parameters: OpenAI function calling 的 JSON Schema（type=object + properties）。
        execute: 可调用对象，接收关键字参数，返回 dict。
    """

    name: str
    description: str
    parameters: dict[str, Any]
    execute: Callable[..., dict[str, Any]]


# ---------------------------------------------------------------------------
# 惰性单例（避免每次调用重复初始化 EmbeddingService / RAGEngine）
# ---------------------------------------------------------------------------
_retriever: HybridRetriever | None = None
_rag_engine: Any = None


def _get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


def _get_rag_engine() -> Any:
    global _rag_engine
    if _rag_engine is None:
        from hermes_kb.rag import RAGEngine  # 延迟导入，避免模块加载时拉起重依赖

        _rag_engine = RAGEngine()
    return _rag_engine


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------
def _parse_ingredients(ingredients_json: str) -> list[Any]:
    """安全解析 ingredients_json 字段（非法 JSON 返回空列表）。"""
    if not ingredients_json:
        return []
    try:
        data = json.loads(ingredients_json)
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def _search_item(doc: Document) -> dict[str, Any]:
    """搜索结果的精简字段。"""
    return {
        "title": doc.title,
        "doc_id": doc.doc_id,
        "source": doc.source,
        "technique": doc.technique,
        "glassware": doc.glassware,
        "base_spirit": doc.base_spirit,
        "abv": doc.abv,
        "difficulty": doc.difficulty,
    }


def _load_search_item(doc_id: str) -> dict[str, Any] | None:
    """按 doc_id 加载精简字段（hybrid 命中但不在过滤池内的文档）。"""
    try:
        with get_session() as session:
            doc = session.get(Document, doc_id)
            return _search_item(doc) if doc else None
    except Exception:  # noqa: BLE001 — 单条加载失败不阻塞整体
        return None


def _batch_search_items(doc_ids: list[str]) -> list[dict[str, Any]]:
    """批量加载精简字段并保持传入顺序（消除 N+1）。"""
    if not doc_ids:
        return []
    with get_session() as session:
        docs = session.exec(
            select(Document).where(Document.doc_id.in_(doc_ids))
        ).all()
    doc_map = {d.doc_id: d for d in docs}
    return [_search_item(doc_map[i]) for i in doc_ids if i in doc_map]


def _query_structured_recipes(
    base_spirit: str | None,
    technique: str | None,
    glassware: str | None,
    non_alcoholic: bool,
) -> list[dict[str, Any]]:
    """结构化过滤查询配方。

    - 仅 technique/glassware 过滤时复用 ``filter_recipes``（该函数支持这两个字段）
    - 涉及 base_spirit / non_alcoholic 时直接查 Document
      （``filter_recipes`` 不支持 base_spirit；non_alcoholic 用 base_spirit=="other" 启发式）
    """
    if not base_spirit and not non_alcoholic:
        filtered = filter_recipes(
            technique=technique or None,
            glassware=glassware or None,
            limit=100,
        )
        return _batch_search_items([d["doc_id"] for d in filtered])

    with get_session() as session:
        stmt = select(Document).where(Document.category == "recipe")
        if technique:
            stmt = stmt.where(Document.technique == technique)
        if glassware:
            stmt = stmt.where(Document.glassware == glassware)
        if non_alcoholic:
            # 无酒精启发式：base_spirit == "other"
            stmt = stmt.where(Document.base_spirit == "other")
        elif base_spirit:
            stmt = stmt.where(Document.base_spirit == base_spirit)
        docs = session.exec(stmt.limit(100)).all()
        return [_search_item(d) for d in docs]


def _serialize_recipe(doc: Document) -> dict[str, Any]:
    """配方的完整字段序列化。"""
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "content": doc.content,
        "source": doc.source,
        "source_id": doc.source_id,
        "technique": doc.technique,
        "glassware": doc.glassware,
        "iba_category": doc.iba_category,
        "flavor_profile": doc.flavor_profile,
        "difficulty": doc.difficulty,
        "abv_bucket": doc.abv_bucket,
        "base_spirit": doc.base_spirit,
        "abv": doc.abv,
        "ingredients_json": _parse_ingredients(doc.ingredients_json),
        "image_url": doc.image_url,
        "source_url": doc.source_url,
        "source_authority": doc.source_authority,
    }


def _find_recipe_docs(title: str) -> list[Document]:
    """按标题查找配方文档（优先精确匹配，回退 LIKE 模糊匹配，均大小写不敏感）。"""
    lowered = title.lower()
    with get_session() as session:
        exact = session.exec(
            select(Document)
            .where(Document.category == "recipe")
            .where(func.lower(Document.title) == lowered)
            .limit(5)
        ).all()
        if exact:
            return list(exact)
        partial = session.exec(
            select(Document)
            .where(Document.category == "recipe")
            .where(Document.title.ilike(f"%{title}%"))
            .limit(10)
        ).all()
        return list(partial)


def _resolve_variant_doc(doc: Document) -> Document:
    """若文档是变体则解析到原配方，否则原样返回。"""
    try:
        base = get_base_recipe(doc.doc_id)
    except Exception:  # noqa: BLE001 — 变体查询失败视为普通配方
        base = None
    if base and base.get("base_doc_id"):
        with get_session() as session:
            base_doc = session.get(Document, base["base_doc_id"])
            if base_doc:
                return base_doc
    return doc


def _search_recipe_doc(title: str) -> Document | None:
    """标题在知识库中无直接命中时，用 HybridRetriever 检索候选配方文档。"""
    try:
        hits = _get_retriever().retrieve(title, top_k=3)
    except Exception:  # noqa: BLE001 — 检索失败返回 None
        return None
    for hit in hits:
        with get_session() as session:
            doc = session.get(Document, hit.doc_id)
        if doc and doc.category == "recipe":
            return doc
    return None


def _list_variants(doc_id: str) -> list[dict[str, Any]]:
    """安全获取配方的变体列表。"""
    try:
        return get_variants(doc_id)
    except Exception:  # noqa: BLE001 — 变体查询失败返回空列表
        return []


# ---------------------------------------------------------------------------
# 1. search_recipes
# ---------------------------------------------------------------------------
def search_recipes(
    query: str = "",
    base_spirit: str | None = None,
    technique: str | None = None,
    glassware: str | None = None,
    non_alcoholic: bool = False,
    limit: int = 10,
) -> dict[str, Any]:
    """按文本查询 + 结构化过滤搜索配方。"""
    try:
        limit = max(1, min(int(limit or 10), 50))

        # 1) 文本查询：HybridRetriever 混合检索（doc_id -> score）
        hit_scores: dict[str, float] = {}
        if query and str(query).strip():
            hits = _get_retriever().retrieve(str(query), top_k=max(limit * 3, 20))
            hit_scores = {h.doc_id: h.score for h in hits}

        # 2) 结构化过滤池（base_spirit/technique/glassware + 无酒精启发式）
        pool = _query_structured_recipes(
            base_spirit=base_spirit,
            technique=technique,
            glassware=glassware,
            non_alcoholic=bool(non_alcoholic),
        )
        pool_map = {item["doc_id"]: item for item in pool}

        # 3) 合并排序：query 命中优先（score 降序），其余按过滤池顺序补齐
        ranked: list[dict[str, Any]] = []
        seen: set[str] = set()
        for doc_id in sorted(hit_scores, key=hit_scores.get, reverse=True):
            item = pool_map.get(doc_id) or _load_search_item(doc_id)
            if item is None:
                continue
            item = dict(item)
            item["score"] = hit_scores.get(doc_id)
            ranked.append(item)
            seen.add(doc_id)
        for item in pool:
            if item["doc_id"] not in seen:
                ranked.append(item)

        results = ranked[:limit]
        return {
            "result": {
                "results": results,
                "count": len(results),
                "query": query or None,
            }
        }
    except Exception as exc:  # noqa: BLE001 — 工具内异常转错误消息
        return {"error": f"search_recipes 执行失败: {exc}"}


# ---------------------------------------------------------------------------
# 2. get_recipe
# ---------------------------------------------------------------------------
def get_recipe(title: str) -> dict[str, Any]:
    """按标题获取配方完整详情（支持变体回退与模糊检索）。"""
    try:
        if not title or not str(title).strip():
            return {"error": "get_recipe 需要提供 title 参数"}
        title = str(title).strip()

        doc: Document | None = None
        matched = _find_recipe_docs(title)
        if matched:
            doc = _resolve_variant_doc(matched[0])
        else:
            # 回退 1：recipe_variants 变体关联中查找
            try:
                base = get_base_recipe_by_title(title)
            except Exception:  # noqa: BLE001
                base = None
            if base:
                doc = base
            else:
                # 回退 2：HybridRetriever 按标题检索
                doc = _search_recipe_doc(title)

        if doc is None:
            return {"result": None, "message": f"未找到配方: {title}"}

        data = _serialize_recipe(doc)
        variants = _list_variants(doc.doc_id)
        if variants:
            data["variants"] = variants
        return {"result": data}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"get_recipe 执行失败: {exc}"}


def get_base_recipe_by_title(title: str) -> Document | None:
    """通过变体关联反查：标题匹配的文档若是变体，返回其原配方。"""
    for cand in _find_recipe_docs(title):
        try:
            base = get_base_recipe(cand.doc_id)
        except Exception:  # noqa: BLE001
            base = None
        if base and base.get("base_doc_id"):
            with get_session() as session:
                base_doc = session.get(Document, base["base_doc_id"])
            if base_doc:
                return base_doc
    return None


# ---------------------------------------------------------------------------
# 3. match_by_ingredients
# ---------------------------------------------------------------------------
def match_by_ingredients(
    ingredients: list[str],
    min_match: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """按用户手头材料匹配配方，返回 full_match / partial_match。"""
    try:
        if not ingredients:
            return {"error": "match_by_ingredients 需要提供 ingredients 列表"}
        ing_list = [str(i).strip() for i in ingredients if str(i).strip()]
        if not ing_list:
            return {"error": "match_by_ingredients 的 ingredients 不能为空"}

        result = find_recipes_by_ingredients(
            ing_list,
            min_match=max(1, int(min_match or 1)),
            limit=max(1, int(limit or 20)),
        )
        return {
            "result": {
                "full_match": result.get("full_match", []),
                "partial_match": result.get("partial_match", []),
            }
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"match_by_ingredients 执行失败: {exc}"}


# ---------------------------------------------------------------------------
# 4. find_substitute
# ---------------------------------------------------------------------------
def find_substitute(ingredient: str) -> dict[str, Any]:
    """查找某材料的替代品。"""
    try:
        if not ingredient or not str(ingredient).strip():
            return {"error": "find_substitute 需要提供 ingredient 参数"}
        name = str(ingredient).strip()
        canonical = canonicalize(name) or name

        subs = get_substitutes(canonical)
        preset = set(get_substitutes_preset(canonical))
        items = [
            {
                "substitute": s,
                "note": "预置替代" if s in preset else "用户自定义替代",
            }
            for s in subs
        ]
        if not items:
            return {
                "result": {
                    "ingredient": name,
                    "canonical": canonical,
                    "substitutes": [],
                    "message": f"未找到 {name} 的替代材料",
                }
            }
        return {
            "result": {
                "ingredient": name,
                "canonical": canonical,
                "substitutes": items,
            }
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"find_substitute 执行失败: {exc}"}


# ---------------------------------------------------------------------------
# 5. get_knowledge
# ---------------------------------------------------------------------------
def get_knowledge(query: str, top_k: int = 5) -> dict[str, Any]:
    """通用鸡尾酒知识问答（技法/历史/材料等）。"""
    try:
        if not query or not str(query).strip():
            return {"error": "get_knowledge 需要提供 query 参数"}
        q = str(query).strip()
        top_k = max(1, min(int(top_k or 5), 20))

        answer = _get_rag_engine().answer(q, top_k=top_k)
        if getattr(answer, "rejected", False):
            return {
                "result": {
                    "text": answer.answer,
                    "rejected": True,
                    "citations": [],
                }
            }
        citations = [c.to_dict() for c in getattr(answer, "citations", [])]
        return {"result": {"text": answer.answer, "citations": citations}}
    except Exception:  # noqa: BLE001 — RAG/LLM 失败时回退到原始检索内容
        try:
            hits = _get_retriever().retrieve(str(query), top_k=top_k)
            items = [
                {
                    "doc_id": h.doc_id,
                    "title": h.title,
                    "text": h.text,
                    "score": h.score,
                }
                for h in hits
            ]
            text = "\n\n".join(it["text"] for it in items) if items else "（无检索结果）"
            return {"result": {"text": text, "citations": items}}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"get_knowledge 执行失败: {exc}"}


# ---------------------------------------------------------------------------
# 工具注册表
# ---------------------------------------------------------------------------
TOOLS: list[ToolDef] = [
    ToolDef(
        name="search_recipes",
        description=(
            "按文本查询和结构化条件搜索鸡尾酒配方。query 可填写配方名/材料/风味等关键词；"
            "可选 base_spirit（gin/vodka/rum/whiskey/tequila/brandy/other）、"
            "technique（shake/stir/build 等）、glassware（载杯类型）过滤，"
            "non_alcoholic=True 时仅返回无酒精配方。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "文本查询词（配方名/材料/风味等），可为空字符串。",
                },
                "base_spirit": {
                    "type": "string",
                    "description": "基酒过滤：gin/vodka/rum/whiskey/tequila/brandy/other。",
                },
                "technique": {
                    "type": "string",
                    "description": "调酒技法过滤：shake/stir/build/layer/muddle/blend。",
                },
                "glassware": {
                    "type": "string",
                    "description": "载杯类型过滤，如 马天尼杯/古典杯/高球杯。",
                },
                "non_alcoholic": {
                    "type": "boolean",
                    "description": "True 时仅返回无酒精配方（base_spirit=other 启发式）。",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量，默认 10，最大 50。",
                },
            },
            "required": [],
        },
        execute=search_recipes,
    ),
    ToolDef(
        name="get_recipe",
        description=(
            "按标题获取鸡尾酒配方的完整详情（材料、步骤、基酒、酒精度、风味等）。"
            "标题精确/模糊匹配，若为变体自动解析到原配方，找不到时用检索兜底。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "配方名称，如 马天尼 / Margarita。",
                },
            },
            "required": ["title"],
        },
        execute=get_recipe,
    ),
    ToolDef(
        name="match_by_ingredients",
        description=(
            "根据用户手头已有的材料列表匹配可制作的鸡尾酒配方，"
            "返回 full_match（材料齐全）与 partial_match（缺 1-2 种材料）两组结果。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "ingredients": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "用户手头可用的材料名称列表，如 [\"金酒\", \"味美思\"]。",
                },
                "min_match": {
                    "type": "integer",
                    "description": "partial_match 的最小命中材料数阈值，默认 1。",
                },
                "limit": {
                    "type": "integer",
                    "description": "每组最大返回数量，默认 20。",
                },
            },
            "required": ["ingredients"],
        },
        execute=match_by_ingredients,
    ),
    ToolDef(
        name="find_substitute",
        description=(
            "查找某材料的替代品。例如用户没有某款利口酒时，返回可替换的材料列表及说明。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "ingredient": {
                    "type": "string",
                    "description": "要查找替代品的材料名称，如 君度 / 青柠汁。",
                },
            },
            "required": ["ingredient"],
        },
        execute=find_substitute,
    ),
    ToolDef(
        name="get_knowledge",
        description=(
            "鸡尾酒通用知识问答，涵盖调酒技法、鸡尾酒历史、材料特性、风味搭配等主题，"
            "基于知识库 RAG 检索生成，附带引用来源。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "知识问题，如 摇和与搅拌的区别 / 马天尼的起源。",
                },
                "top_k": {
                    "type": "integer",
                    "description": "检索片段数量，默认 5，最大 20。",
                },
            },
            "required": ["query"],
        },
        execute=get_knowledge,
    ),
]


def get_tool(name: str) -> ToolDef | None:
    """按名称查找工具定义，未找到返回 None。"""
    for tool in TOOLS:
        if tool.name == name:
            return tool
    return None


__all__ = ["TOOLS", "ToolDef", "get_tool"]
