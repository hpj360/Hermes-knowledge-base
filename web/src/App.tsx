import { useEffect, useState } from "react";
import { Link, Redirect, Route, Switch, useLocation } from "wouter";
import { api, setUnauthorizedHandler } from "./api";
import type { HealthStatus } from "./types";
import { AgeGate } from "./components/AgeGate";
import { Login } from "./components/Login";
import { ChatPanel } from "./components/ChatPanel";
import { DocumentList } from "./components/DocumentList";
import { DocumentDetailPanel } from "./components/DocumentDetailPanel";
import { ImportDialog } from "./components/ImportDialog";
import { TagPanel } from "./components/TagPanel";
import { LabPanel } from "./components/LabPanel";
import { RecipePanel } from "./components/RecipePanel";
import { RecipeEditorPanel } from "./components/RecipeEditorPanel";
import { Skeleton } from "./components/Skeleton";
import { ToastHost, showToast } from "./components/Toast";
import { Logo, useConfirm } from "./components/ui";

/**
 * R3 IA 重构：4 主 tab + 1 管理 tab
 * 主 tab：问答 / 实验室 / 配方 / 文档
 * 管理 tab：标签管理（后续可扩展审核队列、导入历史等）
 */
const NAV_ITEMS: ReadonlyArray<{ path: string; label: string }> = [
  { path: "/chat", label: "问答" },
  { path: "/lab", label: "实验室" },
  { path: "/recipes", label: "配方" },
  { path: "/docs", label: "文档" },
  { path: "/admin", label: "管理" },
];

/** 导航项：当前路径精确或前缀匹配时激活 */
function NavItem({ path, label }: { path: string; label: string }) {
  const [location] = useLocation();
  const isActive = location === path || location.startsWith(`${path}/`);
  return (
    <Link
      to={path}
      className={`nav-tab ${isActive ? "nav-tab-active" : ""}`}
      aria-current={isActive ? "page" : undefined}
    >
      {label}
    </Link>
  );
}

export default function App() {
  const [ageConfirmed, setAgeConfirmed] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const [needLogin, setNeedLogin] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [docRefreshKey, setDocRefreshKey] = useState(0);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [, navigate] = useLocation();

  // R2: 替代 window.confirm 的异步确认对话框
  const { confirm, dialog: confirmDialog } = useConfirm();

  // 健康检查（同时判断是否需要登录）
  const refreshHealth = async () => {
    try {
      const h = await api.health();
      setHealth(h);
      if (h.auth_enabled && !api.getToken()) {
        setNeedLogin(true);
      } else {
        setNeedLogin(false);
      }
      setAuthReady(true);
    } catch {
      setAuthReady(true);
    }
  };

  useEffect(() => {
    if (ageConfirmed) refreshHealth();
  }, [ageConfirmed]); // 依赖 ageConfirmed 触发一次性健康检查

  // P2 修复：注册 401 处理器，token 过期自动跳登录
  useEffect(() => {
    setUnauthorizedHandler(() => setNeedLogin(true));
    return () => setUnauthorizedHandler(null);
  }, []);

  // 年龄门未确认
  if (!ageConfirmed) {
    return <AgeGate onConfirm={() => setAgeConfirmed(true)} />;
  }

  // 等待健康检查
  if (!authReady) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ background: "var(--paper-bg)" }}>
        <div className="reveal-item" style={{ color: "var(--brand-700)" }}>
          <Logo size={36} />
        </div>
        <div className="w-48 reveal-item delay-2">
          <Skeleton height="0.875rem" width="100%" className="mb-2" />
          <Skeleton height="0.875rem" width="60%" />
        </div>
      </div>
    );
  }

  // 需要登录
  if (needLogin) {
    return <Login onLogin={() => { setNeedLogin(false); refreshHealth(); }} />;
  }

  const refreshDocs = () => {
    setDocRefreshKey((k) => k + 1);
    refreshHealth();
  };

  // M2-04：从问答引用跳转到文档详情（R3 URL 化）
  const jumpToDocChunk = (docId: string, chunkRowid?: number) => {
    navigate(chunkRowid !== undefined ? `/docs/${docId}?chunk=${chunkRowid}` : `/docs/${docId}`);
  };

  const handleSelectDoc = (docId: string) => {
    navigate(`/docs/${docId}`);
  };

  const handleBackToList = () => {
    navigate("/docs");
  };

  const handleSeed = async () => {
    if (!(await confirm("将导入 5 篇酒类种子知识（金酒/威士忌/葡萄酒/白酒/朗姆+龙舌兰），是否继续？"))) return;
    setSeeding(true);
    try {
      const result = await api.seed();
      showToast(`导入完成：${result.seeded} 篇成功${result.failed > 0 ? `，${result.failed} 篇失败` : ""}`, "success");
      refreshDocs();
    } catch (err) {
      showToast(`导入失败：${err instanceof Error ? err.message : err}`, "danger");
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="h-screen flex flex-col relative bg-noise" style={{ background: "var(--paper-bg)" }}>
      {/* 顶部栏 — .navbar 语义类：噪点底 + 深酒红渐变 + 金箔底边 + sticky */}
      <header className="navbar px-6 py-4 flex items-center justify-between flex-shrink-0 relative overflow-hidden">
        <div className="flex items-center gap-3 relative z-10">
          <div className="text-gold-foil">
            <Logo size={28} />
          </div>
          <div>
            <h1 className="brand">
              <span className="brand-accent">Hermes 知识库</span>
            </h1>
            {health && (
              <p className="text-xs mt-0.5" style={{ color: "rgba(250, 243, 220, 0.75)" }}>
                {health.doc_count} 篇文档
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {health && health.doc_count === 0 && (
            <button
              onClick={handleSeed}
              className="btn-secondary text-sm"
              disabled={seeding}
            >
              {seeding ? "导入中..." : "导入种子知识"}
            </button>
          )}
          <button
            onClick={() => setShowImport(true)}
            className="btn-primary text-sm"
          >
            导入
          </button>
          {health?.auth_enabled && (
            <button
              onClick={() => {
                api.logout();
                setNeedLogin(true);
              }}
              className="btn-secondary text-sm"
            >
              退出
            </button>
          )}
        </div>
      </header>

      {/* 水平导航 — 杂志式 tab（R3: 4 主 + 1 管理） */}
      <nav
        className="flex items-center gap-1 px-6 bg-white border-b border-ink-200 flex-shrink-0 overflow-x-auto"
        aria-label="主导航"
      >
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.path} path={item.path} label={item.label} />
        ))}
      </nav>

      {/* 内容区 — R3 路由驱动 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <Switch>
          <Route path="/chat">
            <ChatPanel refreshDocs={refreshDocs} onJumpToDoc={jumpToDocChunk} />
          </Route>
          <Route path="/lab">
            <LabPanel onJumpToDoc={jumpToDocChunk} />
          </Route>
          {/* /recipes/new 必须在 /recipes/:id/edit 与 /recipes 之前以避免歧义 */}
          <Route path="/recipes/new">
            <RecipeEditorPanel
              onSaved={() => navigate("/recipes")}
              onCancel={() => navigate("/recipes")}
            />
          </Route>
          <Route path="/recipes/:id/edit">
            {(params) => (
              <RecipeEditorPanel
                docId={params.id}
                onSaved={() => navigate("/recipes")}
                onCancel={() => navigate("/recipes")}
              />
            )}
          </Route>
          <Route path="/recipes">
            <RecipePanel
              onCreateRecipe={() => navigate("/recipes/new")}
              onEditRecipe={(docId) => navigate(`/recipes/${docId}/edit`)}
            />
          </Route>
          {/* /docs/:id 必须在 /docs 之前 */}
          <Route path="/docs/:id">
            {(params) => (
              <DocDetailRoute
                docId={params.id}
                refreshDocs={refreshDocs}
                onBack={handleBackToList}
                docRefreshKey={docRefreshKey}
              />
            )}
          </Route>
          <Route path="/docs">
            <DocumentList
              refreshKey={docRefreshKey}
              onChange={refreshHealth}
              onSelectDoc={handleSelectDoc}
            />
          </Route>
          <Route path="/admin">
            <TagPanel onChange={refreshDocs} />
          </Route>
          <Route path="/">
            <Redirect to="/chat" />
          </Route>
          <Route>
            <NotFound />
          </Route>
        </Switch>
      </main>

      {/* 导入对话框 */}
      {showImport && (
        <ImportDialog
          onClose={() => setShowImport(false)}
          onImported={refreshDocs}
        />
      )}

      {/* 全局 Toast 容器 */}
      <ToastHost />

      {/* R2: useConfirm 对话框 */}
      {confirmDialog}
    </div>
  );
}

/**
 * 文档详情路由组件：从 URL ?chunk=N 解析高亮 chunk（R3 URL 状态同步）
 * 刷新文档列表时通过 docRefreshKey 触发详情重新加载
 */
function DocDetailRoute({
  docId,
  refreshDocs,
  onBack,
  docRefreshKey,
}: {
  docId: string;
  refreshDocs: () => void;
  onBack: () => void;
  docRefreshKey: number;
}) {
  const [location] = useLocation();
  const queryStr = location.split("?")[1] || "";
  const chunkParam = new URLSearchParams(queryStr).get("chunk");
  const highlightChunk = chunkParam ? Number(chunkParam) : undefined;

  return (
    <DocumentDetailPanel
      key={`${docId}-${docRefreshKey}`}
      docId={docId}
      highlightChunk={highlightChunk}
      onBack={onBack}
      onChange={refreshDocs}
    />
  );
}

function NotFound() {
  return (
    <div className="p-8 text-center" style={{ color: "var(--ink-400)" }}>
      <p className="eyebrow mb-2">404</p>
      <p>页面不存在</p>
    </div>
  );
}
