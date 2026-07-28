import { useEffect, useState } from "react";
import { api } from "../api";
import type { TagInfo } from "../types";
import { SkeletonList } from "./Skeleton";
import { showToast } from "./Toast";
import { useConfirm, MetaText, BauhausSectionLabel, BauhausDisplay, BauhausCard, BauhausButton } from "./ui";

interface TagPanelProps {
  onChange: () => void;
}

// 功能性色板：传给 input[type=color] 与预设色块按钮，非视觉装饰，保留 hex 字面量
const PRESET_COLORS = [
  "#6b7280", "#ef4444", "#f97316", "#eab308",
  "#22c55e", "#06b6d4", "#3b82f6", "#8b5cf6",
  "#ec4899", "#78716c",
];

/** M2-06 标签管理面板。
 *
 * R2 重构：元信息用 MetaText、计数用 MetaText、提示框用 Tailwind 工具类 + token。
 * inline style 仅保留两处动态色板：PRESET_COLORS 色块与 tag.color 色点。
 */
export function TagPanel({ onChange }: TagPanelProps) {
  const [tags, setTags] = useState<TagInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [color, setColor] = useState(PRESET_COLORS[0]);
  const [creating, setCreating] = useState(false);

  // R2: 替代 window.confirm 的异步确认对话框
  const { confirm, dialog: confirmDialog } = useConfirm();

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
      showToast(err instanceof Error ? err.message : "创建失败", "danger");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (tag: TagInfo) => {
    if (!(await confirm(`确认删除标签「${tag.name}」？此操作会从所有文档中移除该标签。`))) return;
    try {
      await api.deleteTag(tag.id);
      await load();
      onChange();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "删除失败", "danger");
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <BauhausSectionLabel className="mb-2">TAGS</BauhausSectionLabel>
        <BauhausDisplay as="h2">标签管理</BauhausDisplay>
        <hr className="divider-gold w-24 mt-4" />
      </div>

      {/* 创建 */}
      <BauhausCard className="mb-8 p-6">
        <BauhausSectionLabel className="mb-4">创建新标签</BauhausSectionLabel>
        <div className="flex items-center gap-3 flex-wrap">
          <input className="input flex-1 min-w-[160px]" placeholder="标签名" value={name} onChange={(e) => setName(e.target.value)} maxLength={32} disabled={creating} />
          <div className="flex items-center gap-1">
            <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="w-8 h-8 rounded cursor-pointer border border-ink-200" disabled={creating} />
            <div className="flex gap-1 ml-2">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className={`w-5 h-5 rounded-full border-2 ${color === c ? "border-ink-900" : "border-transparent"}`}
                  // 功能性色板：PRESET_COLORS hex 传给色块按钮，保留
                  style={{ backgroundColor: c }}
                  aria-label={`颜色 ${c}`}
                />
              ))}
            </div>
          </div>
          <BauhausButton variant="solid" onClick={handleCreate} className="text-sm" disabled={creating || !name.trim()}>
            {creating ? "创建中..." : "创建"}
          </BauhausButton>
        </div>
      </BauhausCard>

      {/* 列表 */}
      <BauhausCard>
        <div className="flex items-center justify-between p-5 border-b border-ink-200">
          <BauhausSectionLabel>已有标签</BauhausSectionLabel>
          <MetaText className="text-xs">{tags.length} 个</MetaText>
        </div>
        {loading ? (
          <div className="p-5"><SkeletonList count={3} /></div>
        ) : tags.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-2xl mb-2 text-gold-500">◆</div>
            <MetaText className="text-sm">暂无标签，请在上方创建</MetaText>
          </div>
        ) : (
          <ul className="divide-y border-ink-100">
            {tags.map((t, i) => (
              <li key={t.id} className="flex items-center justify-between px-5 py-3 group">
                <div className="flex items-center gap-3">
                  <span className="numeral">{String(i + 1).padStart(2, "0")}</span>
                  <span
                    className="w-3 h-3 rounded-full"
                    // 动态色板：tag.color 由用户自定义，无法用静态 token 表达
                    style={{ backgroundColor: t.color }}
                  />
                  <span className="font-serif text-ink-900 font-medium">{t.name}</span>
                  <MetaText className="text-xs">关联 {t.doc_count ?? 0} 篇</MetaText>
                </div>
                <BauhausButton
                  variant="outline"
                  onClick={() => handleDelete(t)}
                  className="text-xs text-[color:var(--danger)] opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  删除
                </BauhausButton>
              </li>
            ))}
          </ul>
        )}
      </BauhausCard>

      <div className="mt-6 px-4 py-3 text-xs bg-ink-50 border-l-[3px] border-gold-500 text-ink-600 font-ui">
        提示：标签为多选（一篇文档可有多个标签），分类为单选。在文档详情页可为文档设置标签。
      </div>

      {/* R2: useConfirm 对话框 */}
      {confirmDialog}
    </div>
  );
}
