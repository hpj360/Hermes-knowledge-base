/**
 * HistoryPanel —— 问答历史列表 + 时间筛选 + 客户端关键词搜索
 *
 * 后端 /api/history 已支持 date_from/date_to/feedback 等参数：
 *   - 时间筛选走服务端（更准确，避免客户端全量加载）
 *   - 关键词搜索保留客户端过滤（保留 highlight 高亮逻辑）
 * 视觉沿用包豪斯风格：BauhausCard / BauhausSectionLabel / BauhausButton / BauhausDisplay。
 * 加载态使用 Skeleton（./Skeleton），空状态显示「暂无问答历史」。
 */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api";
import type { HistoryItem } from "../types";
import { SkeletonList } from "./Skeleton";
import {
  BodyText,
  MetaText,
  MonoText,
  BauhausCard,
  BauhausSectionLabel,
  BauhausDisplay,
  BauhausButton,
} from "./ui";

interface HistoryPanelProps {
  /** 返回问答面板的回调（由 ChatPanel 提供） */
  onBack?: () => void;
  /** 点击某条历史项时的回调，可选 */
  onSelect?: (item: HistoryItem) => void;
}

const DEFAULT_LIMIT = 50;
const ANSWER_SUMMARY_LEN = 100;

/** 时间范围预设 */
type TimePreset = "all" | "7d" | "30d" | "custom";

const TIME_PRESETS: Array<{ value: TimePreset; label: string }> = [
  { value: "all", label: "全部" },
  { value: "7d", label: "近 7 天" },
  { value: "30d", label: "近 30 天" },
  { value: "custom", label: "自定义" },
];

/** 将 Date 格式化为 YYYY-MM-DD（本地时区） */
function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** 根据预设返回 [date_from, date_to] 字符串（YYYY-MM-DD，含） */
function presetToRange(preset: TimePreset, customFrom?: string, customTo?: string): {
  date_from?: string;
  date_to?: string;
} {
  if (preset === "all") return {};
  if (preset === "custom") {
    return {
      date_from: customFrom || undefined,
      date_to: customTo || undefined,
    };
  }
  const days = preset === "7d" ? 7 : 30;
  const today = new Date();
  const start = new Date(today);
  start.setDate(start.getDate() - (days - 1));
  return {
    date_from: formatDate(start),
    date_to: formatDate(today),
  };
}

/** 将文本按关键词拆分为段，命中片段用 <mark> 包裹（大小写不敏感）。
 *  使用 split(capturingGroup) 让匹配片段作为独立元素进入数组，
 *  再用大小写不敏感的字符串比较判定，避免 RegExp.test 在 g 标志下的 lastIndex 状态问题。 */
function highlight(text: string, keyword: string): ReactNode {
  const trimmed = keyword.trim();
  if (!trimmed) return text;
  // 转义正则元字符，避免 keyword 形如 "a.b" 时被当作正则
  const escaped = trimmed.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`(${escaped})`, "gi");
  const lower = trimmed.toLowerCase();
  const parts = text.split(re);
  return parts.map((part, i) =>
    part.toLowerCase() === lower ? <mark key={i}>{part}</mark> : <span key={i}>{part}</span>
  );
}

/** 截取答案前 N 字作为摘要。 */
function summarize(answer: string): string {
  const clean = answer.replace(/\s+/g, " ").trim();
  return clean.length > ANSWER_SUMMARY_LEN
    ? clean.slice(0, ANSWER_SUMMARY_LEN) + "…"
    : clean;
}

export function HistoryPanel({ onBack, onSelect }: HistoryPanelProps) {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [keyword, setKeyword] = useState("");

  // 时间筛选状态
  const [timePreset, setTimePreset] = useState<TimePreset>("all");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");

  // 计算当前筛选的 date_from/date_to
  const { date_from, date_to } = useMemo(
    () => presetToRange(timePreset, customFrom, customTo),
    [timePreset, customFrom, customTo]
  );

  // 时间范围变化时重新请求服务端
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const r = await api.history({
          limit: DEFAULT_LIMIT,
          date_from,
          date_to,
        });
        if (!cancelled) {
          setItems(r.items || []);
          setTotal(r.total ?? 0);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "加载历史失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [date_from, date_to]);

  // 客户端过滤：在 query + answer 中匹配关键词（大小写不敏感）
  const filtered = useMemo(() => {
    const k = keyword.trim().toLowerCase();
    if (!k) return items;
    return items.filter(
      (it) =>
        it.query.toLowerCase().includes(k) ||
        it.answer.toLowerCase().includes(k)
    );
  }, [items, keyword]);

  const showTotal = items.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-6 py-3 border-b bg-[color:var(--ink-50)] border-[color:var(--ink-200)]">
        <div className="flex items-baseline gap-3">
          <BauhausSectionLabel>HISTORY</BauhausSectionLabel>
          <h2 className="section-title text-base">问答历史</h2>
        </div>
        <div className="flex items-center gap-2">
          {showTotal && (
            <MetaText className="text-xs">
              共 {filtered.length} 条{total !== filtered.length ? ` / ${total}` : ""}
            </MetaText>
          )}
          {onBack && (
            <BauhausButton
              variant="outline"
              onClick={onBack}
              className="text-xs"
            >
              返回问答
            </BauhausButton>
          )}
        </div>
      </div>

      {/* 筛选栏：时间范围预设 + 关键词搜索 */}
      <div className="px-6 py-3 border-b bg-white border-[color:var(--ink-200)] space-y-3">
        {/* 时间范围预设按钮组 */}
        <div className="flex flex-wrap items-center gap-2">
          <label
            className="text-xs"
            style={{ color: "var(--ink-400)", fontFamily: "var(--font-ui)" }}
            htmlFor="history-time-preset"
          >
            时间
          </label>
          <div
            id="history-time-preset"
            role="group"
            aria-label="时间范围筛选"
            className="flex items-center gap-1"
          >
            {TIME_PRESETS.map((preset) => {
              const active = timePreset === preset.value;
              return (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => setTimePreset(preset.value)}
                  aria-pressed={active}
                  className="text-xs px-3 py-1 rounded-full border transition-all duration-150"
                  style={
                    active
                      ? {
                          background: "var(--ink-900)",
                          color: "#fff",
                          borderColor: "var(--ink-900)",
                        }
                      : {
                          background: "var(--ink-100)",
                          color: "var(--ink-600)",
                          borderColor: "var(--ink-200)",
                          cursor: "pointer",
                        }
                  }
                >
                  {preset.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 自定义日期范围（仅 custom 模式显示） */}
        {timePreset === "custom" && (
          <div className="flex flex-wrap items-center gap-2">
            <label
              className="text-xs"
              style={{ color: "var(--ink-400)", fontFamily: "var(--font-ui)" }}
              htmlFor="history-date-from"
            >
              起
            </label>
            <input
              id="history-date-from"
              type="date"
              className="input text-xs"
              aria-label="起始日期"
              value={customFrom}
              onChange={(e) => setCustomFrom(e.target.value)}
              style={{ minWidth: "140px" }}
            />
            <span
              className="text-xs"
              style={{ color: "var(--ink-400)", fontFamily: "var(--font-ui)" }}
            >
              至
            </span>
            <input
              id="history-date-to"
              type="date"
              className="input text-xs"
              aria-label="结束日期"
              value={customTo}
              onChange={(e) => setCustomTo(e.target.value)}
              style={{ minWidth: "140px" }}
            />
            {(customFrom || customTo) && (
              <button
                type="button"
                onClick={() => {
                  setCustomFrom("");
                  setCustomTo("");
                }}
                className="text-xs"
                style={{ color: "var(--ink-400)", fontFamily: "var(--font-ui)" }}
              >
                清空
              </button>
            )}
          </div>
        )}

        {/* 关键词搜索框 */}
        <input
          type="search"
          className="input text-sm"
          placeholder="搜索问题或答案关键词…"
          aria-label="历史搜索框"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
      </div>

      {/* 主体 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading ? (
          <SkeletonList count={4} />
        ) : error ? (
          <BauhausCard accent="ink" className="text-center">
            <BodyText className="text-sm" style={{ color: "var(--danger)" }}>
              {error}
            </BodyText>
          </BauhausCard>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-6">
            <BauhausSectionLabel className="mb-3">EMPTY</BauhausSectionLabel>
            <BauhausDisplay as="h3" className="mb-2 text-base">
              暂无问答历史
            </BauhausDisplay>
            <div
              className="mx-auto mb-4"
              style={{ width: 32, height: 3, background: "var(--ink-900)" }}
              aria-hidden="true"
            />
            <MetaText className="text-sm">
              {keyword.trim()
                ? "尝试更换搜索关键词"
                : timePreset !== "all"
                ? "当前时间范围内无历史记录"
                : "在问答面板提问后，历史记录会出现在这里"}
            </MetaText>
          </div>
        ) : (
          filtered.map((item, idx) => (
            <BauhausCard
              key={item.log_id}
              accent={idx % 2 === 0 ? "wine" : "ink"}
              title={
                <span style={{ fontFamily: "var(--font-serif)" }}>
                  {highlight(item.query, keyword)}
                </span>
              }
              meta={
                <span>
                  <MonoText>#{String(item.log_id).padStart(4, "0")}</MonoText>
                  {item.created_at && (
                    <>
                      <span className="mx-2">·</span>
                      <MonoText>
                        {new Date(item.created_at).toLocaleString("zh-CN")}
                      </MonoText>
                    </>
                  )}
                  {item.latency_ms !== undefined && (
                    <>
                      <span className="mx-2">·</span>
                      <MonoText>{item.latency_ms}ms</MonoText>
                    </>
                  )}
                  {item.model && (
                    <>
                      <span className="mx-2">·</span>
                      <MonoText>{item.model}</MonoText>
                    </>
                  )}
                  <span className="mx-2">·</span>
                  <MonoText>
                    引用 {item.citations?.length ?? 0}
                  </MonoText>
                </span>
              }
              onClick={onSelect ? () => onSelect(item) : undefined}
              className={onSelect ? "cursor-pointer hover:opacity-90 transition-opacity" : ""}
            >
              <BodyText className="text-sm">
                {highlight(summarize(item.answer), keyword)}
              </BodyText>
              {item.citations && item.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-[color:var(--ink-100)]">
                  <MetaText className="text-xs mb-1.5 block">引用来源</MetaText>
                  <ul className="space-y-1">
                    {item.citations.slice(0, 3).map((c, i) => (
                      <li
                        key={`${c.doc_id}-${c.chunk_rowid}-${i}`}
                        className="text-xs flex items-start gap-2"
                      >
                        <span
                          className="numeral flex-shrink-0"
                          style={{ color: "var(--amber)" }}
                        >
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span
                          style={{
                            color: "var(--ink-900)",
                            fontFamily: "var(--font-ui)",
                          }}
                        >
                          {c.title}
                        </span>
                      </li>
                    ))}
                    {item.citations.length > 3 && (
                      <li
                        className="text-xs"
                        style={{ color: "var(--ink-400)" }}
                      >
                        +{item.citations.length - 3} 条更多引用
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </BauhausCard>
          ))
        )}
      </div>
    </div>
  );
}
