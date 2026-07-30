import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AuditLogItem, HealthStatus, ImportBackupResult } from "../types";
import { ObsidianPanel } from "./ObsidianPanel";
import { TagPanel } from "./TagPanel";
import { UserAdminPanel } from "./UserAdminPanel";
import { showToast } from "./Toast";
import {
  BauhausButton,
  BauhausCard,
  BauhausDisplay,
  BauhausSectionLabel,
  BodyText,
  ErrorBanner,
  MetaText,
  MonoText,
} from "./ui";

interface SettingsPanelProps {
  onChange: () => void;
}

type SettingsTab = "tags" | "export" | "audit" | "users" | "obsidian";

// 设置中心子模块 tab（users 仅 multiuser 模式显示，obsidian 仅 vault 启用时显示）
const TABS: ReadonlyArray<{ key: SettingsTab; label: string; multiuserOnly?: boolean; vaultOnly?: boolean }> = [
  { key: "tags", label: "标签管理" },
  { key: "export", label: "数据导出" },
  { key: "audit", label: "审计日志" },
  { key: "users", label: "用户管理", multiuserOnly: true },
  { key: "obsidian", label: "Obsidian", vaultOnly: true },
];

/** 设置中心：聚合标签管理、数据导出、审计日志、用户管理子模块的容器。 */
export function SettingsPanel({ onChange }: SettingsPanelProps) {
  const [active, setActive] = useState<SettingsTab>("tags");
  const [health, setHealth] = useState<HealthStatus | null>(null);

  // V3-Task10：检查 multiuser 模式（决定是否显示"用户管理"tab）
  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
  }, []);

  const visibleTabs = TABS.filter(
    (t) => (!t.multiuserOnly || health?.multiuser) && (!t.vaultOnly || health?.vault_enabled),
  );

  return (
    <div>
      {/* 顶部标题 + 子模块 tab（pb-0 使 tab 的下边框紧贴内容区） */}
      <div className="p-8 max-w-3xl mx-auto pb-0">
        <div className="mb-8">
          <BauhausSectionLabel className="mb-2">SETTINGS</BauhausSectionLabel>
          <BauhausDisplay as="h2">设置中心</BauhausDisplay>
          <hr className="divider-gold w-24 mt-4" />
        </div>
        <nav
          className="flex items-center gap-1 border-b border-ink-200"
          aria-label="设置子模块"
        >
          {visibleTabs.map((tab) => {
            const isActive = active === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActive(tab.key)}
                className={`nav-tab ${isActive ? "nav-tab-active" : ""}`}
                aria-current={isActive ? "page" : undefined}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* 子模块内容：标签管理直接复用 TagPanel（自带容器与标题，避免双重包裹） */}
      {active === "tags" && <TagPanel onChange={onChange} />}

      {active === "export" && (
        <div className="p-8 max-w-3xl mx-auto">
          <ExportPanel onImported={onChange} />
        </div>
      )}

      {active === "audit" && (
        <div className="p-8 max-w-3xl mx-auto">
          <AuditPanel />
        </div>
      )}

      {active === "users" && (
        <div className="p-8 max-w-3xl mx-auto">
          <UserAdminPanel />
        </div>
      )}

      {active === "obsidian" && (
        <div className="p-8 max-w-3xl mx-auto">
          <ObsidianPanel />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 数据导出 / 导入恢复子模块
// ---------------------------------------------------------------------------

/** 触发浏览器下载 Blob */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function ExportPanel({ onImported }: { onImported: () => void }) {
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportBackupResult | null>(null);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleExport = async () => {
    setExporting(true);
    setError("");
    try {
      const blob = await api.exportAll();
      // 文件名使用固定前缀 + 时间戳；后端已返回 Content-Disposition，但 Blob 无此 header
      const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      downloadBlob(blob, `hermes_kb_export_${ts}.json`);
      showToast("导出成功，已开始下载", "success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      showToast(`导出失败：${msg}`, "danger");
    } finally {
      setExporting(false);
    }
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setError("");
    setImportResult(null);
    try {
      const result = await api.importBackup(file);
      setImportResult(result);
      if (result.total_failed > 0) {
        showToast(`导入完成（${result.total} 行成功，${result.total_failed} 行失败）`, "warning");
      } else {
        showToast(`导入完成：${result.total} 行成功`, "success");
      }
      onImported();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      showToast(`导入失败：${msg}`, "danger");
    } finally {
      setImporting(false);
      // 重置 input 以便相同文件可再次选择
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div>
      <BauhausSectionLabel className="mb-2">DATA EXPORT</BauhausSectionLabel>
      <BauhausDisplay as="h2" className="mb-2">数据导出与恢复</BauhausDisplay>
      <BodyText className="text-sm mb-6" style={{ color: "var(--ink-400)" }}>
        导出包含所有文档、分片、标签、历史、配方统计等业务数据的 JSON 备份；可通过「恢复」按钮上传备份文件，幂等覆盖现有数据。
      </BodyText>

      {error && <div className="mb-4"><ErrorBanner>{error}</ErrorBanner></div>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <BauhausCard className="p-6" accent="wine">
          <BauhausSectionLabel className="mb-2">EXPORT</BauhausSectionLabel>
          <BodyText className="text-sm mb-4">
            下载全量 JSON 备份（含 10 张业务表，不含向量数据）。
          </BodyText>
          <BauhausButton
            variant="solid"
            onClick={handleExport}
            disabled={exporting}
          >
            {exporting ? "导出中..." : "下载备份 JSON"}
          </BauhausButton>
        </BauhausCard>

        <BauhausCard className="p-6" accent="amber">
          <BauhausSectionLabel className="mb-2">IMPORT</BauhausSectionLabel>
          <BodyText className="text-sm mb-4">
            上传备份文件恢复数据（INSERT OR REPLACE，幂等）。
          </BodyText>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            onChange={handleFileChange}
            style={{ display: "none" }}
            aria-label="选择备份 JSON 文件"
          />
          <BauhausButton
            variant="outline"
            onClick={handleImportClick}
            disabled={importing}
          >
            {importing ? "导入中..." : "上传恢复"}
          </BauhausButton>
        </BauhausCard>
      </div>

      {/* 导入结果展示 */}
      {importResult && (
        <BauhausCard className="p-6" accent="bronze">
          <BauhausSectionLabel className="mb-2">IMPORT RESULT</BauhausSectionLabel>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <MetaText as="div" className="text-xs">版本</MetaText>
              <MonoText as="div">{importResult.version}</MonoText>
            </div>
            <div>
              <MetaText as="div" className="text-xs">总成功行</MetaText>
              <MonoText as="div" style={{ color: "var(--success, #16a34a)" }}>
                {importResult.total}
              </MonoText>
            </div>
            <div>
              <MetaText as="div" className="text-xs">总失败行</MetaText>
              <MonoText
                as="div"
                style={{
                  color: importResult.total_failed > 0 ? "var(--danger, #dc2626)" : "var(--ink-400)",
                }}
              >
                {importResult.total_failed}
              </MonoText>
            </div>
          </div>

          {Object.keys(importResult.counts).length > 0 && (
            <div className="mb-3">
              <MetaText as="div" className="text-xs mb-1">各表成功数</MetaText>
              <div className="flex flex-wrap gap-2">
                {Object.entries(importResult.counts).map(([table, count]) => (
                  <span
                    key={table}
                    className="text-xs px-2 py-1"
                    style={{
                      background: "var(--paper)",
                      border: "1px solid var(--ink-100)",
                      borderRadius: "var(--r-sm)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {table}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}

          {importResult.total_failed > 0 && importResult.errors.length > 0 && (
            <div>
              <MetaText as="div" className="text-xs mb-1">错误详情（最多 50 条）</MetaText>
              <ul className="text-xs space-y-1" style={{ fontFamily: "var(--font-mono)" }}>
                {importResult.errors.slice(0, 10).map((e, i) => (
                  <li key={i} style={{ color: "var(--danger, #dc2626)" }}>
                    [{e.table}#{e.row_index}] {e.reason}
                  </li>
                ))}
                {importResult.errors.length > 10 && (
                  <li style={{ color: "var(--ink-400)" }}>
                    ... 还有 {importResult.errors.length - 10} 条
                  </li>
                )}
              </ul>
            </div>
          )}
        </BauhausCard>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 审计日志子模块
// ---------------------------------------------------------------------------

const ACTION_OPTIONS: ReadonlyArray<string> = [
  "",
  "login",
  "logout",
  "import",
  "export",
  "delete",
  "seed",
  "ask",
  "metadata",
];

const PAGE_SIZE = 20;

function AuditPanel() {
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState("");
  const [user, setActionUser] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await api.listAudit({
        limit: PAGE_SIZE,
        offset,
        action: action || undefined,
        user: user || undefined,
      });
      setItems(resp.items);
      setTotal(resp.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset, action, user]);

  const handleFilter = () => {
    setOffset(0);
    // 触发 useEffect 重新加载
  };

  const handleReset = () => {
    setAction("");
    setActionUser("");
    setOffset(0);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div>
      <BauhausSectionLabel className="mb-2">AUDIT LOG</BauhausSectionLabel>
      <BauhausDisplay as="h2" className="mb-2">审计日志</BauhausDisplay>
      <BodyText className="text-sm mb-6" style={{ color: "var(--ink-400)" }}>
        查看系统关键写操作（导入 / 导出 / 删除 / 种子 / 问答 / 元信息更新等），支持按动作与操作者筛选。
      </BodyText>

      {/* 筛选栏 */}
      <div className="flex flex-wrap items-end gap-3 mb-6">
        <div>
          <label
            htmlFor="audit-action"
            className="text-xs block mb-1"
            style={{ color: "var(--ink-400)", fontFamily: "var(--font-ui)" }}
          >
            动作
          </label>
          <select
            id="audit-action"
            className="input"
            value={action}
            onChange={(e) => {
              setAction(e.target.value);
              setOffset(0);
            }}
            style={{ minWidth: "140px" }}
          >
            {ACTION_OPTIONS.map((a) => (
              <option key={a} value={a}>
                {a === "" ? "全部动作" : a}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label
            htmlFor="audit-user"
            className="text-xs block mb-1"
            style={{ color: "var(--ink-400)", fontFamily: "var(--font-ui)" }}
          >
            操作者
          </label>
          <input
            id="audit-user"
            className="input"
            value={user}
            onChange={(e) => setActionUser(e.target.value)}
            placeholder="用户名"
            style={{ minWidth: "160px" }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFilter();
            }}
          />
        </div>
        <BauhausButton variant="solid" onClick={handleFilter} disabled={loading}>
          {loading ? "查询中..." : "筛选"}
        </BauhausButton>
        <BauhausButton variant="outline" onClick={handleReset} disabled={loading}>
          重置
        </BauhausButton>
      </div>

      {error && <div className="mb-4"><ErrorBanner>{error}</ErrorBanner></div>}

      {/* 列表 */}
      {items.length === 0 && !loading && !error ? (
        <BauhausCard className="p-12 text-center">
          <div className="text-2xl mb-2 text-gold-500">◆</div>
          <BauhausSectionLabel className="mb-2">EMPTY</BauhausSectionLabel>
          <BodyText className="text-sm">暂无审计日志</BodyText>
        </BauhausCard>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <BauhausCard key={item.id} className="p-4" accent={accentByAction(item.action)}>
              <div className="flex flex-wrap items-center gap-3 mb-2">
                <span
                  className="text-xs px-2 py-1"
                  style={{
                    background: "var(--ink-900)",
                    color: "#fff",
                    borderRadius: "var(--r-sm)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {item.action}
                </span>
                <MetaText className="text-xs">
                  {item.target_type}
                  {item.target_id ? ` · ${item.target_id}` : ""}
                </MetaText>
                <MetaText className="text-xs ml-auto">
                  {item.user} · {formatTime(item.created_at)}
                </MetaText>
              </div>
              {Object.keys(item.meta || {}).length > 0 && (
                <pre
                  className="text-xs overflow-x-auto"
                  style={{
                    background: "var(--paper)",
                    padding: "var(--sp-2) var(--sp-3)",
                    borderRadius: "var(--r-sm)",
                    border: "1px solid var(--ink-100)",
                    fontFamily: "var(--font-mono)",
                    color: "var(--ink-400)",
                    margin: 0,
                  }}
                >
                  {JSON.stringify(item.meta, null, 2)}
                </pre>
              )}
            </BauhausCard>
          ))}
        </div>
      )}

      {/* 分页 */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between mt-6">
          <MetaText className="text-xs">
            共 {total} 条 · 第 {currentPage} / {totalPages} 页
          </MetaText>
          <div className="flex gap-2">
            <BauhausButton
              variant="outline"
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0 || loading}
            >
              上一页
            </BauhausButton>
            <BauhausButton
              variant="outline"
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total || loading}
            >
              下一页
            </BauhausButton>
          </div>
        </div>
      )}
    </div>
  );
}

/** 根据动作返回包豪斯 accent 色 */
function accentByAction(action: string): "wine" | "amber" | "bronze" {
  if (action === "delete" || action === "reject") return "wine";
  if (action === "import" || action === "export") return "amber";
  return "bronze";
}

/** ISO 字符串 → 本地可读时间 */
function formatTime(iso: string): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
