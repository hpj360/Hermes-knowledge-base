import { useState } from "react";
import { api } from "../api";
import type { BatchImportResult } from "../types";
import { Modal } from "./Modal";
import { BauhausButton, ErrorBanner, FormField, MetaText } from "./ui";

interface ImportDialogProps {
  onClose: () => void;
  onImported: () => void;
}

/** 导入对话框：纯文本 / 单文件 / 批量上传（M2-05）。
 * critical 修复：复用 Modal 组件（.modal-overlay + .modal），不再自写 inline overlay。
 */
export function ImportDialog({ onClose, onImported }: ImportDialogProps) {
  const [tab, setTab] = useState<"text" | "file" | "batch">("text");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileTitle, setFileTitle] = useState("");
  const [batchFiles, setBatchFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [batchResult, setBatchResult] = useState<BatchImportResult | null>(null);

  const handleImportText = async () => {
    if (!title.trim() || !content.trim()) {
      setError("标题和内容不能为空");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await api.importText(title.trim(), content, category.trim() || undefined);
      onImported();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("请选择文件");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await api.uploadFile(file, fileTitle.trim() || undefined);
      onImported();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setLoading(false);
    }
  };

  const handleBatchUpload = async () => {
    if (batchFiles.length === 0) {
      setError("请至少选择 1 个文件");
      return;
    }
    if (batchFiles.length > 20) {
      setError(`单次最多 20 个文件，当前 ${batchFiles.length} 个`);
      return;
    }
    setLoading(true);
    setError("");
    setBatchResult(null);
    try {
      const result = await api.uploadBatch(batchFiles);
      setBatchResult(result);
      if (result.imported > 0) {
        onImported();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "批量上传失败");
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    const valid = files.filter((f) => /\.(txt|md|pdf)$/i.test(f.name));
    if (valid.length === 0) {
      setError("仅支持 .txt / .md / .pdf 文件");
      return;
    }
    setBatchFiles((prev) => [...prev, ...valid].slice(0, 20));
    setError("");
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setBatchFiles((prev) => [...prev, ...files].slice(0, 20));
  };

  return (
    <Modal open={true} onClose={onClose} title="导入文档" maxWidth={672}>
      {/* tab 导航 */}
      <div className="flex gap-1 border-b border-[color:var(--ink-200)] mb-4">
        <button
          className={`nav-tab ${tab === "text" ? "nav-tab-active" : ""}`}
          onClick={() => setTab("text")}
        >
          纯文本
        </button>
        <button
          className={`nav-tab ${tab === "file" ? "nav-tab-active" : ""}`}
          onClick={() => setTab("file")}
        >
          单文件
        </button>
        <button
          className={`nav-tab ${tab === "batch" ? "nav-tab-active" : ""}`}
          onClick={() => setTab("batch")}
        >
          批量上传 (≤20)
        </button>
      </div>

      {error && (
        <ErrorBanner className="text-sm rounded px-3 py-2 mb-3">
          {error}
        </ErrorBanner>
      )}

      {tab === "text" ? (
        <div className="space-y-3">
          <FormField label="标题 *">
            <input
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="文档标题"
              disabled={loading}
            />
          </FormField>
          <FormField label="分类（可选）">
            <input
              className="input"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="如：烈酒 / 葡萄酒 / 中国白酒"
              disabled={loading}
            />
          </FormField>
          <FormField label="内容 *">
            <textarea
              className="input resize-y"
              rows={10}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="粘贴文档内容..."
              disabled={loading}
            />
            <MetaText className="text-xs mt-1">
              支持 Markdown 语法，将自动分片（500 字符/片，80 字符重叠）
            </MetaText>
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <BauhausButton variant="outline" onClick={onClose} disabled={loading}>
              取消
            </BauhausButton>
            <BauhausButton
              variant="solid"
              onClick={handleImportText}
              disabled={loading}
            >
              {loading ? "导入中..." : "导入"}
            </BauhausButton>
          </div>
        </div>
      ) : tab === "file" ? (
        <div className="space-y-3">
          <FormField label="文件 *">
            <input
              type="file"
              accept=".txt,.md,.pdf"
              className="mt-1 block w-full text-sm text-[color:var(--ink-600)] font-[family-name:var(--font-ui)]"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              disabled={loading}
            />
            <MetaText className="text-xs mt-1">支持 .txt / .md / .pdf</MetaText>
          </FormField>
          <FormField label="标题（可选）">
            <input
              className="input"
              value={fileTitle}
              onChange={(e) => setFileTitle(e.target.value)}
              placeholder="留空使用文件名"
              disabled={loading}
            />
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <BauhausButton variant="outline" onClick={onClose} disabled={loading}>
              取消
            </BauhausButton>
            <BauhausButton
              variant="solid"
              onClick={handleUpload}
              disabled={loading || !file}
            >
              {loading ? "上传中..." : "上传"}
            </BauhausButton>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* 拖拽区 — dragOver 两态用条件 className，避免 inline style */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded p-6 text-center transition-colors ${
              dragOver
                ? "border-[color:var(--gold-500)] bg-[color:var(--gold-100)]"
                : "border-[color:var(--ink-200)]"
            }`}
          >
            <div className="text-3xl mb-2 text-[color:var(--gold-500)]">📁</div>
            <p className="text-sm text-[color:var(--ink-600)] font-[family-name:var(--font-ui)]">
              拖拽文件到此处
            </p>
            <MetaText className="text-xs my-1">或</MetaText>
            <label className="bauhaus-btn variant-outline text-sm cursor-pointer">
              选择文件
              <input
                type="file"
                multiple
                accept=".txt,.md,.pdf"
                className="hidden"
                onChange={handleFileInput}
                disabled={loading}
              />
            </label>
            <MetaText className="text-xs mt-2">
              支持 .txt / .md / .pdf，单次最多 20 个
            </MetaText>
          </div>

          {/* 已选文件列表 */}
          {batchFiles.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <MetaText className="text-xs">
                  已选 {batchFiles.length} 个文件
                </MetaText>
                <button
                  onClick={() => setBatchFiles([])}
                  className="text-xs transition-colors text-[color:var(--ink-400)] hover:text-[color:var(--danger)]"
                  disabled={loading}
                >
                  清空
                </button>
              </div>
              <ul className="max-h-40 overflow-y-auto border rounded divide-y border-[color:var(--ink-200)] divide-[color:var(--ink-100)]">
                {batchFiles.map((f, i) => (
                  <li
                    key={`${f.name}-${i}`}
                    className="flex items-center justify-between px-2 py-1 text-xs font-[family-name:var(--font-ui)] text-[color:var(--ink-900)]"
                  >
                    <span className="truncate">{f.name}</span>
                    <MetaText className="ml-2">
                      {(f.size / 1024).toFixed(1)} KB
                    </MetaText>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 批量结果 — 每项 status 颜色用条件 className */}
          {batchResult && (
            <div className="border rounded p-3 text-sm bg-[color:var(--ink-50)] border-[color:var(--ink-200)] font-[family-name:var(--font-ui)]">
              <div className="font-medium mb-2 text-[color:var(--ink-900)]">
                导入完成：{batchResult.imported}/{batchResult.total} 成功
                {batchResult.failed > 0 && (
                  <span className="text-[color:var(--danger)]">
                    （{batchResult.failed} 失败）
                  </span>
                )}
              </div>
              <ul className="space-y-1 max-h-40 overflow-y-auto">
                {batchResult.results.map((r, i) => (
                  <li
                    key={i}
                    className={`text-xs ${
                      r.status === "imported"
                        ? "text-[color:var(--success)]"
                        : "text-[color:var(--danger)]"
                    }`}
                  >
                    {r.status === "imported" ? "✓" : "✗"} {r.filename}
                    {r.error && ` - ${r.error}`}
                    {r.chunk_count !== undefined && ` (${r.chunk_count} 分片)`}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <BauhausButton variant="outline" onClick={onClose} disabled={loading}>
              关闭
            </BauhausButton>
            <BauhausButton
              variant="solid"
              onClick={handleBatchUpload}
              disabled={loading || batchFiles.length === 0}
            >
              {loading ? `上传中...` : `上传 ${batchFiles.length} 个文件`}
            </BauhausButton>
          </div>
        </div>
      )}
    </Modal>
  );
}
