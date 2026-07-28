import { useEffect, useState } from "react";
import { api } from "../api";
import type { CategoryInfo, DocumentItem, TagInfo } from "../types";
import { SkeletonList } from "./Skeleton";
import { showToast } from "./Toast";
import {
  useConfirm,
  MetaText,
  HeadingText,
  ErrorBanner,
  EmptyState,
  BauhausSectionLabel,
  BauhausButton,
} from "./ui";

interface DocumentListProps {
  refreshKey: number;
  onChange: () => void;
  onSelectDoc?: (docId: string) => void;
  onShowImport?: () => void;
}

/** 文档列表（M2-06：分类+标签筛选）。
 *
 * R2 重构：错误用 ErrorBanner、空状态用 EmptyState、筛选 select 用 `.select` 语义类、
 * 标题用 HeadingText、元信息用 MetaText。inline style 仅保留 tag 动态色板。
 */
export function DocumentList({ refreshKey, onChange, onSelectDoc, onShowImport }: DocumentListProps) {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [tags, setTags] = useState<TagInfo[]>([]);
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [filterTagId, setFilterTagId] = useState<number | undefined>(undefined);

  // R2: 替代 window.confirm 的异步确认对话框
  const { confirm, dialog: confirmDialog } = useConfirm();

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
    if (!(await confirm(`确认删除文档「${title}」？此操作不可恢复。`))) return;
    try {
      await api.deleteDocument(docId);
      await load();
      onChange();
    } catch (err) {
      showToast(`删除失败：${err instanceof Error ? err.message : err}`, "danger");
    }
  };

  const clearFilters = () => {
    setFilterCategory("");
    setFilterTagId(undefined);
  };

  if (loading && docs.length === 0) {
    return (
      <>
        <div className="p-4"><SkeletonList count={4} /></div>
        {confirmDialog}
      </>
    );
  }

  if (error) {
    return (
      <>
        <ErrorBanner className="p-4 text-center mb-0">{error}</ErrorBanner>
        {confirmDialog}
      </>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* 筛选栏 */}
      <div className="flex items-center gap-3 px-6 py-3 border-b bg-white flex-wrap border-ink-200">
        <BauhausSectionLabel>筛选</BauhausSectionLabel>
        <select
          className="select text-sm rounded px-2 py-1"
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
          className="select text-sm rounded px-2 py-1"
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
          <BauhausButton
            variant="outline"
            onClick={clearFilters}
            className="text-xs"
          >
            清除
          </BauhausButton>
        )}
        <MetaText className="ml-auto text-xs">共 {docs.length} 篇</MetaText>
        {onShowImport && (
          <BauhausButton variant="solid" onClick={onShowImport}>
            导入文档
          </BauhausButton>
        )}
      </div>

      {/* 列表 */}
      {docs.length === 0 ? (
        <EmptyState
          eyebrow="EMPTY"
          title={filterCategory || filterTagId ? "无匹配文档" : "知识库为空"}
          description={
            filterCategory || filterTagId
              ? "尝试更换筛选条件"
              : "点击右上角导入或种子知识"
          }
        />
      ) : (
        <div className="flex-1 overflow-y-auto">
          <div className="divide-y border-ink-200">
            {docs.map((d, i) => (
              <div key={d.doc_id} className="flex items-center gap-4 px-6 py-4 hover:bg-ink-50 transition-colors group">
                {/* 编号 */}
                <span className="numeral flex-shrink-0 w-8">{String(i + 1).padStart(2, "0")}</span>

                {/* 主信息 */}
                <div className="flex-1 min-w-0">
                  <HeadingText
                    as="button"
                    size="1rem"
                    onClick={() => onSelectDoc?.(d.doc_id)}
                    className="text-left block font-semibold bg-transparent border-0 p-0 cursor-pointer"
                  >
                    {d.title}
                  </HeadingText>
                  <MetaText as="div" className="flex items-center gap-3 mt-1 text-xs">
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
                  </MetaText>
                </div>

                {/* 标签 */}
                {(d.tags || []).length > 0 && (
                  <div className="flex gap-1 flex-shrink-0">
                    {d.tags.map((t) => (
                      <span
                        key={t.id}
                        className="text-xs px-2 py-0.5 rounded-full text-white"
                        // 动态色板：tag.color 由用户自定义，无法用静态 token 表达
                        style={{ backgroundColor: t.color }}
                      >
                        {t.name}
                      </span>
                    ))}
                  </div>
                )}

                {/* 操作 */}
                <div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  {onSelectDoc && (
                    <BauhausButton variant="outline" onClick={() => onSelectDoc(d.doc_id)} className="text-xs">详情</BauhausButton>
                  )}
                  <BauhausButton
                    variant="outline"
                    onClick={() => handleDelete(d.doc_id, d.title)}
                    className="text-xs text-[color:var(--danger)]"
                  >
                    删除
                  </BauhausButton>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* R2: useConfirm 对话框 */}
      {confirmDialog}
    </div>
  );
}
