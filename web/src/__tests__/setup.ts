// Vitest 全局 setup
import "@testing-library/jest-dom/vitest";
import { beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom 不实现 matchMedia，部分组件可能依赖
if (!window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

// jsdom 不实现 IntersectionObserver
class MockIntersectionObserver {
  observe = () => {};
  unobserve = () => {};
  disconnect = () => {};
  takeRecords = () => [];
}
// @ts-expect-error jsdom 没有 IntersectionObserver
global.IntersectionObserver = MockIntersectionObserver;

// R3: 路由测试隔离 — 每个用例前重置 URL 到 /，避免上一个用例的导航污染下一个
beforeEach(() => {
  window.history.replaceState({}, "", "/");
});

// R3: 显式 cleanup，确保上一个用例的渲染（含 ImportDialog 等 fixed 层）不残留
afterEach(() => {
  cleanup();
});
