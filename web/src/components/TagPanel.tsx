import { useEffect, useState } from "react";
import { api } from "../api";
import type { TagInfo } from "../types";
import { SkeletonList } from "./Skeleton";

interface TagPanelProps {
  onChange: () => void;
}

const PRESET_COLORS = [
  "#6b7280", "#ef4444", "#f97316", "#eab308",
  "#22c55e", "#06b6d4", "#3b82f6", "#8b5cf6",
  "#ec4899", "#78716c",
];

/** M2-06 标签管理面板。 */
export function TagPanel({ onChange }: TagPanelProps) {
  const [tags, setTags] = useState<TagInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [color, setColor] = useState(PRESET_COLORS[0]);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const resp = await api.listTags();
      setTags(resp.items);
    } catch (err) {
      console.error("加载标签失败", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await api.createTag(name.trim(), color);
      setName("");
      setColor(PRESET_COLORS[0]);
      await load();
      onChange();
    } catch (err) {
      alert(err instanceof Error ? err.message : "创建失败");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (tag: TagInfo) => {
    if (!confirm(`确认删除标签「${tag.name}」？此操作会从所有文档中移除该标签。`)) return;
    try {
      await api.deleteTag(tag.id);
      await load();
      onChange();
    } catch (err) {
      alert(err instanceof Error ? err.message : "删除失败");
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <p className="eyebrow mb-2">TAGS</p>
        <h2 className="display-title">标签管理</h2>
        <hr className="divider-gold w-24 mt-4" />
      </div>

      {/* 创建 */}
      <div className="card mb-8 p-6">
        <p className="eyebrow mb-4">创建新标签</p>
        <div className="flex items-center gap-3 flex-wrap">
          <input className="input flex-1 min-w-[160px]" placeholder="标签名" value={name} onChange={(e) => setName(e.target.value)} maxLength={32} disabled={creating} />
          <div className="flex items-center gap-1">
            <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="w-8 h-8 rounded cursor-pointer border" style={{ borderColor: "var(--ink-200)" }} disabled={creating} />
            <div className="flex gap-1 ml-2">
              {PRESET_COLORS.map((c) => (
                <button key={c} onClick={() => setColor(c)} className={`w-5 h-5 rounded-full border-2 ${color === c ? "border-ink-900" : "border-transparent"}`} style={{ backgroundColor: c }} aria-label={`颜色 ${c}`} />
              ))}
            </div>
          </div>
          <button onClick={handleCreate} className="btn-primary text-sm" disabled={creating || !name.trim()}>
            {creating ? "创建中..." : "创建"}
          </button>
        </div>
      </div>

      {/* 列表 */}
      <div className="card">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--ink-200)" }}>
          <p className="eyebrow">已有标签</p>
          <span className="text-xs" style={{ color: "var(--ink-400)" }}>{tags.length} 个</span>
        </div>
        {loading ? (
          <div className="p-5"><SkeletonList count={3} /></div>
        ) : tags.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-2xl mb-2" style={{ color: "var(--gold-500)" }}>◆</div>
            <p className="text-sm" style={{ color: "var(--ink-400)", fontFamily: "var(--font-sans)" }}>暂无标签，请在上方创建</p>
          </div>
        ) : (
          <ul className="divide-y" style={{ borderColor: "var(--ink-100)" }}>
            {tags.map((t, i) => (
              <li key={t.id} className="flex items-center justify-between px-5 py-3 group">
                <div className="flex items-center gap-3">
                  <span className="numeral">{String(i + 1).padStart(2, "0")}</span>
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: t.color }} />
                  <span className="font-medium" style={{ fontFamily: "var(--font-serif)", color: "var(--ink-900)" }}>{t.name}</span>
                  <span className="text-xs" style={{ color: "var(--ink-400)", fontFamily: "var(--font-sans)" }}>关联 {t.doc_count ?? 0} 篇</span>
                </div>
                <button onClick={() => handleDelete(t)} className="btn-ghost text-xs opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: "var(--danger)" }}>删除</button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-6 px-4 py-3 text-xs" style={{ background: "var(--ink-50)", borderLeft: "3px solid var(--gold-500)", color: "var(--ink-600)", fontFamily: "var(--font-sans)" }}>
        提示：标签为多选（一篇文档可有多个标签），分类为单选。在文档详情页可为文档设置标签。
      </div>
    </div>
  );
}
