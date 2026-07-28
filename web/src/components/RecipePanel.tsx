import { useEffect, useState } from "react";
import { api } from "../api";
import type { LabRecipe, LabRecipeVariant } from "../types";
import { PendingReviewPanel } from "./PendingReviewPanel";
import { SkeletonList } from "./Skeleton";
import { showToast } from "./Toast";
import {
  BauhausButton,
  BauhausCard,
  BauhausChip,
  BauhausDisplay,
  BauhausSectionLabel,
  EmptyState,
  ErrorBanner,
  HeadingText,
  MetaText,
  MonoText,
  StatusBadge,
} from "./ui";

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
      {/* 页面头部：包豪斯 SectionLabel + Display + 3px 粗分隔 */}
      <div className="flex items-baseline justify-between mb-6 pb-4" style={{ borderBottom: "var(--border-bold)" }}>
        <div>
          <BauhausSectionLabel className="mb-2">RECIPES</BauhausSectionLabel>
          <BauhausDisplay as="h2">📝 配方治理</BauhausDisplay>
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

      {/* 筛选栏 — 包豪斯卡片 */}
      <BauhausCard accent="ink" className="mb-6">
        <div className="flex items-center gap-3 flex-wrap">
          <BauhausSectionLabel className="mr-2">筛选</BauhausSectionLabel>
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
            <BauhausButton variant="outline" onClick={clearFilters}>
              清除
            </BauhausButton>
          )}
          <span className="ml-auto flex items-baseline gap-2">
            <BauhausChip variant="outline">{filtered.length} 款</BauhausChip>
          </span>
          {onCreateRecipe && (
            <BauhausButton variant="solid" onClick={onCreateRecipe}>
              + 创作配方
            </BauhausButton>
          )}
        </div>
      </BauhausCard>

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
      className={`bauhaus-card flex flex-col gap-2 ${recipe.hidden ? "opacity-55" : ""}`}
      data-doc-id={recipe.doc_id}
    >
      {recipe.image_url && !imgError ? (
        <img
          src={recipe.image_url}
          alt={recipe.title || "配方"}
          loading="lazy"
          onError={() => setImgError(true)}
          className="w-full h-40 object-cover mb-2"
          style={{ borderRadius: "var(--r-sm)" }}
        />
      ) : (
        <div
          className="w-full h-40 mb-2 flex flex-col items-center justify-center"
          style={{
            background: "var(--ink-100)",
            borderRadius: "var(--r-sm)",
          }}
        >
          <span style={{ color: "var(--wine)", fontSize: "1.5rem" }}>◆</span>
          <BauhausSectionLabel className="mt-1">NO IMAGE</BauhausSectionLabel>
        </div>
      )}
      <div className="flex items-start justify-between gap-2 pl-[26px]">
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
      <div className="flex gap-2 flex-wrap items-center text-xs pl-[26px]">
        <BauhausChip variant="outline">{recipe.source || "local"}</BauhausChip>
        {recipe.verified ? (
          <BauhausChip variant="bronze">✓ 已审核</BauhausChip>
        ) : (
          <BauhausChip variant="outline">待审核</BauhausChip>
        )}
        {recipe.hidden && (
          <BauhausChip variant="wine">隐藏</BauhausChip>
        )}
        {recipe.season && (
          <BauhausChip variant="amber">{recipe.season}</BauhausChip>
        )}
      </div>
      <MonoText
        className="text-xs break-all pl-[26px]"
        as="div"
        title={recipe.doc_id}
      >
        {recipe.doc_id}
      </MonoText>
      <div className="flex gap-2 pt-2 pl-[26px]" style={{ borderTop: "1px dashed var(--ink-200)" }}>
        {!recipe.verified && (
          <BauhausButton variant="outline" onClick={onVerify} disabled={busy}>
            审核通过
          </BauhausButton>
        )}
        <BauhausButton variant="outline" onClick={onToggleHide} disabled={busy}>
          {recipe.hidden ? "取消隐藏" : "隐藏"}
        </BauhausButton>
        {onEdit && (recipe.status === "draft" || recipe.status === "rejected") && (
          <BauhausButton variant="solid" onClick={onEdit} disabled={busy} className="ml-auto">
            编辑
          </BauhausButton>
        )}
      </div>
      {/* 配方变体 */}
      <div className="pl-[26px]">
        <BauhausButton
          variant="outline"
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
        >
          {showVariants ? "▾" : "▸"} 变体
          {variants.length > 0 && ` (${variants.length})`}
        </BauhausButton>
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
                  className="text-xs flex items-center gap-1 px-2 py-1"
                  style={{ background: "var(--ink-50)", borderRadius: "var(--r-sm)" }}
                >
                  <span style={{ color: "var(--wine)" }}>↳</span>
                  <span className="truncate" style={{ color: "var(--ink-900)" }}>
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
