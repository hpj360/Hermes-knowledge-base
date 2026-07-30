/** V4-Phase1 ObsidianPanel 测试：状态展示 + 同步操作 + 监听切换 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../api", () => ({
  api: {
    obsidianStatus: vi.fn(),
    obsidianSync: vi.fn(),
    obsidianWatch: vi.fn(),
    obsidianExport: vi.fn(),
  },
}));

vi.mock("../components/Toast", () => ({
  showToast: vi.fn(),
}));

import { api } from "../api";
import { showToast } from "../components/Toast";
import { ObsidianPanel } from "../components/ObsidianPanel";

const mockStatus = vi.mocked(api.obsidianStatus);
const mockSync = vi.mocked(api.obsidianSync);
const mockWatch = vi.mocked(api.obsidianWatch);

const DISABLED_STATUS = {
  enabled: false,
  vault_path: "",
  watch_enabled: false,
  watchdog_available: false,
  watching: false,
  synced_docs: 0,
  last_sync: null,
};

const ENABLED_STATUS = {
  enabled: true,
  vault_path: "/home/user/vault",
  watch_enabled: true,
  watchdog_available: true,
  watching: false,
  synced_docs: 5,
  last_sync: "2026-07-30T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ObsidianPanel", () => {
  it("未启用时渲染禁用提示与配置说明", async () => {
    mockStatus.mockResolvedValue(DISABLED_STATUS);
    render(<ObsidianPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("obsidian-disabled-hint")).toBeInTheDocument();
    });
    // 配置说明中包含 KB_VAULT_PATH（多处出现，用 getAllByText）
    expect(screen.getAllByText(/KB_VAULT_PATH/).length).toBeGreaterThan(0);
    expect(screen.queryByTestId("obsidian-actions")).not.toBeInTheDocument();
  });

  it("启用时渲染状态卡片与操作按钮", async () => {
    mockStatus.mockResolvedValue(ENABLED_STATUS);
    render(<ObsidianPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("obsidian-status-card")).toBeInTheDocument();
    });
    expect(screen.getByText("/home/user/vault")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByTestId("obsidian-actions")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "增量同步（仅变更文件）" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "全量重扫（所有 .md 文件）" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "启动实时监听" })).toBeInTheDocument();
  });

  it("增量同步：调用 API 并展示结果指标", async () => {
    const user = userEvent.setup();
    mockStatus.mockResolvedValue(ENABLED_STATUS);
    mockSync.mockResolvedValue({
      status: "ok",
      scanned: 10,
      imported: 3,
      skipped: 6,
      failed: 1,
      errors: ["note.md: 解析错误"],
    });
    render(<ObsidianPanel />);

    await waitFor(() => expect(screen.getByTestId("obsidian-actions")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "增量同步（仅变更文件）" }));

    await waitFor(() => expect(mockSync).toHaveBeenCalledWith(true));
    await waitFor(() => {
      expect(screen.getByTestId("obsidian-sync-result")).toBeInTheDocument();
    });
    // 四个指标数字
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    // 错误详情
    expect(screen.getByTestId("obsidian-sync-errors")).toBeInTheDocument();
    expect(screen.getByText(/note\.md: 解析错误/)).toBeInTheDocument();
    // Toast 成功提示（failed>0 用 danger）
    expect(showToast).toHaveBeenCalledWith(
      expect.stringContaining("失败 1"),
      "danger",
    );
  });

  it("全量重扫：调用 API 带 incremental=false", async () => {
    const user = userEvent.setup();
    mockStatus.mockResolvedValue(ENABLED_STATUS);
    mockSync.mockResolvedValue({
      status: "ok",
      scanned: 20,
      imported: 20,
      skipped: 0,
      failed: 0,
      errors: [],
    });
    render(<ObsidianPanel />);

    await waitFor(() => expect(screen.getByTestId("obsidian-actions")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "全量重扫（所有 .md 文件）" }));

    await waitFor(() => expect(mockSync).toHaveBeenCalledWith(false));
    await waitFor(() => {
      expect(screen.getByTestId("obsidian-sync-result")).toBeInTheDocument();
    });
    // 无错误详情区
    expect(screen.queryByTestId("obsidian-sync-errors")).not.toBeInTheDocument();
  });

  it("同步中：按钮禁用并显示「同步中...」", async () => {
    const user = userEvent.setup();
    mockStatus.mockResolvedValue(ENABLED_STATUS);
    let resolveFn!: (v: unknown) => void;
    mockSync.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFn = resolve;
        }) as Promise<any>,
    );
    render(<ObsidianPanel />);

    await waitFor(() => expect(screen.getByTestId("obsidian-actions")).toBeInTheDocument());

    const syncBtn = screen.getByRole("button", { name: "增量同步（仅变更文件）" });
    await user.click(syncBtn);

    await waitFor(() => {
      expect(syncBtn).toBeDisabled();
      expect(syncBtn).toHaveTextContent("同步中...");
    });

    // 释放悬挂 promise
    resolveFn({ status: "ok", scanned: 1, imported: 1, skipped: 0, failed: 0, errors: [] });
    // loadStatus 会触发 loading=true 再 false，按钮会重新挂载
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "增量同步（仅变更文件）" })).not.toBeDisabled();
    });
  });

  it("同步失败：展示错误信息", async () => {
    const user = userEvent.setup();
    mockStatus.mockResolvedValue(ENABLED_STATUS);
    mockSync.mockRejectedValue(new Error("vault 路径无效"));
    render(<ObsidianPanel />);

    await waitFor(() => expect(screen.getByTestId("obsidian-actions")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "增量同步（仅变更文件）" }));

    expect(await screen.findByText("vault 路径无效")).toBeInTheDocument();
    expect(showToast).toHaveBeenCalledWith("同步失败：vault 路径无效", "danger");
  });

  it("启动监听：调用 watch API 并刷新状态", async () => {
    const user = userEvent.setup();
    // 首次加载 watching=false，启动后第二次加载 watching=true
    mockStatus.mockResolvedValueOnce(ENABLED_STATUS).mockResolvedValueOnce({
      ...ENABLED_STATUS,
      watching: true,
    });
    mockWatch.mockResolvedValue({ status: "watching", watching: true });
    render(<ObsidianPanel />);

    await waitFor(() => expect(screen.getByTestId("obsidian-actions")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "启动实时监听" }));

    await waitFor(() => expect(mockWatch).toHaveBeenCalledWith(true));
    await waitFor(() => {
      expect(showToast).toHaveBeenCalledWith("实时监听已启动", "success");
    });
  });

  it("停止监听：调用 watch API enable=false", async () => {
    const user = userEvent.setup();
    const watchingStatus = { ...ENABLED_STATUS, watching: true };
    mockStatus.mockResolvedValueOnce(watchingStatus).mockResolvedValueOnce(ENABLED_STATUS);
    mockWatch.mockResolvedValue({ status: "stopped", watching: false });
    render(<ObsidianPanel />);

    await waitFor(() => expect(screen.getByTestId("obsidian-actions")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "停止实时监听" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "停止实时监听" }));

    await waitFor(() => expect(mockWatch).toHaveBeenCalledWith(false));
    await waitFor(() => {
      expect(showToast).toHaveBeenCalledWith("实时监听已停止", "success");
    });
  });

  it("watchdog 不可用时不渲染监听按钮", async () => {
    mockStatus.mockResolvedValue({ ...ENABLED_STATUS, watchdog_available: false });
    render(<ObsidianPanel />);

    await waitFor(() => expect(screen.getByTestId("obsidian-actions")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /实时监听/ })).not.toBeInTheDocument();
    expect(screen.getByText("watchdog 未安装")).toBeInTheDocument();
  });

  it("状态加载失败：展示错误信息", async () => {
    mockStatus.mockRejectedValue(new Error("网络错误"));
    render(<ObsidianPanel />);

    expect(await screen.findByText("网络错误")).toBeInTheDocument();
  });

  it("最后同步时间格式化为本地时间", async () => {
    mockStatus.mockResolvedValue({
      ...ENABLED_STATUS,
      last_sync: "2026-07-30T10:00:00Z",
    });
    render(<ObsidianPanel />);

    await waitFor(() => expect(screen.getByTestId("obsidian-status-card")).toBeInTheDocument());
    // toLocaleString("zh-CN") 格式包含日期和时间
    const timeEl = screen.getByText(/2026/);
    expect(timeEl).toBeInTheDocument();
  });

  it("从未同步时显示「从未同步」", async () => {
    mockStatus.mockResolvedValue({ ...ENABLED_STATUS, last_sync: null });
    render(<ObsidianPanel />);

    await waitFor(() => expect(screen.getByTestId("obsidian-status-card")).toBeInTheDocument());
    expect(screen.getByText("从未同步")).toBeInTheDocument();
  });
});
