import { useEffect, useState } from "react";
import { api } from "../api";
import type { RecipeRatingSummary } from "../types";
import { showToast } from "./Toast";
import {
  BauhausButton,
  BauhausChip,
  BauhausSectionLabel,
  EmptyState,
  ErrorBanner,
  MetaText,
} from "./ui";

interface RecipeRatingPanelProps {
  docId: string;
  /** 可选变更回调，外部可用于刷新列表 */
  onChanged?: () => void;
}

/**
 * V2-Task6：配方评分与调酒笔记面板。
 *
 * - 顶部展示平均分 / 评分人数 / 笔记数
 * - 中间是评分输入区：5 颗星 + 笔记 textarea + 提交按钮
 * - 底部展示笔记列表（comment 非空，按 updated_at 倒序，最多 50 条）
 *
 * UPSERT 语义：同一用户对同一配方仅保留一条记录，重复提交触发更新。
 */
export function RecipeRatingPanel({ docId, onChanged }: RecipeRatingPanelProps) {
  const [summary, setSummary] = useState<RecipeRatingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hoverScore, setHoverScore] = useState(0);
  const [score, setScore] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const s = await api.labGetRating(docId);
      setSummary(s);
      // 回填当前用户评分到输入区
      if (s.current_user_rating) {
        setScore(s.current_user_rating.score);
        setComment(s.current_user_rating.comment);
      } else {
        setScore(0);
        setComment("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [docId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = async () => {
    if (score === 0 && !comment.trim()) {
      showToast("请选择评分或填写笔记", "danger");
      return;
    }
    setSubmitting(true);
    try {
      const result = await api.labRateRecipe(docId, {
        score: score > 0 ? score : undefined,
        comment: comment.trim() || undefined,
      });
      showToast(
        result.status === "created" ? "评分已提交" : "评分已更新",
        "success"
      );
      await load();
      onChanged?.();
    } catch (err) {
      showToast(`提交失败：${err instanceof Error ? err.message : err}`, "danger");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-4">
        <MetaText className="text-xs">加载评分中…</MetaText>
      </div>
    );
  }
  if (error) {
    return (
      <div className="p-4">
        <ErrorBanner>{error}</ErrorBanner>
      </div>
    );
  }
  if (!summary) return null;

  return (
    <div
      className="bauhaus-card accent-amber p-4 mt-4"
      data-testid="recipe-rating-panel"
    >
      {/* 标题 */}
      <BauhausSectionLabel className="mb-3">RATING & NOTES</BauhausSectionLabel>

      {/* 评分摘要 */}
      <div className="flex items-baseline gap-4 mb-4 flex-wrap">
        <div className="flex items-baseline gap-2">
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "2rem",
              fontWeight: 700,
              color: "var(--amber)",
              lineHeight: 1,
            }}
            data-testid="rating-average"
          >
            {summary.average_score.toFixed(1)}
          </span>
          <MetaText className="text-xs">/ 5.0</MetaText>
        </div>
        <BauhausChip variant="outline">
          {summary.rating_count} 人评分
        </BauhausChip>
        <BauhausChip variant="outline">
          {summary.note_count} 条笔记
        </BauhausChip>
      </div>

      {/* 评分输入区 */}
      <div
        className="mb-4 p-3"
        style={{
          background: "var(--paper)",
          border: "1px solid var(--ink-100)",
          borderRadius: "var(--r-sm)",
        }}
      >
        <MetaText as="div" className="text-xs mb-2">
          我的评分（点击星星，0 星 = 仅笔记）
        </MetaText>
        <div
          className="flex gap-1 mb-3"
          role="radiogroup"
          aria-label="评分"
          data-testid="rating-stars"
        >
          {[1, 2, 3, 4, 5].map((s) => {
            const active = (hoverScore || score) >= s;
            return (
              <button
                key={s}
                type="button"
                role="radio"
                aria-checked={score === s}
                aria-label={`${s} 星`}
                onClick={() => setScore(s)}
                onMouseEnter={() => setHoverScore(s)}
                onMouseLeave={() => setHoverScore(0)}
                className="transition-transform"
                style={{
                  fontSize: "1.5rem",
                  color: active ? "var(--amber)" : "var(--ink-200)",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  padding: "0 2px",
                  lineHeight: 1,
                }}
              >
                {active ? "★" : "☆"}
              </button>
            );
          })}
          {score > 0 && (
            <button
              type="button"
              onClick={() => setScore(0)}
              className="ml-2 text-xs"
              style={{
                color: "var(--ink-400)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                textDecoration: "underline",
              }}
              aria-label="清除评分"
            >
              清除
            </button>
          )}
        </div>
        <textarea
          className="input w-full"
          rows={3}
          placeholder="调酒笔记：替代材料、口感调整、心得…"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          maxLength={2000}
          disabled={submitting}
          aria-label="调酒笔记"
          data-testid="rating-comment"
        />
        <div className="flex justify-between items-center mt-2">
          <MetaText className="text-xs">
            {comment.length}/2000
          </MetaText>
          <BauhausButton
            variant="solid"
            onClick={handleSubmit}
            disabled={submitting || (score === 0 && !comment.trim())}
            data-testid="rating-submit"
          >
            {submitting ? "提交中…" : "提交"}
          </BauhausButton>
        </div>
      </div>

      {/* 笔记列表 */}
      <BauhausSectionLabel className="mb-2">最近笔记</BauhausSectionLabel>
      {summary.notes.length === 0 ? (
        <EmptyState
          title="暂无笔记"
          description="第一个写下你的调酒心得吧"
        />
      ) : (
        <ul className="space-y-2" data-testid="rating-notes">
          {summary.notes.map((note, idx) => (
            <li
              key={`${note.user}-${note.updated_at || idx}`}
              className="p-2 text-sm"
              style={{
                background: "var(--paper)",
                borderLeft: "3px solid var(--amber)",
                borderRadius: "var(--r-sm)",
              }}
            >
              <div className="flex items-baseline justify-between gap-2 mb-1">
                <div className="flex items-baseline gap-2">
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.85rem",
                      fontWeight: 600,
                      color: "var(--ink-900)",
                    }}
                  >
                    {note.user}
                  </span>
                  {note.score > 0 && (
                    <span
                      style={{
                        color: "var(--amber)",
                        fontSize: "0.85rem",
                      }}
                      aria-label={`${note.score} 星`}
                    >
                      {"★".repeat(note.score)}
                      <span style={{ color: "var(--ink-200)" }}>
                        {"★".repeat(5 - note.score)}
                      </span>
                    </span>
                  )}
                </div>
                {note.updated_at && (
                  <MetaText className="text-xs">
                    {new Date(note.updated_at).toLocaleDateString("zh-CN")}
                  </MetaText>
                )}
              </div>
              {note.comment && (
                <div
                  style={{
                    color: "var(--ink-900)",
                    fontFamily: "var(--font-body)",
                    fontSize: "0.9rem",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {note.comment}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
