import { useEffect, useState } from "react";
import { Link, Redirect, Route, Switch, useLocation } from "wouter";
import { api, setUnauthorizedHandler } from "./api";
import type { HealthStatus } from "./types";
import { AgeGate } from "./components/AgeGate";
import { Login } from "./components/Login";
import { MultiLogin } from "./components/MultiLogin";
import { OfflineBanner } from "./components/OfflineBanner";
import { ChatPanel } from "./components/ChatPanel";
import { DocumentList } from "./components/DocumentList";
import { DocumentDetailPanel } from "./components/DocumentDetailPanel";
import { ImportDialog } from "./components/ImportDialog";
import { SettingsPanel } from "./components/SettingsPanel";
import { LabPanel } from "./components/LabPanel";
import { RecipePanel } from "./components/RecipePanel";
import { RecipeEditorPanel } from "./components/RecipeEditorPanel";
import { DashboardPanel } from "./components/DashboardPanel";
import { Skeleton } from "./components/Skeleton";
import { ToastHost, showToast } from "./components/Toast";
import { BottomTabBar } from "./components/BottomTabBar";
import { Logo, useConfirm, BauhausBrandMark, BauhausButton, BauhausGeometry } from "./components/ui";

/**
 * 移动端断点检测：匹配 Tailwind md: 断点（< 768px 视为移动端）。
 *
 * 用途：条件渲染顶部 nav（仅桌面）与底部 BottomTabBar（仅移动）。
 * 测试时通过 mock window.matchMedia 控制返回值。
 */
function useIsMobile() {
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;
    return window.matchMedia("(max-width: 767px)").matches;
  });
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia("(max-width: 767px)");
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);
  return isMobile;
}

/**
 * 产品重构：分组导航 — 首页 + 知识区(问答/文档) + 调酒区(配方/实验室) + 设置
 * 统一叙事：从知识到实践（知识可信 → 实践可用 → 持续成长）
 */
interface NavGroup {
  label: string;
  items: ReadonlyArray<{ path: string; label: string }>;
}

const NAV_GROUPS: ReadonlyArray<NavGroup> = [
  { label: "", items: [{ path: "/", label: "首页" }] },
  {
    label: "知识",
    items: [
      { path: "/chat", label: "问答" },
      { path: "/docs", label: "文档" },
    ],
  },
  {
    label: "调酒",
    items: [
      { path: "/recipes", label: "配方" },
      { path: "/lab", label: "实验室" },
    ],
  },
  { label: "", items: [{ path: "/settings", label: "设置" }] },
];

/** 导航项：当前路径精确或前缀匹配时激活 */
function NavItem({ path, label }: { path: string; label: string }) {
  const [location] = useLocation();
  const isActive = path === "/" ? location === "/" : location === path || location.startsWith(`${path}/`);
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
  const isMobile = useIsMobile();

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
        <div className="reveal-item" style={{ color: "var(--wine)" }}>
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
    // V3-Task10：multiuser 模式用 MultiLogin，否则用单用户 Login
    if (health?.multiuser) {
      return <MultiLogin onLogin={() => { setNeedLogin(false); refreshHealth(); }} />;
    }
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
    <div className="h-screen flex flex-col relative" style={{ background: "var(--paper-bg)" }}>
      <OfflineBanner />
      {/* 顶部栏 — 包豪斯导航栏：白底 + 3px 黑色底边 + brand mark 实色方块
          T1 信息密度优化：压缩 header 高度（py-2 / Logo 20 / 标题 base），
          文档数与操作按钮下沉到主导航右侧，header 与 nav 形成视觉整体。 */}
      <header className="navbar px-6 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <BauhausBrandMark />
          <Logo size={20} className="text-ink-900" />
          <h1 className="brand" style={{ fontSize: "var(--fs-base)" }}>
            <span className="brand-accent">Hermes 知识库</span>
          </h1>
        </div>
      </header>

      {/* 水平导航 — 分组：首页 | 知识区(问答/文档) | 调酒区(配方/实验室) | 设置
          移动端 (<768px) 隐藏，改用底部 BottomTabBar；桌面端 (≥768px) 显示。
          hidden md:flex 提供 CSS 级隐藏，!isMobile 提供条件渲染（jsdom 测试用）。
          T1：文档数 + 导入种子/退出按钮合并到导航栏右侧（ml-auto），
          nav border 降为 ink-100，与 header 3px 黑边形成层次统一的顶部区。 */}
      {!isMobile && (
      <nav
        className="hidden md:flex items-center gap-1 px-6 border-b border-ink-100 flex-shrink-0 overflow-x-auto"
        aria-label="主导航"
        style={{ background: "var(--paper)" }}
      >
        {NAV_GROUPS.map((group, gi) => (
          <div key={gi} className="flex items-center gap-1">
            {gi > 0 && (
              <span
                className="mx-1 h-4 w-px flex-shrink-0"
                style={{ background: "var(--ink-200)" }}
                aria-hidden="true"
              />
            )}
            {group.items.map((item) => (
              <NavItem key={item.path} path={item.path} label={item.label} />
            ))}
          </div>
        ))}
        <span className="ml-auto flex items-center gap-3">
          {health && (
            <span
              className="text-xs font-mono"
              style={{ color: "var(--ink-400)" }}
            >
              {health.doc_count} 篇文档
            </span>
          )}
          {health && health.doc_count === 0 && (
            <BauhausButton
              variant="outline"
              onClick={handleSeed}
              disabled={seeding}
            >
              {seeding ? "导入中..." : "导入种子知识"}
            </BauhausButton>
          )}
          {health?.auth_enabled && (
            <BauhausButton
              variant="outline"
              onClick={() => {
                api.logout();
                setNeedLogin(true);
              }}
            >
              退出
            </BauhausButton>
          )}
        </span>
      </nav>
      )}

      {/* 内容区 — 路由驱动，包豪斯几何装饰
          移动端 pb-14 给底部 tab bar 留空间（约 56px），桌面端 md:pb-0 */}
      <main className="flex-1 flex flex-col overflow-hidden relative pb-14 md:pb-0">
        <BauhausGeometry positions={["tr", "br"]} />
        <div className="relative z-10 flex-1 flex flex-col overflow-hidden">
          <Switch>
          <Route path="/">
            <DashboardPanel
              health={health}
              onSeed={handleSeed}
              seeding={seeding}
              onShowImport={() => setShowImport(true)}
            />
          </Route>
          <Route path="/chat">
            <ChatPanel refreshDocs={refreshDocs} onJumpToDoc={jumpToDocChunk} />
          </Route>
          <Route path="/lab">
            <LabPanel
              onJumpToDoc={jumpToDocChunk}
              onCreateRecipe={() => navigate("/recipes/new")}
              onEditRecipe={(docId) => navigate(`/recipes/${docId}/edit`)}
            />
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
              onShowImport={() => setShowImport(true)}
            />
          </Route>
          <Route path="/settings">
            <SettingsPanel onChange={refreshDocs} />
          </Route>
          <Route>
            <NotFound />
          </Route>
          </Switch>
        </div>
      </main>

      {/* 移动端底部 tab bar — 仅 <768px 显示（md:hidden CSS 隐藏 + isMobile 条件渲染）
          已通过 ageConfirmed && authReady && !needLogin 检查（在此 return 分支内） */}
      {isMobile && (
        <div className="md:hidden">
          <BottomTabBar />
        </div>
      )}

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
