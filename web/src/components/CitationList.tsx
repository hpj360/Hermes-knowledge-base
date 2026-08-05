import { useState } from "react";
import type { Citation } from "../types";
import { HeadingText, MetaText, MonoText } from "./ui";

interface CitationListProps {
  citations: Citation[];
  onJumpToDoc?: (docId: string, chunkRowid?: number) => void;
}

/**
 * 引用列表（M1-04：含 chunk_rowid；M2-04：点击跳转文档详情）。
 *
 * R2 重构：复用 _components.css 的 `.citation-list` / `.cite-title` / `.cite-item` /
 * `.cite-num` / `.cite-snippet` 语义类，承载金箔渐变边框 + 噪点底 + 戏剧化阴影 +
 * 金箔来源编号 + 杂志分栏标题。inline style 只保留动态 cursor 与 brand-700 颜色覆盖。
 *
 * UI 密度优化 Task 3.3：引用列表默认折叠，仅显示「N 条引用 + 来源标题摘要」，
 * 点击展开后显示完整列表（不影响 onJumpToDoc 跳转功能）。
 */
export function CitationList({ citations, onJumpToDoc }: CitationListProps) {
  // 默认折叠：仅展示「N 条引用 + 首条来源标题」摘要，点击展开后渲染完整列表
  const [expanded, setExpanded] = useState(false);

  if (!citations || citations.length === 0) {
    return (
      <MetaText className="text-xs italic mt-3">无引用</MetaText>
    );
  }

  return (
    <div className="citation-list mt-4">
      {!expanded ? (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          aria-label={`展开 ${citations.length} 条引用`}
          className="w-full flex flex-wrap items-center gap-1.5 text-left text-sm bauhaus-btn variant-outline"
          style={{
            cursor: "pointer",
            fontFamily: "var(--font-ui)",
          }}
        >
          <span style={{ color: "var(--gold-700)" }}>📚 {citations.length} 条引用 ·</span>
          {/* 来源标题摘要：首条标题单独成 span，便于测试 getByText 定位 */}
          <span style={{ color: "var(--ink-900)", fontWeight: 600 }}>
            {citations[0].title}
          </span>
          {citations.length > 1 && (
            <span style={{ color: "var(--ink-600)" }}>等 {citations.length} 条</span>
          )}
          <span style={{ color: "var(--gold-700)" }}>· 点击展开 ▸</span>
        </button>
      ) : (
        <>
          <button
            type="button"
            onClick={() => setExpanded(false)}
            aria-label="收起引用"
            className="w-full flex items-center gap-1.5 text-left text-sm mb-3 bauhaus-btn variant-outline"
            style={{
              cursor: "pointer",
              fontFamily: "var(--font-ui)",
            }}
          >
            <span style={{ color: "var(--gold-700)" }}>▾ 收起引用</span>
          </button>

          {/* 杂志式分栏标题：.cite-title 由 _components.css 提供 gold-700 大写 tracking + ::after 金线 */}
          <div className="cite-title">
            <span>来源溯源</span>
            <MonoText className="text-[0.7rem] font-medium ml-2">
              {citations.length}
            </MonoText>
          </div>

          <div className="space-y-2">
            {citations.map((c) => {
              const canJump = onJumpToDoc && c.doc_id;
              return (
                <div
                  key={`${c.doc_id}-${c.id}`}
                  className="citation-item"
                  onClick={() => canJump && onJumpToDoc!(c.doc_id, c.chunk_rowid || undefined)}
                  title={canJump ? "点击查看原文" : undefined}
                  // 动态 cursor：仅当可跳转时为 pointer（保留动态计算值）
                  style={{ cursor: canJump ? "pointer" : "default" }}
                >
                  {/* 金箔来源编号：.cite-num 由 _components.css 提供 serif + 金箔文字效果 */}
                  <span className="cite-num">[{c.id}]</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2 mb-1">
                      <HeadingText as="span" size="0.92rem" className="font-semibold truncate">
                        {c.title}
                      </HeadingText>
                      <MonoText className="text-[0.65rem] flex-shrink-0">
                        {c.score.toFixed(4)}
                      </MonoText>
                    </div>

                    <p className="cite-snippet leading-relaxed line-clamp-3">
                      {c.snippet}
                    </p>

                    <div className="flex items-center gap-2 mt-1.5">
                      <MonoText className="text-[0.62rem]">doc: {c.doc_id}</MonoText>
                      <span className="text-gold-300 text-[0.62rem]" aria-hidden="true">·</span>
                      <MonoText className="text-[0.62rem]">chunk: {c.chunk_rowid}</MonoText>
                      {canJump && (
                        <MetaText
                          as="span"
                          className="ml-auto font-medium text-[0.62rem]"
                          // 覆盖 MetaText 默认 ink-400，强调可点击动作
                          style={{ color: "var(--wine)" }}
                        >
                          查看原文 →
                        </MetaText>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
