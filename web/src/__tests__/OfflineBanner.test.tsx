/**
 * SubTask 13.6: OfflineBanner 组件测试
 *
 * 验证：
 * 1. 在线时不渲染 banner
 * 2. 离线时渲染 banner，含「离线模式」文字 + role=status
 * 3. online/offline 事件切换 banner 显示（vi.spyOn 捕获回调 + 真实事件派发 + waitFor）
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup, waitFor, act } from "@testing-library/react";
import { OfflineBanner } from "../components/OfflineBanner";

/** 控制 navigator.onLine（jsdom 默认为 true，通过实例属性遮蔽原型 getter） */
function setOnline(value: boolean) {
  Object.defineProperty(navigator, "onLine", {
    value,
    configurable: true,
    writable: true,
  });
}

describe("OfflineBanner", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    setOnline(true);
    cleanup();
  });

  it("在线时不渲染 banner", () => {
    setOnline(true);
    const { container } = render(<OfflineBanner />);
    expect(container.firstChild).toBeNull();
    expect(screen.queryByText(/离线模式/)).toBeNull();
  });

  it("离线时渲染 banner，含「离线模式」文字并带 role=status", () => {
    setOnline(false);
    render(<OfflineBanner />);
    const banner = screen.getByText(/离线模式/);
    expect(banner).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("online/offline 事件切换 banner 显示", async () => {
    setOnline(true);
    // vi.fn 通过 spyOn 捕获 addEventListener 回调，验证注册了 online/offline 监听
    const addSpy = vi.spyOn(window, "addEventListener");
    render(<OfflineBanner />);
    expect(addSpy).toHaveBeenCalledWith("offline", expect.any(Function));
    expect(addSpy).toHaveBeenCalledWith("online", expect.any(Function));

    // 真实派发 offline 事件 → banner 出现（act 包裹同步状态更新）
    act(() => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByText(/离线模式/)).toBeInTheDocument();

    // 真实派发 online 事件 → banner 消失（waitFor 验证异步 UI 变化）
    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    await waitFor(() => {
      expect(screen.queryByText(/离线模式/)).toBeNull();
    });
  });
});
