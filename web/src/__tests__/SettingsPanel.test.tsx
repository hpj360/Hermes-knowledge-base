/** SettingsPanel 测试：子模块 tab 切换 + 默认渲染 TagPanel */
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock api — TagPanel 挂载时调用 listTags，返回空数组
vi.mock("../api", () => ({
  api: {
    listTags: vi.fn().mockResolvedValue({ total: 0, items: [] }),
  },
}));

import { SettingsPanel } from "../components/SettingsPanel";

describe("SettingsPanel", () => {
  it("默认展示标签管理子模块（渲染 TagPanel）", async () => {
    render(<SettingsPanel onChange={() => {}} />);

    // TagPanel 的“创建新标签”区域出现，说明标签管理子模块已渲染
    await waitFor(() => {
      expect(screen.getByText("创建新标签")).toBeInTheDocument();
    });

    // “标签管理” tab 处于激活态
    expect(screen.getByRole("button", { name: "标签管理" })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  it("点击「数据导出」tab 切换到数据导出子模块", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "数据导出" }));

    await waitFor(() => {
      expect(screen.getByText("数据导出功能即将上线")).toBeInTheDocument();
    });

    // 数据导出 tab 激活，标签管理内容不再展示
    expect(
      screen.getByRole("button", { name: "数据导出" })
    ).toHaveAttribute("aria-current", "page");
    expect(screen.queryByText("创建新标签")).not.toBeInTheDocument();
  });

  it("点击「审计日志」tab 切换到审计日志子模块", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "审计日志" }));

    await waitFor(() => {
      expect(screen.getByText("审计日志功能即将上线")).toBeInTheDocument();
    });

    expect(
      screen.getByRole("button", { name: "审计日志" })
    ).toHaveAttribute("aria-current", "page");
  });
});
