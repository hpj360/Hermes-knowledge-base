import { useEffect, useState } from "react";
import { api } from "../api";
import type { CategoryInfo, DocumentItem, TagInfo } from "../types";
import { SkeletonList } from "./Skeleton";

interface DocumentListProps {
  refreshKey: number;
  onChange: () => void;
  onSelectDoc?: (docId: string) => void;
}

/** 文档列表（M2-06：分类+标签筛选）。 */
export function DocumentList({ refreshKey, onChange, onSelectDoc }: DocumentListProps) {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [tags, setTags] = useState<TagInfo[]>([]);
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [filterTagId, setFilterTagId] = useState<number | undefined>(undefined);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [docsResp, catsResp, tagsResp] = await Promise.all([
        api.listDocuments(filterCategory || undefined, filterTagId),
        api.listCategories(),
        api.listTags(),
      ]);
      setDocs(docsResp.items);
      setCategories(catsResp.items);
      setTags(tagsResp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshKey, filterCategory, filterTagId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDelete = async (docId: string, title: string) => {
    if (!confirm(`确认删除文档「${title}」？此操作不可恢复。`)) return;
    try {
      await api.deleteDocument(docId);
      await load();
      onChange();
    } catch (err) {
      alert(`删除失败：${err instanceof Error ? err.message : err}`);
    }
  };

  const clearFilters = () => {
    setFilterCategory("");
    setFilterTagId(undefined);
  };

  if (loading && docs.length === 0) {
    return <div className="p-4"><SkeletonList count={4} /></div>;
  }

  if (error) {
    return (
      <div
        className="p-4 text-center"
        style={{ color: "var(--danger)", fontFamily: "var(--font-sans)" }}
      >
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* 筛选栏 */}
      <div className="flex items-center gap-3 px-6 py-3 border-b bg-white flex-wrap" style={{ borderColor: "var(--ink-200)" }}>
        <span className="eyebrow">筛选</span>
        <select
          className="text-sm border rounded px-2 py-1 bg-white"
          style={{ borderColor: "var(--ink-200)", fontFamily: "var(--font-sans)" }}
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
        >
          <option value="">全部分类</option>
          {categories.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name} ({c.doc_count})
            </option>
          ))}
        </select>
        <select
          className="text-sm border rounded px-2 py-1 bg-white"
          style={{ borderColor: "var(--ink-200)", fontFamily: "var(--font-sans)" }}
          value={filterTagId ?? ""}
          onChange={(e) => setFilterTagId(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">全部标签</option>
          {tags.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} ({t.doc_count ?? 0})
            </option>
          ))}
        </select>
        {(filterCategory || filterTagId) && (
          <button
            onClick={clearFilters}
            className="btn-ghost text-xs"
          >
            清除
          </button>
        )}
        <span className="ml-auto text-xs" style={{ color: "var(--ink-400)" }}>共 {docs.length} 篇</span>
      </div>

      {/* 列表 */}
      {docs.length === 0 ? (
        <div className="p-16 text-center">
          <div className="text-3xl mb-3" style={{ color: "var(--gold-500)" }}>◆</div>
          <p className="eyebrow mb-2">EMPTY</p>
          <p className="section-title mb-2">{filterCategory || filterTagId ? "无匹配文档" : "知识库为空"}</p>
          <p className="text-sm" style={{ color: "var(--ink-400)", fontFamily: "var(--font-sans)" }}>
            {filterCategory || filterTagId ? "尝试更换筛选条件" : "点击右上角导入或种子知识"}
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          <div className="divide-y" style={{ borderColor: "var(--ink-200)" }}>
            {docs.map((d, i) => (
              <div key={d.doc_id} className="flex items-center gap-4 px-6 py-4 hover:bg-ink-50 transition-colors group">
                {/* 编号 */}
                <span className="numeral flex-shrink-0 w-8">{String(i + 1).padStart(2, "0")}</span>

                {/* 主信息 */}
                <div className="flex-1 min-w-0">
                  <button
                    onClick={() => onSelectDoc?.(d.doc_id)}
                    className="text-left block"
                    style={{ fontFamily: "var(--font-serif)", fontSize: "1rem", color: "var(--ink-900)", fontWeight: 600 }}
                  >
                    {d.title}
                  </button>
                  <div className="flex items-center gap-3 mt-1 text-xs" style={{ color: "var(--ink-400)", fontFamily: "var(--font-sans)" }}>
                    {d.category && <span>{d.category}</span>}
                    <span>·</span>
                    <span>{d.chunk_count} 片段</span>
                    <span>·</span>
                    <span>{d.source_type}</span>
                    {d.created_at && (
                      <>
                        <span>·</span>
                        <span>{new Date(d.created_at).toLocaleDateString()}</span>
                      </>
                    )}
                  </div>
                </div>

                {/* 标签 */}
                {(d.tags || []).length > 0 && (
                  <div className="flex gap-1 flex-shrink-0">
                    {d.tags.map((t) => (
                      <span key={t.id} className="text-xs px-2 py-0.5 rounded-full text-white" style={{ backgroundColor: t.color }}>
                        {t.name}
                      </span>
                    ))}
                  </div>
                )}

                {/* 操作 */}
                <div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  {onSelectDoc && (
                    <button onClick={() => onSelectDoc(d.doc_id)} className="btn-ghost text-xs">详情</button>
                  )}
                  <button onClick={() => handleDelete(d.doc_id, d.title)} className="btn-ghost text-xs" style={{ color: "var(--danger)" }}>删除</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
