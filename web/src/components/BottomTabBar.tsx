/**
 * 移动端底部 tab bar（< 768px 响应式导航）
 *
 * 设计：包豪斯几何 + 极简现代风格
 * - 白底 + 顶部 3px 黑色边框
 * - 5 个 tab：首页 / 问答 / 配方 / 实验室 / 设置
 * - SVG 简约线条图标（stroke-width=2, stroke="currentColor"）
 * - 激活态：底部 3px wine 色边框 + wine 色文字
 * - 非激活态：ink-400 灰色文字
 * - 固定视口底部，含 safe-area-inset-bottom
 *
 * 路由库：wouter（useLocation 返回 [location, navigate]，Link 接 to prop）
 */
import type { ReactNode } from "react";
import { Link, useLocation } from "wouter";

interface TabItem {
  path: string;
  label: string;
  icon: ReactNode;
}

const TABS: ReadonlyArray<TabItem> = [
  { path: "/", label: "首页", icon: <HomeIcon /> },
  { path: "/chat", label: "问答", icon: <ChatIcon /> },
  { path: "/recipes", label: "配方", icon: <RecipeIcon /> },
  { path: "/lab", label: "实验室", icon: <LabIcon /> },
  { path: "/settings", label: "设置", icon: <SettingsIcon /> },
];

export function BottomTabBar() {
  const [location] = useLocation();

  return (
    <nav
      aria-label="移动导航"
      className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex items-stretch"
      style={{
        background: "var(--paper)",
        borderTop: "3px solid var(--ink-900)",
        height: "calc(56px + env(safe-area-inset-bottom))",
        paddingBottom: "env(safe-area-inset-bottom)",
      }}
    >
      {TABS.map((tab) => {
        const isActive =
          tab.path === "/"
            ? location === "/"
            : location === tab.path || location.startsWith(`${tab.path}/`);
        return (
          <Link
            key={tab.path}
            to={tab.path}
            aria-current={isActive ? "page" : undefined}
            className="flex-1 flex flex-col items-center justify-center gap-1 no-underline"
            style={{
              color: isActive ? "var(--wine)" : "var(--ink-400)",
              borderBottom: isActive
                ? "3px solid var(--wine)"
                : "3px solid transparent",
              fontFamily: "var(--font-mono)",
              fontSize: "0.625rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// SVG 简约线条图标：stroke="currentColor" stroke-width="2"
// ---------------------------------------------------------------------------

function HomeIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 12 L12 4 L21 12" />
      <path d="M5 11 L5 20 L19 20 L19 11" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 5 H20 V16 H12 L7 20 V16 H4 Z" />
    </svg>
  );
}

function RecipeIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5 4 H19 V20 H5 Z" />
      <path d="M9 4 V20" />
      <path d="M12 8 H16" />
      <path d="M12 12 H16" />
    </svg>
  );
}

function LabIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M9 3 H15" />
      <path d="M10 3 V10 L5 19 Q5 21 7 21 H17 Q19 21 19 19 L14 10 V3" />
      <path d="M7.5 15 H16.5" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2 V5 M12 19 V22 M2 12 H5 M19 12 H22 M4.9 4.9 L7 7 M17 17 L19.1 19.1 M4.9 19.1 L7 17 M17 7 L19.1 4.9" />
    </svg>
  );
}
