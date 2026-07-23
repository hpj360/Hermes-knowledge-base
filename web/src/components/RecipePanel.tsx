import { useEffect, useState } from "react";
import { api } from "../api";
import type { LabRecipe } from "../types";
import { PendingReviewPanel } from "./PendingReviewPanel";
import { SkeletonList } from "./Skeleton";

interface RecipePanelProps {
  /** 打开 UGC 编辑器（外部通过 tab 切换实现，组件本身只发请求）。 */
  onCreateRecipe?: () => void;
  /** 编辑已有配方。 */
  onEditRecipe?: (docId: string) => void;
}

const SOURCE_OPTIONS = [
  { value: "", label: "全部来源" },
  { value: "local", label: "本地" },
  { value: "iba_dataset", label: "IBA 金标准" },
  { value: "thecocktaildb", label: "TheCocktailDB" },
  { value: "ugc", label: "用户投稿" },
];

const VERIFIED_OPTIONS = [
  { value: "", label: "全部状态" },
  { value: "true", label: "已审核" },
  { value: "false", label: "待审核" },
];

const HIDDEN_OPTIONS = [
  { value: "", label: "全部可见性" },
  { value: "false", label: "仅可见" },
  { value: "true", label: "仅隐藏" },
];

/** M4 配方治理面板：筛选 + 卡片网格 + verify/hide 操作 + 待审核队列。 */
export function RecipePanel({ onCreateRecipe, onEditRecipe }: RecipePanelProps) {
  const [items, setItems] = useState<LabRecipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterVerified, setFilterVerified] = useState("");
  const [filterHidden, setFilterHidden] = useState("");
  const [search, setSearch] = useState("");
  const [busyDocId, setBusyDocId] = useState<string | null>(null);
  const [reviewTick, setReviewTick] = useState(0);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const params: Parameters<typeof api.labRecipes>[0] = { limit: 200 };
      if (filterSource) params.source = filterSource;
      if (filterVerified === "true") params.verified = true;
      else if (filterVerified === "false") params.verified = false;
      if (filterHidden === "true") params.hidden = true;
      else if (filterHidden === "false") params.hidden = false;
      const resp = await api.labRecipes(params);
      setItems(resp.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [filterSource, filterVerified, filterHidden]); // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = search
    ? items.filter((r) => (r.title || "").toLowerCase().includes(search.toLowerCase()))
    : items;

  const handleVerify = async (docId: string) => {
    setBusyDocId(docId);
    try {
      await api.labVerifyRecipe(docId);
      await load();
      setReviewTick((t) => t + 1);
    } catch (err) {
      alert(`审核失败：${err instanceof Error ? err.message : err}`);
    } finally {
      setBusyDocId(null);
    }
  };

  const handleToggleHide = async (recipe: LabRecipe) => {
    setBusyDocId(recipe.doc_id);
    try {
      await api.labHideRecipe(recipe.doc_id, !recipe.hidden);
      await load();
    } catch (err) {
      alert(`操作失败：${err instanceof Error ? err.message : err}`);
    } finally {
      setBusyDocId(null);
    }
  };

  const clearFilters = () => {
    setFilterSource("");
    setFilterVerified("");
    setFilterHidden("");
    setSearch("");
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* 页面头部：杂志式 eyebrow + display-title + 细线分隔 */}
      <div
        className="flex items-baseline justify-between mb-6 pb-4 border-b"
        style={{ borderColor: "var(--ink-200)" }}
      >
        <div>
          <p className="eyebrow mb-1">RECIPES</p>
          <h2 className="display-title">📝 配方治理</h2>
        </div>
        <span
          className="text-xs"
          style={{ color: "var(--ink-400)", fontFamily: "var(--font-sans)" }}
        >
          外部数据源 / 审核 / 隐藏
        </span>
      </div>

      {/* 待审核队列（status=pending 自动加载） */}
      <PendingReviewPanel
        refreshTick={reviewTick}
        onResolved={() => {
          load();
          setReviewTick((t) => t + 1);
        }}
      />

      {/* 筛选栏 — 杂志式：eyebrow + 细线分隔 */}
      <div className="card p-4 mb-6">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="eyebrow">筛选</span>
          <select
            className="text-sm border rounded px-2 py-1 bg-white min-w-[140px]"
            style={{ borderColor: "var(--ink-200)" }}
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            aria-label="来源筛选"
          >
            {SOURCE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            className="text-sm border rounded px-2 py-1 bg-white"
            style={{ borderColor: "var(--ink-200)" }}
            value={filterVerified}
            onChange={(e) => setFilterVerified(e.target.value)}
            aria-label="审核状态筛选"
          >
            {VERIFIED_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            className="text-sm border rounded px-2 py-1 bg-white"
            style={{ borderColor: "var(--ink-200)" }}
            value={filterHidden}
            onChange={(e) => setFilterHidden(e.target.value)}
            aria-label="可见性筛选"
          >
            {HIDDEN_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <input
            type="search"
            className="input flex-1 min-w-[160px]"
            placeholder="搜索配方名…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="配方搜索"
          />
          {(filterSource || filterVerified || filterHidden || search) && (
            <button
              type="button"
              onClick={clearFilters}
              className="btn-ghost text-xs"
            >
              清除
            </button>
          )}
          <span
            className="ml-auto text-sm flex items-baseline gap-2"
            style={{ color: "var(--ink-600)" }}
          >
            <span
              className="numeral"
              style={{ fontSize: "1.5rem", color: "var(--gold-500)" }}
            >
              {filtered.length}
            </span>
            <span>款</span>
          </span>
          {onCreateRecipe && (
            <button
              type="button"
              onClick={onCreateRecipe}
              className="btn-primary text-sm"
            >
              + 创作配方
            </button>
          )}
        </div>
      </div>

      {/* 错误 */}
      {error && (
        <div className="card p-6 mb-4 text-center text-red-600">加载失败：{error}</div>
      )}

      {/* 加载中 — F3: 骨架屏替代纯文字 */}
      {loading && items.length === 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <SkeletonList count={6} />
        </div>
      )}

      {/* 空状态 — 杂志化 */}
      {!loading && filtered.length === 0 && !error && (
        <div className="text-center py-16">
          <div className="text-3xl mb-3" style={{ color: "var(--gold-500)" }}>
            ◆
          </div>
          <p className="eyebrow mb-2">EMPTY</p>
          <p className="section-title mb-2">暂无配方</p>
          <p
            className="text-sm"
            style={{ color: "var(--ink-400)", fontFamily: "var(--font-sans)" }}
          >
            请先同步外部数据源或创作新配方
          </p>
        </div>
      )}

      {/* 配方卡片网格 */}
      {filtered.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((r) => (
            <RecipeCard
              key={r.doc_id}
              recipe={r}
              busy={busyDocId === r.doc_id}
              onVerify={() => handleVerify(r.doc_id)}
              onToggleHide={() => handleToggleHide(r)}
              onEdit={onEditRecipe ? () => onEditRecipe(r.doc_id) : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface RecipeCardProps {
  recipe: LabRecipe;
  busy: boolean;
  onVerify: () => void;
  onToggleHide: () => void;
  onEdit?: () => void;
}

function RecipeCard({ recipe, busy, onVerify, onToggleHide, onEdit }: RecipeCardProps) {
  const [imgError, setImgError] = useState(false);
  const statusText = (() => {
    switch (recipe.status) {
      case "draft": return "草稿";
      case "pending": return "待审核";
      case "published": return "已发布";
      case "rejected": return "已驳回";
      default: return recipe.status;
    }
  })();
  // 状态标签：保持现有 statusClass 逻辑不变（测试可能依赖）
  const statusClass = (() => {
    switch (recipe.status) {
      case "published": return "bg-brand-50 text-brand-700";
      case "pending": return "bg-gold-100 text-gold-700";
      case "rejected": return "bg-red-50 text-red-600";
      default: return "bg-ink-100 text-ink-600";
    }
  })();

  return (
    <div
      className={`card p-4 flex flex-col gap-2 hover:shadow-md transition-shadow ${
        recipe.hidden ? "opacity-55" : ""
      }`}
      data-doc-id={recipe.doc_id}
    >
      {recipe.image_url && !imgError ? (
        <img
          src={recipe.image_url}
          alt={recipe.title || "配方"}
          loading="lazy"
          onError={() => setImgError(true)}
          className="w-full h-40 object-cover rounded mb-2"
          style={{ borderRadius: "var(--r-sm)" }}
        />
      ) : (
        <div
          className="w-full h-40 rounded mb-2 flex flex-col items-center justify-center"
          style={{
            background:
              "linear-gradient(135deg, var(--ink-100) 0%, var(--ink-50) 100%)",
            borderRadius: "var(--r-sm)",
          }}
        >
          <span className="text-2xl mb-1" style={{ color: "var(--gold-500)" }}>
            ◆
          </span>
          <span className="eyebrow" style={{ fontSize: "0.6rem" }}>
            NO IMAGE
          </span>
        </div>
      )}
      <div className="flex items-start justify-between gap-2">
        <h3
          className="font-semibold truncate flex-1"
          style={{
            fontFamily: "var(--font-serif)",
            color: "var(--ink-900)",
            fontSize: "1.05rem",
          }}
          title={recipe.title}
        >
          {recipe.title || "(未命名)"}
        </h3>
        <span className={`text-xs px-2 py-0.5 rounded-full ${statusClass}`}>
          {statusText}
        </span>
      </div>
      <div className="flex gap-2 flex-wrap items-center text-xs">
        <span className="px-1.5 py-0.5 rounded bg-brand-50 text-brand-700">
          {recipe.source || "local"}
        </span>
        {recipe.verified ? (
          <span className="px-1.5 py-0.5 rounded bg-green-50 text-green-700">✓ 已审核</span>
        ) : (
          <span className="px-1.5 py-0.5 rounded bg-ink-100 text-ink-600">待审核</span>
        )}
        {recipe.hidden && (
          <span className="px-1.5 py-0.5 rounded bg-red-50 text-red-600">隐藏</span>
        )}
        {recipe.season && (
          <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700">{recipe.season}</span>
        )}
      </div>
      <div className="text-xs text-gray-400 break-all" title={recipe.doc_id}>
        {recipe.doc_id}
      </div>
      <div className="flex gap-2 pt-2 border-t border-dashed border-ink-100">
        {!recipe.verified && (
          <button
            type="button"
            onClick={onVerify}
            disabled={busy}
            className="btn-ghost text-xs"
          >
            审核通过
          </button>
        )}
        <button
          type="button"
          onClick={onToggleHide}
          disabled={busy}
          className="btn-ghost text-xs"
        >
          {recipe.hidden ? "取消隐藏" : "隐藏"}
        </button>
        {onEdit && (recipe.status === "draft" || recipe.status === "rejected") && (
          <button
            type="button"
            onClick={onEdit}
            disabled={busy}
            className="btn-ghost text-xs ml-auto"
          >
            编辑
          </button>
        )}
      </div>
    </div>
  );
}
