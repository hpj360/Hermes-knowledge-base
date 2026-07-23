import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { LabDailyRecipe, LabMatchItem, LabMatchResult } from "../types";

interface LabPanelProps {
  onJumpToDoc?: (docId: string, chunkRowid?: number) => void;
}

/** M3 实验室主面板：今日推荐 + 材料选择 + 匹配结果。 */
export function LabPanel({ onJumpToDoc }: LabPanelProps) {
  const [daily, setDaily] = useState<LabDailyRecipe | null>(null);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [result, setResult] = useState<LabMatchResult | null>(null);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState("");

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
      {/* 页面头部：杂志式 eyebrow + display-title + 金线 */}
      <div className="text-center mb-8">
        <p className="eyebrow mb-2">LABORATORY</p>
        <h2 className="display-title">🧪 鸡尾酒实验室</h2>
        <hr className="divider-gold w-24 mx-auto mt-4" />
        <p
          className="text-sm mt-4"
          style={{ color: "var(--ink-400)", fontFamily: "var(--font-sans)" }}
        >
          选择手头的材料，发现你能调的鸡尾酒
        </p>
      </div>

      {/* 今日推荐 — 杂志式卡片 */}
      {daily && daily.title && (
        <div
          className="card-elevated mb-8 p-6 cursor-pointer transition-shadow hover:shadow-lg"
          onClick={() =>
            onJumpToDoc && daily.doc_id
              ? onJumpToDoc(daily.doc_id, daily.chunk_rowid || undefined)
              : undefined
          }
          onKeyDown={(e) => {
            // F4: a11y — role=button 需支持 Enter/Space 键盘激活
            if ((e.key === "Enter" || e.key === " ") && onJumpToDoc && daily.doc_id) {
              e.preventDefault();
              onJumpToDoc(daily.doc_id, daily.chunk_rowid || undefined);
            }
          }}
          role="button"
          tabIndex={0}
        >
          <div className="flex items-center gap-3 mb-2">
            <p className="eyebrow">今日推荐</p>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ background: "var(--gold-100)", color: "var(--gold-700)" }}
            >
              {reasonText(daily.reason)}
            </span>
          </div>
          <h3 className="section-title mb-2">{daily.title}</h3>
          {daily.base_spirit && (
            <span
              className="text-xs px-2 py-0.5 rounded"
              style={{ background: "var(--brand-50)", color: "var(--brand-700)" }}
            >
              {daily.base_spirit}
            </span>
          )}
        </div>
      )}

      {/* 材料选择器 — 分类用 eyebrow 区隔，chip 选中态用金/酒红边框 */}
      <div className="card p-6 mb-6">
        <p className="eyebrow mb-4">选择材料</p>
        <input
          className="input mb-5"
          placeholder="搜索材料... 如 金酒"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="材料搜索"
        />

        {filteredCategories.map((cat) => (
          <div
            key={cat.id}
            className="mb-5 last:mb-0 pb-5 last:pb-0 border-b last:border-b-0"
            style={{ borderColor: "var(--ink-100)" }}
          >
            <div className="flex items-baseline gap-2 mb-3">
              <span className="eyebrow">{cat.label}</span>
              <span className="numeral">{cat.items.length}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {cat.items.map((name) => {
                const isSelected = !!selected[name];
                return (
                  <button
                    key={name}
                    type="button"
                    onClick={() => toggleMaterial(name, cat.id)}
                    className="text-xs px-3 py-1.5 rounded-full border transition-all"
                    style={
                      isSelected
                        ? {
                            background: "var(--brand-700)",
                            color: "#fff",
                            borderColor: "var(--brand-700)",
                          }
                        : {
                            background: "transparent",
                            color: "var(--ink-600)",
                            borderColor: "var(--ink-200)",
                          }
                    }
                    aria-pressed={isSelected}
                  >
                    {name}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        {/* 已选材料条 */}
        {selectedNames.length > 0 && (
          <div
            className="mt-5 p-4 rounded"
            style={{
              background: "var(--gold-100)",
              borderLeft: "3px solid var(--gold-500)",
            }}
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="eyebrow">已选</span>
              {selectedNames.map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => toggleMaterial(name, selected[name])}
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{ background: "var(--gold-500)", color: "var(--ink-900)" }}
                >
                  {name} ×
                </button>
              ))}
              <button
                type="button"
                onClick={clearAll}
                className="ml-auto text-xs"
                style={{ color: "var(--ink-400)" }}
              >
                清空
              </button>
            </div>
          </div>
        )}

        <button
          type="button"
          onClick={doMatch}
          className="btn-primary w-full mt-5"
          disabled={matching || selectedNames.length === 0}
        >
          {matching
            ? "匹配中..."
            : selectedNames.length > 0
              ? `匹配配方 →（已选 ${selectedNames.length} 种）`
              : "匹配配方 →"}
        </button>
      </div>

      {/* 错误 */}
      {error && (
        <div
          className="card p-6 mb-6 text-center text-sm"
          style={{ color: "var(--danger)" }}
        >
          匹配失败：{error}
        </div>
      )}

      {/* 空状态 — 杂志化 */}
      {!result && !error && (
        <div className="text-center py-16">
          <div className="text-3xl mb-3" style={{ color: "var(--gold-500)" }}>
            ◆
          </div>
          <p className="eyebrow mb-2">START</p>
          <p className="section-title mb-2">选择材料开始</p>
          <p
            className="text-sm mb-6"
            style={{ color: "var(--ink-400)", fontFamily: "var(--font-sans)" }}
          >
            点击上方材料 chip，或试试这些：
          </p>
          <div className="flex gap-2 justify-center flex-wrap">
            <button
              type="button"
              onClick={() => quickSelect(["金酒", "味美思", "橄榄"])}
              className="btn-secondary text-xs"
            >
              马天尼套餐
            </button>
            <button
              type="button"
              onClick={() => quickSelect(["朗姆酒", "青柠汁", "糖浆", "薄荷叶", "苏打水"])}
              className="btn-secondary text-xs"
            >
              莫吉托套餐
            </button>
            <button
              type="button"
              onClick={() => quickSelect(["龙舌兰", "橙汁", "糖浆"])}
              className="btn-secondary text-xs"
            >
              龙舌兰日出套餐
            </button>
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
          />
          <MatchGroup
            title="差一种就能做"
            items={result.partial_match}
            emptyHint="无差一种匹配"
            variant="partial"
            onJumpToDoc={onJumpToDoc}
          />
        </div>
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
}

function MatchGroup({ title, items, emptyHint, variant, onJumpToDoc }: MatchGroupProps) {
  if (items.length === 0) {
    return (
      <div
        className="text-center py-6 text-sm"
        style={{ color: "var(--ink-400)" }}
      >
        {emptyHint}
      </div>
    );
  }
  return (
    <div className="mb-8">
      <div className="flex items-baseline gap-3 mb-4">
        <span className="numeral">{String(items.length).padStart(2, "0")}</span>
        <h3 className="section-title" style={{ fontSize: "1.25rem" }}>
          {title}
        </h3>
        <hr className="divider-gold flex-1" />
      </div>
      <div className="space-y-4">
        {items.map((r) => (
          <RecipeMatchCard key={r.doc_id} item={r} variant={variant} onJumpToDoc={onJumpToDoc} />
        ))}
      </div>
    </div>
  );
}

interface RecipeMatchCardProps {
  item: LabMatchItem;
  variant: "full" | "partial";
  onJumpToDoc?: (docId: string, chunkRowid?: number) => void;
}

function RecipeMatchCard({ item, variant, onJumpToDoc }: RecipeMatchCardProps) {
  const isPartial = variant === "partial";
  return (
    <div
      className="card p-5"
      style={{
        borderLeft: `3px solid ${isPartial ? "var(--gold-500)" : "var(--brand-700)"}`,
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <h4
          className="font-semibold"
          style={{
            fontFamily: "var(--font-serif)",
            color: "var(--ink-900)",
            fontSize: "1.05rem",
          }}
        >
          {item.title}
        </h4>
        <span
          className="text-xs px-2 py-0.5 rounded-full"
          style={
            isPartial
              ? { background: "var(--gold-100)", color: "var(--gold-700)" }
              : { background: "var(--brand-50)", color: "var(--brand-700)" }
          }
        >
          {isPartial
            ? `缺 ${item.missing_count ?? (item.missing?.length || 0)} 种`
            : "材料齐全"}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5 mb-3">
        {(item.ingredients || []).map((ing) => (
          <span
            key={ing.name}
            className="text-xs px-2 py-0.5 rounded"
            style={
              ing.have
                ? { background: "var(--brand-50)", color: "var(--brand-700)" }
                : {
                    background: "var(--ink-100)",
                    color: "var(--ink-400)",
                    textDecoration: "line-through",
                  }
            }
          >
            {ing.have ? "✓ " : "✗ "}
            {ing.name}
          </span>
        ))}
      </div>
      {isPartial && item.missing && item.missing.length > 0 && (
        <div className="text-xs mb-3" style={{ color: "var(--gold-700)" }}>
          缺：{item.missing.join("、")}
        </div>
      )}
      <div
        className="flex items-center justify-between pt-3 border-t border-dashed"
        style={{ borderColor: "var(--ink-200)" }}
      >
        {item.chunk_rowid ? (
          <button
            type="button"
            onClick={() =>
              onJumpToDoc && item.doc_id
                ? onJumpToDoc(item.doc_id, item.chunk_rowid || undefined)
                : undefined
            }
            className="text-xs"
            style={{ color: "var(--brand-700)" }}
          >
            [{item.chunk_rowid}] 查看引用
          </button>
        ) : (
          <span className="text-xs" style={{ color: "var(--ink-400)" }}>
            无引用
          </span>
        )}
        {item.base_spirit && (
          <span className="text-xs" style={{ color: "var(--ink-400)" }}>
            基酒：{item.base_spirit}
          </span>
        )}
      </div>
    </div>
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
