import { useEffect, useState } from "react";
import { api } from "../api";
import type { DocumentDetail, LabRecipe } from "../types";

interface PendingReviewPanelProps {
  /** 外部传入的刷新信号：每次自增触发重新加载。 */
  refreshTick?: number;
  /** 审核结果回调（通过/驳回后通知父组件刷新列表）。 */
  onResolved?: () => void;
}

/** M4.3 待审核队列：列出 status=pending 的配方，支持单条通过/驳回 + 批量审核 + 配方详情预览。 */
export function PendingReviewPanel({ refreshTick, onResolved }: PendingReviewPanelProps) {
  const [items, setItems] = useState<LabRecipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyDocId, setBusyDocId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detailCache, setDetailCache] = useState<Record<string, DocumentDetail>>({});
  const [resolvedCount, setResolvedCount] = useState(0);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await api.labRecipes({ status: "pending", limit: 100 });
      setItems(resp.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshTick]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleSelect = (docId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) next.delete(docId);
      else next.add(docId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === items.length && items.length > 0) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((r) => r.doc_id)));
    }
  };

  const toggleExpand = async (docId: string) => {
    if (expanded === docId) {
      setExpanded(null);
      return;
    }
    setExpanded(docId);
    if (!detailCache[docId]) {
      try {
        const detail = await api.getDocument(docId);
        setDetailCache((prev) => ({ ...prev, [docId]: detail }));
      } catch {
        // 详情懒加载失败时静默 — 预览区不展示
      }
    }
  };

  const handleApprove = async (docId: string) => {
    setBusyDocId(docId);
    try {
      await api.labApproveRecipe(docId);
      setResolvedCount((c) => c + 1);
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(docId);
        return next;
      });
      await load();
      onResolved?.();
    } catch (err) {
      alert(`通过失败：${err instanceof Error ? err.message : err}`);
    } finally {
      setBusyDocId(null);
    }
  };

  const handleReject = async (docId: string) => {
    // 浏览器原生 prompt 与 mockup recipe-editor 行为一致；测试环境 jsdom 可 stubGlobal prompt。
    const reason = typeof window !== "undefined" && typeof window.prompt === "function"
      ? window.prompt("驳回理由：") || ""
      : "";
    setBusyDocId(docId);
    try {
      await api.labRejectRecipe(docId, reason);
      setResolvedCount((c) => c + 1);
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(docId);
        return next;
      });
      await load();
      onResolved?.();
    } catch (err) {
      alert(`驳回失败：${err instanceof Error ? err.message : err}`);
    } finally {
      setBusyDocId(null);
    }
  };

  const handleBatchApprove = async () => {
    if (selected.size === 0) return;
    setBusyDocId("__batch__");
    let ok = 0;
    let fail = 0;
    try {
      for (const docId of selected) {
        try {
          await api.labApproveRecipe(docId);
          ok++;
        } catch {
          fail++;
        }
      }
      setResolvedCount((c) => c + ok);
      setSelected(new Set());
      await load();
      onResolved?.();
      if (fail > 0) {
        alert(`批量通过完成：成功 ${ok}，失败 ${fail}`);
      }
    } finally {
      setBusyDocId(null);
    }
  };

  const handleBatchReject = async () => {
    if (selected.size === 0) return;
    setBusyDocId("__batch__");
    let ok = 0;
    let fail = 0;
    try {
      for (const docId of selected) {
        try {
          await api.labRejectRecipe(docId, "批量驳回");
          ok++;
        } catch {
          fail++;
        }
      }
      setResolvedCount((c) => c + ok);
      setSelected(new Set());
      await load();
      onResolved?.();
      if (fail > 0) {
        alert(`批量驳回完成：成功 ${ok}，失败 ${fail}`);
      }
    } finally {
      setBusyDocId(null);
    }
  };

  const allSelected = items.length > 0 && selected.size === items.length;
  const totalProcessed = items.length + resolvedCount;
  const progressPct = totalProcessed > 0 ? Math.round((resolvedCount / totalProcessed) * 100) : 0;

  return (
    <div className="card p-4 mb-4">
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="text-base font-semibold text-ink-900">📨 待审核配方</h3>
        <span className="text-xs text-gray-400">
          {loading ? "加载中…" : items.length > 0 ? `共 ${items.length} 条 UGC 投稿待审` : "当前无 UGC 投稿待审"}
        </span>
      </div>

      {/* 审核进度统计 */}
      {items.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
            <span>待审 {items.length} / 已处理 {resolvedCount}</span>
            <span>{progressPct}%</span>
          </div>
          <div className="w-full h-1.5 bg-ink-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gold-500 transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* 批量操作工具栏 */}
      {items.length > 0 && (
        <div className="flex items-center gap-3 mb-2 pb-2 border-b border-ink-100">
          <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleSelectAll}
            />
            全选
          </label>
          {selected.size > 0 && (
            <>
              <span className="text-xs text-gray-400">已选 {selected.size}</span>
              <button
                type="button"
                onClick={handleBatchApprove}
                disabled={busyDocId !== null}
                className="text-xs px-2 py-1 rounded bg-brand-700 text-white hover:opacity-90 disabled:opacity-50"
              >
                批量通过
              </button>
              <button
                type="button"
                onClick={handleBatchReject}
                disabled={busyDocId !== null}
                className="text-xs px-2 py-1 rounded border border-red-500 text-red-500 hover:bg-red-500 hover:text-white disabled:opacity-50"
              >
                批量驳回
              </button>
            </>
          )}
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 py-2">加载失败：{error}</div>
      )}

      {!loading && items.length === 0 && !error && (
        <div className="text-sm text-gray-400 py-4 text-center">暂无待审核配方</div>
      )}

      {items.length > 0 && (
        <ul className="divide-y divide-ink-100">
          {items.map((r) => {
            const detail = detailCache[r.doc_id];
            return (
              <li
                key={r.doc_id}
                className="py-2 flex items-center justify-between gap-3"
                data-doc-id={r.doc_id}
              >
                <input
                  type="checkbox"
                  checked={selected.has(r.doc_id)}
                  onChange={() => toggleSelect(r.doc_id)}
                  className="flex-shrink-0"
                  aria-label={`选择 ${r.title || r.doc_id}`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => toggleExpand(r.doc_id)}
                      className="font-medium text-sm text-ink-900 truncate text-left hover:text-brand-700"
                      title={r.title}
                    >
                      {r.title || "(未命名)"}
                    </button>
                    <span className="text-xs text-gray-400 flex-shrink-0">
                      {expanded === r.doc_id ? "▼" : "▶"}
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 truncate">
                    {r.doc_id}
                    {r.source ? ` · ${r.source}` : ""}
                  </div>
                  {expanded === r.doc_id && detail && (
                    <div className="mt-1 p-2 bg-ink-50 rounded text-xs text-gray-600 max-h-40 overflow-y-auto">
                      <div className="flex gap-3 mb-1 text-gray-500">
                        <span>来源：{detail.doc.source_type}</span>
                        {detail.doc.created_at && (
                          <span>创建：{detail.doc.created_at}</span>
                        )}
                      </div>
                      {detail.chunks.slice(0, 3).map((c) => (
                        <div key={c.rowid} className="mb-1 break-words">{c.text}</div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => handleApprove(r.doc_id)}
                    disabled={busyDocId === r.doc_id}
                    className="text-xs px-3 py-1 rounded bg-brand-700 text-white hover:opacity-90 disabled:opacity-50"
                  >
                    通过
                  </button>
                  <button
                    type="button"
                    onClick={() => handleReject(r.doc_id)}
                    disabled={busyDocId === r.doc_id}
                    className="text-xs px-3 py-1 rounded border border-red-500 text-red-500 hover:bg-red-500 hover:text-white disabled:opacity-50"
                  >
                    驳回
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
