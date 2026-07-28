import { useEffect, useState } from "react";
import { api } from "../api";
import type { LabRecipe, LabRecipeVariant } from "../types";
import { PendingReviewPanel } from "./PendingReviewPanel";
import { SkeletonList } from "./Skeleton";
import { showToast } from "./Toast";
import { EmptyState, ErrorBanner, HeadingText, MetaText, MonoText, StatusBadge } from "./ui";

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
      showToast(`审核失败：${err instanceof Error ? err.message : err}`, "danger");
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
      showToast(`操作失败：${err instanceof Error ? err.message : err}`, "danger");
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
      <div className="flex items-baseline justify-between mb-6 pb-4 border-b border-[color:var(--ink-200)]">
        <div>
          <p className="eyebrow mb-1">RECIPES</p>
          <h2 className="display-title">📝 配方治理</h2>
        </div>
        <MetaText className="text-xs">
          外部数据源 / 审核 / 隐藏
        </MetaText>
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
            className="select min-w-[140px]"
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            aria-label="来源筛选"
          >
            {SOURCE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            className="select"
            value={filterVerified}
            onChange={(e) => setFilterVerified(e.target.value)}
            aria-label="审核状态筛选"
          >
            {VERIFIED_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            className="select"
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
          <span className="ml-auto text-sm flex items-baseline gap-2 text-[color:var(--ink-600)]">
            <span className="numeral text-[1.5rem] text-[color:var(--gold-500)]">
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

      {/* 错误 — 用 ErrorBanner（role=alert + token 化） */}
      {error && (
        <div className="card p-6 mb-4 text-center">
          <ErrorBanner>加载失败：{error}</ErrorBanner>
        </div>
      )}

      {/* 加载中 — F3: 骨架屏替代纯文字 */}
      {loading && items.length === 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <SkeletonList count={6} />
        </div>
      )}

      {/* 空状态 — 杂志化 */}
      {!loading && filtered.length === 0 && !error && (
        <EmptyState
          title="暂无配方"
          description="请先同步外部数据源或创作新配方"
        />
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

// 状态 -> StatusBadge variant 映射（替代原 statusStyle inline 对象）
const STATUS_VARIANT_MAP: Record<string, "brand" | "gold" | "danger" | "ink"> = {
  published: "brand",
  pending: "gold",
  rejected: "danger",
  draft: "ink",
};

function RecipeCard({ recipe, busy, onVerify, onToggleHide, onEdit }: RecipeCardProps) {
  const [imgError, setImgError] = useState(false);
  const [showVariants, setShowVariants] = useState(false);
  const [variants, setVariants] = useState<LabRecipeVariant[]>([]);
  const [variantLoading, setVariantLoading] = useState(false);
  const statusText = (() => {
    switch (recipe.status) {
      case "draft": return "草稿";
      case "pending": return "待审核";
      case "published": return "已发布";
      case "rejected": return "已驳回";
      default: return recipe.status;
    }
  })();
  const statusVariant = STATUS_VARIANT_MAP[recipe.status] ?? "ink";

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
          className="w-full h-40 object-cover rounded-md mb-2"
        />
      ) : (
        <div
          className="w-full h-40 rounded-md mb-2 flex flex-col items-center justify-center"
          style={{ background: "linear-gradient(135deg, var(--ink-100) 0%, var(--ink-50) 100%)" }}
        >
          <span className="text-2xl mb-1 text-[color:var(--gold-500)]">◆</span>
          <span className="eyebrow text-[0.6rem]">NO IMAGE</span>
        </div>
      )}
      <div className="flex items-start justify-between gap-2">
        <HeadingText
          size="1.05rem"
          as="h3"
          className="font-semibold truncate flex-1"
          title={recipe.title}
        >
          {recipe.title || "(未命名)"}
        </HeadingText>
        <StatusBadge variant={statusVariant}>{statusText}</StatusBadge>
      </div>
      <div className="flex gap-2 flex-wrap items-center text-xs">
        <StatusBadge variant="brand" pill={false}>
          {recipe.source || "local"}
        </StatusBadge>
        {recipe.verified ? (
          <StatusBadge variant="success" pill={false}>
            ✓ 已审核
          </StatusBadge>
        ) : (
          <StatusBadge variant="ink" pill={false}>
            待审核
          </StatusBadge>
        )}
        {recipe.hidden && (
          <StatusBadge variant="danger" pill={false}>
            隐藏
          </StatusBadge>
        )}
        {recipe.season && (
          <StatusBadge variant="gold" pill={false}>
            {recipe.season}
          </StatusBadge>
        )}
      </div>
      <MonoText
        className="text-xs break-all"
        as="div"
        title={recipe.doc_id}
      >
        {recipe.doc_id}
      </MonoText>
      <div className="flex gap-2 pt-2 border-t border-dashed border-[color:var(--ink-100)]">
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
      {/* 配方变体 */}
      <div>
        <button
          type="button"
          onClick={async () => {
            if (!showVariants && variants.length === 0) {
              setVariantLoading(true);
              try {
                const res = await api.labListVariants(recipe.doc_id);
                setVariants(res.items);
              } catch { setVariants([]); }
              setVariantLoading(false);
            }
            setShowVariants(!showVariants);
          }}
          className="btn-ghost text-xs text-[color:var(--ink-600)]"
        >
          {showVariants ? "▾" : "▸"} 变体
          {variants.length > 0 && ` (${variants.length})`}
        </button>
        {showVariants && (
          <div className="mt-2 space-y-1">
            {variantLoading ? (
              <MetaText className="text-xs">加载中…</MetaText>
            ) : variants.length === 0 ? (
              <MetaText className="text-xs">暂无变体</MetaText>
            ) : (
              variants.map((v) => (
                <div
                  key={v.variant_doc_id}
                  className="text-xs flex items-center gap-1 px-2 py-1 rounded bg-[color:var(--ink-50)]"
                >
                  <span className="text-[color:var(--brand-700)]">↳</span>
                  <span className="truncate text-[color:var(--ink-900)]">
                    {v.variant_title}
                  </span>
                  {v.variant_note && (
                    <MetaText className="truncate ml-1">
                      — {v.variant_note}
                    </MetaText>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
