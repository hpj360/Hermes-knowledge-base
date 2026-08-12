import { useEffect, useState } from "react";
import { api } from "../api";
import type { ObsidianDocItem, VaultStatus, VaultSyncResult } from "../types";
import { showToast } from "./Toast";
import {
  BauhausButton,
  BauhausCard,
  BauhausSectionLabel,
  BodyText,
  ErrorBanner,
  MetaText,
  MonoText,
} from "./ui";

/**
 * V4-Phase1：Obsidian vault 集成面板。
 *
 * 功能：
 * - 显示 vault 集成状态（enabled/watching/synced_docs/last_sync）
 * - 手动触发全量/增量扫描同步
 * - 启动/停止实时监听（watchdog）
 * - 显示同步结果（scanned/imported/skipped/failed + errors）
 *
 * 注意：vault 路径通过环境变量 KB_VAULT_PATH 配置，前端仅展示不可修改。
 */
export function ObsidianPanel() {
  const [status, setStatus] = useState<VaultStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [togglingWatch, setTogglingWatch] = useState(false);
  const [syncResult, setSyncResult] = useState<VaultSyncResult | null>(null);
  const [docs, setDocs] = useState<ObsidianDocItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [exportingId, setExportingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const loadStatus = async () => {
    setLoading(true);
    setError("");
    try {
      const s = await api.obsidianStatus();
      setStatus(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : "状态加载失败");
    } finally {
      setLoading(false);
    }
  };

  const loadDocs = async () => {
    setDocsLoading(true);
    try {
      const res = await api.obsidianDocs();
      setDocs(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "文档列表加载失败");
    } finally {
      setDocsLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  useEffect(() => {
    if (status?.enabled) {
      loadDocs();
    }
  }, [status?.enabled]);

  const handleExport = async (docId: string, title: string) => {
    setExportingId(docId);
    setError("");
    try {
      const res = await api.obsidianExport(docId);
      showToast(`已导出「${title}」→ vault/${res.path}`, "success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      showToast(`导出失败：${msg}`, "danger");
    } finally {
      setExportingId(null);
    }
  };

  const handleSync = async (incremental: boolean) => {
    setSyncing(true);
    setError("");
    setSyncResult(null);
    try {
      const result = await api.obsidianSync(incremental);
      setSyncResult(result);
      showToast(
        `同步完成：扫描 ${result.scanned}，导入 ${result.imported}，跳过 ${result.skipped}，失败 ${result.failed}`,
        result.failed > 0 ? "danger" : "success",
      );
      await loadStatus();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      showToast(`同步失败：${msg}`, "danger");
    } finally {
      setSyncing(false);
    }
  };

  const handleToggleWatch = async () => {
    if (!status) return;
    setTogglingWatch(true);
    setError("");
    try {
      const enable = !status.watching;
      await api.obsidianWatch(enable);
      showToast(enable ? "实时监听已启动" : "实时监听已停止", "success");
      await loadStatus();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      showToast(`操作失败：${msg}`, "danger");
    } finally {
      setTogglingWatch(false);
    }
  };

  if (loading) {
    return <MetaText className="text-sm text-center py-8">加载中…</MetaText>;
  }

  return (
    <div data-testid="obsidian-panel">
      <BauhausSectionLabel className="mb-2">OBSIDIAN</BauhausSectionLabel>
      <h3
        className="mb-1"
        style={{ fontFamily: "var(--font-serif)", fontSize: "1.5rem", color: "var(--ink-900)" }}
      >
        Obsidian Vault 集成
      </h3>
      <hr className="divider-gold w-24 mt-3 mb-6" />

      <MetaText className="text-sm mb-6">
        将 Obsidian vault 文件夹接入 Hermes 知识库，自动同步 .md 笔记并建立 RAG 索引。
        vault 路径通过环境变量 <code className="px-1 rounded bg-ink-100">KB_VAULT_PATH</code> 配置。
      </MetaText>

      {error && (
        <ErrorBanner className="mb-4" data-testid="obsidian-error">
          {error}
        </ErrorBanner>
      )}

      {/* 状态展示 */}
      <BauhausCard className="p-5 mb-6" data-testid="obsidian-status-card">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <StatusItem label="集成状态" value={status?.enabled ? "已启用" : "未启用"} />
          <StatusItem label="Vault 路径" value={status?.vault_path || "(未配置)"} mono />
          <StatusItem
            label="实时监听"
            value={
              !status?.enabled
                ? "—"
                : !status.watchdog_available
                  ? "watchdog 未安装"
                  : status.watching
                    ? "运行中"
                    : "已停止"
            }
          />
          <StatusItem label="已同步文档" value={String(status?.synced_docs ?? 0)} />
          <StatusItem
            label="最后同步"
            value={
              status?.last_sync
                ? new Date(status.last_sync).toLocaleString("zh-CN")
                : "从未同步"
            }
          />
        </div>
      </BauhausCard>

      {/* 未启用提示 */}
      {!status?.enabled && (
        <BauhausCard className="p-5 mb-6" data-testid="obsidian-disabled-hint">
          <BodyText className="text-sm mb-2">
            vault 集成未启用。请在环境变量中配置：
          </BodyText>
          <MonoText className="text-xs p-3 rounded" style={{ background: "var(--ink-100)" }}>
            KB_VAULT_PATH=/path/to/your/vault
          </MonoText>
          <BodyText className="text-sm mt-3">
            配置后重启服务即可启用。可选配置：
          </BodyText>
          <ul className="text-xs mt-1 space-y-1" style={{ color: "var(--ink-700)" }}>
            <li><code className="px-1 rounded bg-ink-100">KB_VAULT_WATCH=true</code> 启用实时监听（默认 true）</li>
            <li><code className="px-1 rounded bg-ink-100">KB_VAULT_EXCLUDE=.obsidian,*.png</code> 排除模式（逗号分隔）</li>
          </ul>
        </BauhausCard>
      )}

      {/* 操作按钮 */}
      {status?.enabled && (
        <div className="flex flex-wrap gap-3 mb-6" data-testid="obsidian-actions">
          <BauhausButton
            variant="solid"
            onClick={() => handleSync(true)}
            disabled={syncing}
            aria-label="增量同步（仅变更文件）"
          >
            {syncing ? "同步中..." : "增量同步"}
          </BauhausButton>
          <BauhausButton
            variant="outline"
            onClick={() => handleSync(false)}
            disabled={syncing}
            aria-label="全量重扫（所有 .md 文件）"
          >
            全量重扫
          </BauhausButton>
          {status.watchdog_available && (
            <BauhausButton
              variant="outline"
              onClick={handleToggleWatch}
              disabled={togglingWatch}
              aria-label={status.watching ? "停止实时监听" : "启动实时监听"}
            >
              {togglingWatch ? "处理中..." : status.watching ? "停止监听" : "启动监听"}
            </BauhausButton>
          )}
        </div>
      )}

      {/* 同步结果 */}
      {syncResult && (
        <BauhausCard className="p-5 mb-6" data-testid="obsidian-sync-result">
          <BodyText className="text-sm font-medium mb-3">同步结果</BodyText>
          <div className="grid grid-cols-4 gap-3 text-center mb-3">
            <ResultMetric label="扫描" value={syncResult.scanned} />
            <ResultMetric label="导入" value={syncResult.imported} />
            <ResultMetric label="跳过" value={syncResult.skipped} />
            <ResultMetric
              label="失败"
              value={syncResult.failed}
              danger={syncResult.failed > 0}
            />
          </div>
          {syncResult.errors.length > 0 && (
            <div className="mt-3">
              <MetaText className="text-xs mb-1" style={{ color: "var(--danger)" }}>
                错误详情（前 {Math.min(syncResult.errors.length, 20)} 条）：
              </MetaText>
              <ul
                className="text-xs space-y-1 max-h-40 overflow-y-auto p-2 rounded"
                style={{ background: "rgba(179, 38, 30, 0.05)" }}
                data-testid="obsidian-sync-errors"
              >
                {syncResult.errors.map((err, i) => (
                  <li key={i} className="truncate" style={{ color: "var(--danger)" }}>
                    {err}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </BauhausCard>
      )}

      {/* 已同步文档列表 */}
      {status?.enabled && (
        <BauhausCard className="p-5 mb-6" data-testid="obsidian-docs-card">
          <div className="flex items-center justify-between mb-3">
            <BodyText className="text-sm font-medium">已同步文档（{docs.length}）</BodyText>
            <BauhausButton variant="outline" onClick={loadDocs} disabled={docsLoading} aria-label="刷新已同步文档列表">
              {docsLoading ? "加载中..." : "刷新"}
            </BauhausButton>
          </div>
          {docs.length === 0 ? (
            <MetaText className="text-xs">尚无已同步的 Obsidian 文档，点击上方「增量同步」或「全量重扫」导入 .md 笔记。</MetaText>
          ) : (
            <ul className="space-y-2 max-h-72 overflow-y-auto" data-testid="obsidian-docs-list">
              {docs.map((d) => (
                <li
                  key={d.doc_id}
                  className="p-3 rounded border border-ink-100 flex items-start justify-between gap-3"
                  data-testid={`obsidian-doc-${d.doc_id}`}
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate" style={{ color: "var(--ink-900)" }} title={d.title}>
                      {d.title}
                    </div>
                    <MetaText className="text-xs mt-0.5 block truncate" title={d.vault_path}>
                      {d.vault_path || "(无 vault 路径)"}
                    </MetaText>
                    {Array.isArray(d.wikilinks) && d.wikilinks.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {d.wikilinks.slice(0, 6).map((w) => (
                          <span key={w} className="text-[10px] px-1.5 py-0.5 rounded bg-ink-100" style={{ color: "var(--ink-600)" }}>
                            [[{w}]]
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <BauhausButton
                    variant="outline"
                    disabled={exportingId === d.doc_id}
                    onClick={() => handleExport(d.doc_id, d.title)}
                    aria-label={`导出「${d.title}」到 vault`}
                  >
                    {exportingId === d.doc_id ? "导出中..." : "导出"}
                  </BauhausButton>
                </li>
              ))}
            </ul>
          )}
        </BauhausCard>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 内部子组件
// ---------------------------------------------------------------------------
function StatusItem({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <MetaText className="text-xs mb-1">{label}</MetaText>
      <BodyText
        className="text-sm truncate"
        style={mono ? { fontFamily: "var(--font-mono)" } : undefined}
        title={value}
      >
        {value}
      </BodyText>
    </div>
  );
}

function ResultMetric({
  label,
  value,
  danger,
}: {
  label: string;
  value: number;
  danger?: boolean;
}) {
  return (
    <div>
      <div
        className="text-2xl font-bold"
        style={{
          fontFamily: "var(--font-serif)",
          color: danger ? "var(--danger)" : "var(--ink-900)",
        }}
      >
        {value}
      </div>
      <MetaText className="text-xs">{label}</MetaText>
    </div>
  );
}
