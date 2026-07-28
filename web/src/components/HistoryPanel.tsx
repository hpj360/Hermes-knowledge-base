/**
 * HistoryPanel —— 问答历史列表 + 客户端关键词搜索
 *
 * 后端 /api/history 端点不支持搜索参数，因此搜索在前端对 query + answer 进行过滤。
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [keyword, setKeyword] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const r = await api.history(DEFAULT_LIMIT);
        if (!cancelled) setItems(r.items || []);
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
  }, []);

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

  return (
    <div className="flex flex-col h-full">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-6 py-3 border-b bg-[color:var(--ink-50)] border-[color:var(--ink-200)]">
        <div className="flex items-baseline gap-3">
          <BauhausSectionLabel>HISTORY</BauhausSectionLabel>
          <h2 className="section-title text-base">问答历史</h2>
        </div>
        <div className="flex items-center gap-2">
          {items.length > 0 && (
            <MetaText className="text-xs">共 {filtered.length} 条</MetaText>
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

      {/* 搜索框 */}
      <div className="px-6 py-3 border-b bg-white border-[color:var(--ink-200)]">
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
