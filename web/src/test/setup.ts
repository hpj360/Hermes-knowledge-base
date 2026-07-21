// Vitest 全局 setup
import "@testing-library/jest-dom/vitest";

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
