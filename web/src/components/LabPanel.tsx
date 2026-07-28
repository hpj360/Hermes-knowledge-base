import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api";
import type {
  IMASearchItem,
  IMASyncResult,
  LabDailyRecipe,
  LabMatchItem,
  LabMatchResult,
  LabTranslateResult,
} from "../types";
import { Modal } from "./Modal";
import { showToast } from "./Toast";
import {
  BauhausButton,
  BauhausCard,
  BauhausDisplay,
  BauhausMetric,
  BauhausSectionLabel,
  GoldFoilCard,
  MetaText,
} from "./ui";

interface LabPanelProps {
  onJumpToDoc?: (docId: string, chunkRowid?: number) => void;
}

/** M3 实验室主面板：今日推荐 + 材料选择 + 匹配结果 + 替代原料 + 制作步骤 + IMA 同步。 */
export function LabPanel({ onJumpToDoc }: LabPanelProps) {
  const [daily, setDaily] = useState<LabDailyRecipe | null>(null);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [result, setResult] = useState<LabMatchResult | null>(null);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState("");

  // B6: IMA 知识库同步入口
  const [showImaModal, setShowImaModal] = useState(false);

  // P1: LLM 翻译配方标题入口
  const [showTranslateModal, setShowTranslateModal] = useState(false);

  // 加载今日推荐
  useEffect(() => {
    let cancelled = false;
    api
      .labDaily()
      .then((d) => {
        if (!cancelled && d && d.title) setDaily(d);
      })
      .catch(() => {
        /* 静默：今日推荐为可选 */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedNames = useMemo(() => Object.keys(selected), [selected]);

  const toggleMaterial = (name: string, category: string) => {
    setSelected((prev) => {
      const next = { ...prev };
      if (next[name]) {
        delete next[name];
      } else {
        next[name] = category;
      }
      return next;
    });
  };

  /** B6+: 点击缺失材料的替代品 → 加入已选材料，重新匹配。 */
  const applySubstitute = (canonical: string, sub: string) => {
    setSelected((prev) => {
      const next = { ...prev };
      // 仅当用户尚未拥有该替代品时加入
      if (!next[sub]) {
        next[sub] = prev[canonical] || "modifier";
      }
      return next;
    });
    showToast(`已加入替代原料：${sub}`, "success");
  };

  const clearAll = () => {
    setSelected({});
    setResult(null);
    setError("");
  };

  const quickSelect = (names: string[]) => {
    const next: Record<string, string> = {};
    for (const name of names) {
      const found = MATERIAL_CATEGORIES.find((c) =>
        c.items.some((it) => it === name)
      );
      if (found) next[name] = found.id;
    }
    setSelected(next);
    setResult(null);
    setError("");
  };

  const doMatch = async () => {
    if (selectedNames.length === 0) return;
    setMatching(true);
    setError("");
    try {
      const r = await api.labMatch(selectedNames);
      setResult(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "匹配失败");
      setResult(null);
    } finally {
      setMatching(false);
    }
  };

  const reasonText = (reason?: string): string => {
    if (reason === "season") return "应季推荐";
    if (reason === "hot") return "本周热门";
    if (reason === "random") return "随机发现";
    return "今日推荐";
  };

  const filteredCategories = useMemo(() => {
    if (!search.trim()) return MATERIAL_CATEGORIES;
    const q = search.trim().toLowerCase();
    return MATERIAL_CATEGORIES.map((c) => ({
      ...c,
      items: c.items.filter((it) => it.toLowerCase().includes(q)),
    })).filter((c) => c.items.length > 0);
  }, [search]);

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* 页面头部：包豪斯章节标签 + 大标题 + IMA 入口 */}
      <div className="text-center mb-8">
        <BauhausSectionLabel className="mb-2">LABORATORY</BauhausSectionLabel>
        <BauhausDisplay as="h2">🧪 鸡尾酒实验室</BauhausDisplay>
        <hr className="divider-gold w-24 mx-auto mt-4" />
        <MetaText className="text-sm mt-4">
          选择手头的材料，发现你能调的鸡尾酒
        </MetaText>
        <div className="mt-4 flex gap-3 justify-center">
          <BauhausButton
            variant="outline"
            className="text-xs"
            onClick={() => setShowImaModal(true)}
            aria-label="从 IMA 知识库同步内容"
          >
            📚 从 IMA 知识库同步
          </BauhausButton>
          <BauhausButton
            variant="outline"
            className="text-xs"
            onClick={() => setShowTranslateModal(true)}
            aria-label="翻译英文配方标题为中文"
          >
            🌐 翻译配方标题
          </BauhausButton>
        </div>
      </div>

      {/* C3: 金箔引导卡（mockup lab.html#L84-L88，gap-analysis P0.4） */}
      <GoldFoilCard
        className="mb-8"
        title="调酒实验室"
        quote="告诉我们你手边有哪些材料，我们将从 IBA 金标准与 TheCocktailDB 600+ 配方中为你匹配最合适的鸡尾酒。"
        attribution="HERMES LAB"
      />

      {/* 今日推荐 — .daily-recipe 语义类（mockup lab.html#L90-L97） */}
      {daily && daily.title && (
        <div
          className="daily-recipe cursor-pointer"
          onClick={() =>
            onJumpToDoc && daily.doc_id
              ? onJumpToDoc(daily.doc_id, daily.chunk_rowid || undefined)
              : undefined
          }
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === " ") && onJumpToDoc && daily.doc_id) {
              e.preventDefault();
              onJumpToDoc(daily.doc_id, daily.chunk_rowid || undefined);
            }
          }}
          role="button"
          tabIndex={0}
        >
          <span className="daily-badge">今日推荐</span>
          <span className="daily-name">{daily.title}</span>
          <span className="daily-reason">{reasonText(daily.reason)}</span>
          {daily.base_spirit && (
            <span className="match-badge match-full whitespace-nowrap">
              {daily.base_spirit}
            </span>
          )}
        </div>
      )}

      {/* 材料选择器 — .material-selector 语义类（gap-analysis P1.1） */}
      <div className="material-selector mb-6">
        <BauhausSectionLabel className="mb-4">选择材料</BauhausSectionLabel>
        <input
          className="input material-search"
          placeholder="搜索材料... 如 金酒"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="材料搜索"
        />

        {filteredCategories.map((cat) => (
          <div key={cat.id} className="material-category">
            <div className="flex items-baseline gap-2 mb-3">
              <span className="eyebrow">{cat.label}</span>
              <span style={{ fontFamily: "var(--font-mono)" }}>{cat.items.length}</span>
            </div>
            <div className="chip-list">
              {cat.items.map((name) => {
                const isSelected = !!selected[name];
                // P0.1 修复：用 .chip-chip.cat-{category}.selected 触发 _components.css 4 色分类规则
                return (
                  <button
                    key={name}
                    type="button"
                    onClick={() => toggleMaterial(name, cat.id)}
                    className={`chip-chip cat-${cat.id}${isSelected ? " selected" : ""}`}
                    aria-pressed={isSelected}
                  >
                    {name}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        {/* 已选材料条 — .selected-bar 语义类 */}
        {selectedNames.length > 0 && (
          <div className="selected-bar">
            <span className="eyebrow">已选</span>
            {selectedNames.map((name) => (
              <button
                key={name}
                type="button"
                onClick={() => toggleMaterial(name, selected[name])}
                className="selected-chip"
              >
                {name} ×
              </button>
            ))}
            <BauhausButton
              variant="outline"
              onClick={clearAll}
              className="clear-btn text-xs ml-auto"
            >
              清空
            </BauhausButton>
          </div>
        )}

        <BauhausButton
          variant="solid"
          onClick={doMatch}
          className="match-btn w-full mt-5"
          disabled={matching || selectedNames.length === 0}
        >
          {matching
            ? "匹配中..."
            : selectedNames.length > 0
              ? `匹配配方 →（已选 ${selectedNames.length} 种）`
              : "匹配配方 →"}
        </BauhausButton>
      </div>

      {/* 错误 — BauhausCard 包裹，保留 inline 文本色（无对应语义类，token 引用） */}
      {error && (
        <BauhausCard
          accent="ink"
          className="p-6 mb-6 text-center text-sm"
          style={{ color: "var(--danger)" }}
        >
          匹配失败：{error}
        </BauhausCard>
      )}

      {/* 空状态 — .lab-empty 语义类 */}
      {!result && !error && (
        <div className="lab-empty text-center py-16">
          {/* 保留 1 处 inline：装饰符号 ◆ 的领域色（无对应语义类） */}
          <div
            className="text-3xl mb-3"
            style={{ color: "var(--amber)" }}
          >
            ◆
          </div>
          <BauhausSectionLabel className="mb-2">START</BauhausSectionLabel>
          <p className="section-title mb-2">选择材料开始</p>
          <MetaText className="text-sm mb-6">
            点击上方材料 chip，或试试这些：
          </MetaText>
          <div className="flex gap-2 justify-center flex-wrap">
            <BauhausButton
              variant="outline"
              className="text-xs"
              onClick={() => quickSelect(["金酒", "味美思", "橄榄"])}
            >
              马天尼套餐
            </BauhausButton>
            <BauhausButton
              variant="outline"
              className="text-xs"
              onClick={() => quickSelect(["朗姆酒", "青柠汁", "糖浆", "薄荷叶", "苏打水"])}
            >
              莫吉托套餐
            </BauhausButton>
            <BauhausButton
              variant="outline"
              className="text-xs"
              onClick={() => quickSelect(["龙舌兰", "橙汁", "糖浆"])}
            >
              龙舌兰日出套餐
            </BauhausButton>
          </div>
        </div>
      )}

      {/* 匹配结果 — 分组用 section-title + 编号 */}
      {result && (
        <div>
          <MatchGroup
            title="现在就能做"
            items={result.full_match}
            emptyHint="无完整匹配，再选一些材料试试"
            variant="full"
            onJumpToDoc={onJumpToDoc}
            onApplySubstitute={applySubstitute}
          />
          <MatchGroup
            title="差一种就能做"
            items={result.partial_match}
            emptyHint="无差一种匹配"
            variant="partial"
            onJumpToDoc={onJumpToDoc}
            onApplySubstitute={applySubstitute}
          />
        </div>
      )}

      {/* B6: IMA 同步 Modal */}
      {showImaModal && (
        <ImaSyncDialog
          onClose={() => setShowImaModal(false)}
          onSynced={() => {
            // 同步后清空结果，让用户重新匹配
            setResult(null);
          }}
        />
      )}

      {/* P1: 翻译配方标题 Modal */}
      {showTranslateModal && (
        <TranslateDialog
          onClose={() => setShowTranslateModal(false)}
          onTranslated={() => {
            // 翻译后清空匹配结果，让用户重新匹配以拿到新标题
            setResult(null);
          }}
        />
      )}
    </div>
  );
}

interface MatchGroupProps {
  title: string;
  items: LabMatchItem[];
  emptyHint: string;
  variant: "full" | "partial";
  onJumpToDoc?: (docId: string, chunkRowid?: number) => void;
  onApplySubstitute?: (canonical: string, sub: string) => void;
}

function MatchGroup({
  title,
  items,
  emptyHint,
  variant,
  onJumpToDoc,
  onApplySubstitute,
}: MatchGroupProps) {
  if (items.length === 0) {
    return (
      <div className="empty-state-mini text-center py-6">{emptyHint}</div>
    );
  }
  return (
    <div className="mb-8">
      <div className="flex items-baseline gap-3 mb-4">
        <span style={{ fontFamily: "var(--font-mono)" }}>
          {String(items.length).padStart(2, "0")}
        </span>
        <h3 className="section-title text-xl">{title}</h3>
        <hr className="divider-gold flex-1" />
      </div>
      <div className="space-y-4">
        {items.map((r) => (
          <RecipeMatchCard
            key={r.doc_id}
            item={r}
            variant={variant}
            onJumpToDoc={onJumpToDoc}
            onApplySubstitute={onApplySubstitute}
          />
        ))}
      </div>
    </div>
  );
}

interface RecipeMatchCardProps {
  item: LabMatchItem;
  variant: "full" | "partial";
  onJumpToDoc?: (docId: string, chunkRowid?: number) => void;
  onApplySubstitute?: (canonical: string, sub: string) => void;
}

function RecipeMatchCard({
  item,
  variant,
  onJumpToDoc,
  onApplySubstitute,
}: RecipeMatchCardProps) {
  const isPartial = variant === "partial";
  const [expanded, setExpanded] = useState(false);
  const hasSteps = !!item.steps && item.steps.length > 0;
  const missingItems = item.ingredients.filter((ing) => !ing.have);
  const hasSubstitutes = missingItems.some((ing) => ing.substitutes && ing.substitutes.length > 0);
  // variant → .recipe-card 修饰类（_components.css 提供 .full-match/.partial-match 左边框色）
  const cardClass = `recipe-card ${isPartial ? "partial-match" : "full-match"}`;
  // variant → .match-badge 修饰类（_components.css 提供 .match-full/.match-partial 配色）
  const badgeClass = `match-badge ${isPartial ? "match-partial" : "match-full"}`;
  const badgeText = isPartial
    ? `缺 ${item.missing_count ?? (item.missing?.length || 0)} 种`
    : "材料齐全";

  return (
    <div className={cardClass}>
      <div className="recipe-header">
        <h3 className="recipe-name">{item.title}</h3>
        <span className={badgeClass}>{badgeText}</span>
      </div>

      {/* 材料清单 — .ing.have/.missing 语义类（_components.css 提供 ✓/✗ 配色 + 删除线） */}
      <div className="recipe-ingredients">
        {(item.ingredients || []).map((ing) => (
          <span key={ing.name} className={`ing ${ing.have ? "have" : "missing"}`}>
            {ing.have ? "✓ " : "✗ "}
            {ing.name}
          </span>
        ))}
      </div>

      {/* 替代原料推荐 — .substitute-suggest 语义类 + .sub-chip */}
      {hasSubstitutes && (
        <div className="substitute-suggest">
          {missingItems
            .filter((ing) => ing.substitutes && ing.substitutes.length > 0)
            .map((ing) => (
              <span
                key={ing.name}
                className="flex items-center gap-2 flex-wrap"
              >
                <span className="ing missing">{ing.name} →</span>
                {(ing.substitutes || []).map((sub) => (
                  <button
                    key={sub}
                    type="button"
                    onClick={() => onApplySubstitute?.(ing.name, sub)}
                    className="sub-chip"
                    aria-label={`使用 ${sub} 替代 ${ing.name}`}
                  >
                    {sub}
                  </button>
                ))}
              </span>
            ))}
        </div>
      )}

      {/* 缺失摘要（partial 时仍保留简短列表，便于无替代时也可视） */}
      {isPartial && item.missing && item.missing.length > 0 && !hasSubstitutes && (
        <div className="substitute-suggest">
          缺：{item.missing.join("、")}
        </div>
      )}

      {/* 制作方法推荐：可折叠的步骤区，杂志式编号 */}
      {hasSteps && (
        <div className="mb-3 rounded p-3 bg-[var(--ink-50)] border border-[var(--ink-100)]">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="w-full flex items-center justify-between text-left eyebrow"
            aria-expanded={expanded}
          >
            <span>制作方法 · {item.steps!.length} 步</span>
            <span className="text-xs text-[var(--ink-400)]" aria-hidden="true">
              {expanded ? "收起 ▲" : "展开 ▼"}
            </span>
          </button>
          {expanded && (
            <ol className="m-0 mt-2 px-4 pb-2 list-none">
              {item.steps!.map((step, i) => (
                <li key={i} className="flex gap-3 mb-2 last:mb-0">
                  {/* 保留 1 处 inline：步骤编号样式（serif + wine，无对应语义类） */}
                  <span
                    className="font-serif font-bold text-sm min-w-[1.5rem] text-right"
                    style={{ color: "var(--wine)" }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {/* 保留 1 处 inline：步骤正文样式（ink-900 + 行高，无对应语义类） */}
                  <span
                    className="flex-1 text-sm leading-relaxed"
                    style={{ color: "var(--ink-900)" }}
                  >
                    {step}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      <div className="recipe-footer">
        {item.chunk_rowid ? (
          <button
            type="button"
            onClick={() =>
              onJumpToDoc && item.doc_id
                ? onJumpToDoc(item.doc_id, item.chunk_rowid || undefined)
                : undefined
            }
            className="citation-link"
          >
            [{item.chunk_rowid}] 查看引用
          </button>
        ) : (
          <span className="citation-link opacity-60">无引用</span>
        )}
        {item.base_spirit && (
          <span className="text-xs text-[var(--ink-400)]">
            基酒：{item.base_spirit}
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// B6: IMA 知识库同步弹窗
// ---------------------------------------------------------------------------

/** 配置项 inline code 样式：ink-100 底 + 等宽字体（无对应语义类，集中定义避免重复 inline） */
function ConfigCode({ children }: { children: ReactNode }) {
  return (
    <code
      className="font-mono mx-1"
      style={{
        background: "var(--ink-100)",
        padding: "1px 4px",
        borderRadius: "var(--r-sm)",
        fontSize: "0.85em",
      }}
    >
      {children}
    </code>
  );
}

interface ImaSyncDialogProps {
  onClose: () => void;
  onSynced?: () => void;
}

function ImaSyncDialog({ onClose, onSynced }: ImaSyncDialogProps) {
  const [query, setQuery] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchHits, setSearchHits] = useState<IMASearchItem[] | null>(null);
  const [lastResult, setLastResult] = useState<IMASyncResult | null>(null);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    try {
      const r = await api.labImaSearch(query.trim(), undefined, 5);
      setSearchHits(r.info_list || []);
      if ((r.info_list || []).length === 0) {
        showToast("未找到相关内容", "warning");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      showToast(`检索失败：${msg}`, "danger");
    } finally {
      setSearching(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError("");
    try {
      const r = await api.labImaSync({
        query: query.trim(),
        limit: 50,
        category: "资料",
      });
      setLastResult(r);
      const msg = `同步完成：新增 ${r.imported}，跳过 ${r.skipped}，失败 ${r.failed}`;
      showToast(msg, r.failed > 0 ? "warning" : "success");
      onSynced?.();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      showToast(`同步失败：${msg}`, "danger");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="从 IMA 知识库同步"
      maxWidth={560}
      footer={
        <>
          <BauhausButton variant="outline" onClick={onClose} disabled={syncing}>
            关闭
          </BauhausButton>
          <BauhausButton variant="solid" onClick={handleSync} disabled={syncing}>
            {syncing ? "同步中..." : "同步到本地"}
          </BauhausButton>
        </>
      }
    >
      <MetaText className="text-sm mb-4">
        通过 IMA OpenAPI 把知识库中的内容检索并导入到本地知识库。需在服务端配置
        <ConfigCode>KB_IMA_CLIENT_ID</ConfigCode>
        与
        <ConfigCode>KB_IMA_API_KEY</ConfigCode>
        。
      </MetaText>

      <div className="flex gap-2 mb-4">
        <input
          className="input flex-1"
          placeholder="检索关键词，如 鸡尾酒 历史 / 调酒技法"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSearch();
          }}
          aria-label="IMA 检索关键词"
        />
        <BauhausButton
          variant="outline"
          onClick={handleSearch}
          disabled={searching || !query.trim()}
        >
          {searching ? "检索中..." : "预览"}
        </BauhausButton>
      </div>

      {/* 保留 1 处 inline：错误横幅（rgba + var 混用，无对应语义类） */}
      {error && (
        <div
          className="text-xs mb-3 p-2 rounded"
          style={{
            background: "rgba(179, 38, 30, 0.08)",
            color: "var(--danger)",
          }}
        >
          {error}
        </div>
      )}

      {searchHits && (
        <div className="mb-4">
          <BauhausSectionLabel className="mb-2">
            检索预览 · {searchHits.length} 条
          </BauhausSectionLabel>
          {/* 保留 1 处 inline：搜索结果滚动容器（maxHeight + 多 token 边框/底色，无对应语义类） */}
          <div
            className="rounded-md"
            style={{
              maxHeight: "240px",
              overflowY: "auto",
              border: "1px solid var(--ink-200)",
              background: "var(--ink-50)",
            }}
          >
            {searchHits.length === 0 ? (
              <p className="empty-state-mini text-center py-6">
                未找到相关内容
              </p>
            ) : (
              searchHits.map((hit, i) => (
                <div
                  key={i}
                  className="px-3 py-2 border-b last:border-b-0 border-[var(--ink-100)]"
                >
                  {/* 保留 1 处 inline：检索 hit 标题（serif + ink-900，无对应语义类） */}
                  <p
                    className="text-sm font-semibold mb-1"
                    style={{
                      fontFamily: "var(--font-serif)",
                      color: "var(--ink-900)",
                    }}
                  >
                    {hit.title || "未命名"}
                  </p>
                  {/* 保留 1 处 inline：检索 hit 正文（line-clamp + 多 token，无对应语义类） */}
                  <p
                    className="text-xs line-clamp-2"
                    style={{
                      color: "var(--ink-600)",
                      fontFamily: "var(--font-ui)",
                      lineHeight: 1.5,
                    }}
                  >
                    {hit.content || "（无正文预览）"}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* 上次同步结果 — .lab-sync-panel + BauhausMetric（gap-analysis P1.1） */}
      {lastResult && (
        <div className="lab-sync-panel">
          <BauhausSectionLabel className="mb-2">上次同步结果</BauhausSectionLabel>
          <div className="lab-metrics">
            <BauhausMetric label="新增" num={lastResult.imported} variant="outline" />
            <BauhausMetric label="跳过" num={lastResult.skipped} variant="outline" />
            <BauhausMetric
              label="失败"
              num={lastResult.failed}
              variant={lastResult.failed > 0 ? "amber" : "outline"}
            />
          </div>
        </div>
      )}
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// P1: 批量翻译英文配方标题为中文
// ---------------------------------------------------------------------------
interface TranslateDialogProps {
  onClose: () => void;
  onTranslated?: () => void;
}

const TRANSLATE_SOURCE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "", label: "全部配方源" },
  { value: "iba", label: "IBA 官方" },
  { value: "thecocktaildb", label: "TheCocktailDB" },
  { value: "ugc", label: "UGC 用户投稿" },
  { value: "local", label: "本地导入" },
];

function TranslateDialog({ onClose, onTranslated }: TranslateDialogProps) {
  const [source, setSource] = useState("");
  const [limit, setLimit] = useState(50);
  const [translating, setTranslating] = useState(false);
  const [lastResult, setLastResult] = useState<LabTranslateResult | null>(null);
  const [error, setError] = useState("");

  const handleTranslate = async () => {
    setTranslating(true);
    setError("");
    try {
      const r = await api.labTranslateTitles({
        source: source || undefined,
        limit,
      });
      setLastResult(r);
      const msg = `翻译完成：新增 ${r.translated}，跳过 ${r.skipped}，失败 ${r.failed}（${r.model_used}）`;
      showToast(msg, r.failed > 0 ? "warning" : "success");
      onTranslated?.();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      showToast(`翻译失败：${msg}`, "danger");
    } finally {
      setTranslating(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="翻译英文配方标题为中文"
      maxWidth={520}
      footer={
        <>
          <BauhausButton variant="outline" onClick={onClose} disabled={translating}>
            关闭
          </BauhausButton>
          <BauhausButton variant="solid" onClick={handleTranslate} disabled={translating}>
            {translating ? "翻译中..." : "开始翻译"}
          </BauhausButton>
        </>
      }
    >
      <MetaText className="text-sm mb-4">
        将英文配方标题（IBA / TheCocktailDB）批量翻译为中文。已含中文的标题自动跳过。
        LLM 后端可用时使用 AI 翻译，否则回退到内置鸡尾酒词典。
      </MetaText>

      <div className="mb-4">
        <label
          className="eyebrow block mb-2"
          htmlFor="translate-source"
        >
          数据源筛选
        </label>
        <select
          id="translate-source"
          className="input"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          disabled={translating}
        >
          {TRANSLATE_SOURCE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-4">
        <label
          className="eyebrow block mb-2"
          htmlFor="translate-limit"
        >
          翻译上限（1-500）
        </label>
        <input
          id="translate-limit"
          className="input"
          type="number"
          min={1}
          max={500}
          value={limit}
          onChange={(e) => {
            const v = parseInt(e.target.value, 10);
            setLimit(Number.isFinite(v) ? Math.max(1, Math.min(500, v)) : 50);
          }}
          disabled={translating}
        />
      </div>

      {/* 保留 1 处 inline：错误横幅（同 ImaSyncDialog） */}
      {error && (
        <div
          className="text-xs mb-3 p-2 rounded"
          style={{
            background: "rgba(179, 38, 30, 0.08)",
            color: "var(--danger)",
          }}
        >
          {error}
        </div>
      )}

      {/* 上次翻译结果 — .lab-sync-panel + BauhausMetric（gap-analysis P1.1） */}
      {lastResult && (
        <div className="lab-sync-panel">
          <BauhausSectionLabel className="mb-2">
            上次翻译结果 · {lastResult.model_used}
          </BauhausSectionLabel>
          <div className="lab-metrics">
            <BauhausMetric label="翻译" num={lastResult.translated} variant="outline" />
            <BauhausMetric label="跳过" num={lastResult.skipped} variant="outline" />
            <BauhausMetric
              label="失败"
              num={lastResult.failed}
              variant={lastResult.failed > 0 ? "amber" : "outline"}
            />
          </div>
        </div>
      )}
    </Modal>
  );
}

const MATERIAL_CATEGORIES = [
  {
    id: "base_spirit",
    label: "基酒",
    items: ["金酒", "威士忌", "朗姆酒", "龙舌兰", "白兰地", "伏特加"],
  },
  {
    id: "modifier",
    label: "辅料",
    items: ["味美思", "金巴利", "糖浆", "君度", "苦精", "汤力水", "苏打水", "可乐", "姜啤"],
  },
  {
    id: "juice",
    label: "果汁",
    items: ["柠檬汁", "青柠汁", "橙汁", "蔓越莓汁", "菠萝汁", "番茄汁"],
  },
  {
    id: "garnish",
    label: "装饰",
    items: ["橄榄", "柠檬片", "薄荷叶", "樱桃", "橙皮"],
  },
] as const;
