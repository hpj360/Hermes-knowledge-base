import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { DocumentDetail, TagInfo } from "../types";
import { Skeleton, SkeletonText } from "./Skeleton";
import { showToast } from "./Toast";
import { BodyText, ErrorBanner, FormField, HeadingText, MetaText, MonoText } from "./ui";

interface DocumentDetailPanelProps {
  docId: string;
  highlightChunk?: number;
  onBack: () => void;
  onChange: () => void;
}

/** M2-03 文档详情面板：左侧目录 + 右侧全文 + chunk 高亮。 */
export function DocumentDetailPanel({
  docId,
  highlightChunk,
  onBack,
  onChange,
}: DocumentDetailPanelProps) {
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editTagIds, setEditTagIds] = useState<number[]>([]);
  const [allTags, setAllTags] = useState<TagInfo[]>([]);
  const [saving, setSaving] = useState(false);
  const chunkRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const d = await api.getDocument(docId);
      setDetail(d);
      setEditTitle(d.doc.title);
      setEditCategory(d.doc.category);
      setEditTagIds(d.tags.map((t) => t.id).filter(Boolean) as number[]);
      const tagsResp = await api.listTags();
      setAllTags(tagsResp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [docId]); // eslint-disable-line react-hooks/exhaustive-deps

  // M2-04：高亮 chunk 自动滚动
  useEffect(() => {
    if (!detail || highlightChunk === undefined) return;
    const t = setTimeout(() => {
      const el = chunkRefs.current[highlightChunk];
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("ring-4", "ring-brand-200", "bg-brand-50");
        setTimeout(() => {
          el.classList.remove("ring-4", "ring-brand-200", "bg-brand-50");
        }, 2000);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [detail, highlightChunk]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateDocMetadata(docId, {
        title: editTitle,
        category: editCategory,
        tag_ids: editTagIds,
      });
      setEditing(false);
      await load();
      onChange();
    } catch (err) {
      showToast(`保存失败：${err instanceof Error ? err.message : err}`, "danger");
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async () => {
    try {
      await api.downloadDocumentRaw(docId);
    } catch (err) {
      showToast(`下载失败：${err instanceof Error ? err.message : err}`, "danger");
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-3xl mx-auto">
        <Skeleton height="1.75rem" width="50%" className="mb-6" />
        <SkeletonText lines={8} lastLineRatio={0.7} />
      </div>
    );
  }
  if (error) {
    return (
      <div className="p-8 text-center">
        <ErrorBanner>{error}</ErrorBanner>
        <button onClick={onBack} className="btn-secondary">返回</button>
      </div>
    );
  }
  if (!detail) return null;

  const { doc, chunks } = detail;

  return (
    <div className="flex flex-col h-full">
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between px-6 py-3 border-b bg-white border-[color:var(--ink-200)]">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-sm text-[color:var(--ink-600)] font-[family-name:var(--font-ui)]"
          >
            <span>←</span>
            <span>返回列表</span>
          </button>
          <span className="eyebrow">文档详情</span>
        </div>
        <div className="flex gap-2">
          <button onClick={handleDownload} className="btn-secondary text-sm">下载</button>
          <button onClick={() => setEditing(!editing)} className="btn-secondary text-sm">{editing ? "取消" : "编辑"}</button>
        </div>
      </div>

      {/* 编辑区 */}
      {editing && (
        <div className="px-6 py-4 bg-white border-b space-y-3 border-[color:var(--ink-200)]">
          <p className="eyebrow">编辑元信息</p>
          <FormField label="标题">
            <input
              className="input mt-1"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              disabled={saving}
            />
          </FormField>
          <FormField label="分类">
            <input
              className="input mt-1"
              value={editCategory}
              onChange={(e) => setEditCategory(e.target.value)}
              placeholder="如：烈酒 / 葡萄酒 / 中国白酒"
              disabled={saving}
            />
          </FormField>
          <FormField label="标签（多选）">
            <div className="flex flex-wrap gap-2 mt-1">
              {allTags.length === 0 && (
                <MetaText className="text-xs">暂无标签，请先在标签管理创建</MetaText>
              )}
              {allTags.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => {
                    if (editTagIds.includes(t.id)) {
                      setEditTagIds(editTagIds.filter((x) => x !== t.id));
                    } else {
                      setEditTagIds([...editTagIds, t.id]);
                    }
                  }}
                  className="text-xs px-2 py-1 rounded border transition-colors font-[family-name:var(--font-ui)]"
                  style={
                    editTagIds.includes(t.id)
                      ? { background: "var(--brand-700)", color: "#fff", borderColor: "var(--brand-700)" }
                      : { background: "#fff", color: "var(--ink-600)", borderColor: t.color || "var(--ink-200)" }
                  }
                >
                  {t.name}
                </button>
              ))}
            </div>
          </FormField>
          <button
            onClick={handleSave}
            className="btn-primary text-sm"
            disabled={saving || !editTitle.trim()}
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      )}

      {/* 主体：左目录 + 右全文 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：元信息 + chunk 目录 */}
        <aside className="w-64 border-r bg-white overflow-y-auto p-6 flex-shrink-0 border-[color:var(--ink-200)]">
          <p className="eyebrow mb-3">文档信息</p>
          <HeadingText as="h2" size="1.125rem" className="font-bold mb-4 break-all">
            {doc.title}
          </HeadingText>
          <dl className="text-xs space-y-2 text-[color:var(--ink-600)] font-[family-name:var(--font-ui)]">
            <div><MetaText as="dt" className="font-medium">类型</MetaText><dd>{doc.file_type.toUpperCase()}</dd></div>
            <div><MetaText as="dt" className="font-medium">来源</MetaText><dd>{doc.source_type}</dd></div>
            <div><MetaText as="dt" className="font-medium">分类</MetaText><dd>{doc.category || "未分类"}</dd></div>
            <div><MetaText as="dt" className="font-medium">分片</MetaText><dd>{doc.chunk_count}</dd></div>
            <div><MetaText as="dt" className="font-medium">字符</MetaText><dd>{doc.content_length}</dd></div>
          </dl>
          {detail.tags.length > 0 && (
            <div className="mt-4">
              <p className="eyebrow mb-2">标签</p>
              <div className="flex flex-wrap gap-1">
                {detail.tags.map((t) => (
                  <span
                    key={t.id}
                    className="text-xs px-2 py-0.5 rounded-full text-white"
                    style={{ backgroundColor: t.color }}
                  >
                    {t.name}
                  </span>
                ))}
              </div>
            </div>
          )}
          {chunks.length > 0 && (
            <div className="mt-6">
              <p className="eyebrow mb-2">目录</p>
              <ol className="space-y-1.5">
                {chunks.map((c) => (
                  <li key={c.rowid}>
                    <a
                      href={`#chunk-${c.rowid}`}
                      onClick={(e) => {
                        e.preventDefault();
                        const el = chunkRefs.current[c.rowid];
                        el?.scrollIntoView({ behavior: "smooth", block: "center" });
                      }}
                      className="block text-xs truncate text-[color:var(--brand-700)] font-[family-name:var(--font-ui)]"
                      title={c.text.slice(0, 60)}
                    >
                      <span className="numeral mr-2">{String(c.idx + 1).padStart(2, "0")}</span>
                      {c.text.slice(0, 30)}...
                    </a>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </aside>

        {/* 右侧：全文（按 chunk 渲染，带 rowid 锚点） */}
        <main className="flex-1 overflow-y-auto p-6">
          {chunks.length === 0 ? (
            <MetaText as="div" className="text-center mt-12">
              此文档无分片内容（可能为空文档）
            </MetaText>
          ) : (
            <div className="space-y-4 max-w-3xl">
              {chunks.map((c) => (
                <div
                  key={c.rowid}
                  id={`chunk-${c.rowid}`}
                  ref={(el) => { chunkRefs.current[c.rowid] = el; }}
                  className="card p-5 transition-all duration-300"
                >
                  <div className="flex items-center justify-between mb-3 pb-2 border-b border-[color:var(--ink-100)]">
                    <span className="numeral">片段 {String(c.idx + 1).padStart(2, "0")}</span>
                    <MonoText className="text-xs">chars {c.char_start}-{c.char_end}</MonoText>
                  </div>
                  <BodyText as="div" className="whitespace-pre-wrap leading-relaxed text-[length:0.95rem]">
                    {c.text}
                  </BodyText>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
