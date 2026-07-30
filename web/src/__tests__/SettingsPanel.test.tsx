/** SettingsPanel 测试：子模块 tab 切换 + 数据导出 + 审计日志 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// vi.mock 工厂是 hoisted 的，所以 mock 变量也必须在工厂内部声明
vi.mock("../api", () => ({
  api: {
    listTags: vi.fn().mockResolvedValue({ total: 0, items: [] }),
    listAudit: vi.fn().mockResolvedValue({
      total: 0,
      limit: 20,
      offset: 0,
      items: [],
    }),
    feedbackList: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    }),
    exportAll: vi.fn(),
    importBackup: vi.fn(),
    health: vi.fn().mockResolvedValue({ multiuser: false }),
    obsidianStatus: vi.fn().mockResolvedValue({
      enabled: false,
      vault_path: "",
      watch_enabled: false,
      watchdog_available: false,
      watching: false,
      synced_docs: 0,
      last_sync: null,
    }),
  },
}));

// Mock showToast 以避免全局 listener 累积
vi.mock("../components/Toast", () => ({
  showToast: vi.fn(),
}));

import { api } from "../api";
import { SettingsPanel } from "../components/SettingsPanel";

// 取出 mock 函数（vi.mocked 返回类型化的 mock）
const mockListTags = vi.mocked(api.listTags);
const mockListAudit = vi.mocked(api.listAudit);
const mockExportAll = vi.mocked(api.exportAll);
const mockImportBackup = vi.mocked(api.importBackup);
const mockFeedbackList = vi.mocked(api.feedbackList);

describe("SettingsPanel", () => {
  let originalCreateObjectURL: typeof URL.createObjectURL;
  let originalRevokeObjectURL: typeof URL.revokeObjectURL;
  let originalAnchorClick: typeof HTMLAnchorElement.prototype.click;

  beforeEach(() => {
    mockListTags.mockClear();
    mockListAudit.mockClear();
    mockExportAll.mockClear();
    mockImportBackup.mockClear();
    mockListTags.mockResolvedValue({ total: 0, items: [] });
    mockListAudit.mockResolvedValue({ total: 0, limit: 20, offset: 0, items: [] });

    // jsdom 不支持 navigation（<a>.click() 触发），全局 mock 掉
    originalCreateObjectURL = URL.createObjectURL;
    originalRevokeObjectURL = URL.revokeObjectURL;
    originalAnchorClick = HTMLAnchorElement.prototype.click;
    URL.createObjectURL = vi.fn().mockReturnValue("blob:mock");
    URL.revokeObjectURL = vi.fn();
    HTMLAnchorElement.prototype.click = vi.fn();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    HTMLAnchorElement.prototype.click = originalAnchorClick;
  });

  it("默认展示标签管理子模块（渲染 TagPanel）", async () => {
    render(<SettingsPanel onChange={() => {}} />);

    // TagPanel 的"创建新标签"区域出现，说明标签管理子模块已渲染
    await waitFor(() => {
      expect(screen.getByText("创建新标签")).toBeInTheDocument();
    });

    // "标签管理" tab 处于激活态
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
      expect(screen.getByText("数据导出与恢复")).toBeInTheDocument();
    });

    // 数据导出 tab 激活，标签管理内容不再展示
    expect(
      screen.getByRole("button", { name: "数据导出" })
    ).toHaveAttribute("aria-current", "page");
    expect(screen.queryByText("创建新标签")).not.toBeInTheDocument();

    // 应有「下载备份 JSON」与「上传恢复」两个按钮
    expect(screen.getByRole("button", { name: "下载备份 JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "上传恢复" })).toBeInTheDocument();
  });

  it("点击「审计日志」tab 切换到审计日志子模块（自动加载列表）", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "审计日志" }));

    // 等待审计面板加载（筛选按钮出现说明 AuditPanel 已渲染）
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "筛选" })).toBeInTheDocument();
    });

    expect(
      screen.getByRole("button", { name: "审计日志" })
    ).toHaveAttribute("aria-current", "page");

    // 应自动调用 listAudit 一次
    expect(mockListAudit).toHaveBeenCalledTimes(1);
    // 应有筛选按钮
    expect(screen.getByRole("button", { name: "重置" })).toBeInTheDocument();
  });

  it("数据导出：点击「下载备份 JSON」触发 exportAll 调用", async () => {
    const blob = new Blob(["{}"], { type: "application/json" });
    mockExportAll.mockResolvedValueOnce(blob);

    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "数据导出" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "下载备份 JSON" })).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "下载备份 JSON" }));

    await waitFor(() => {
      expect(mockExportAll).toHaveBeenCalledTimes(1);
    });
  });

  it("数据导出：exportAll 失败时显示错误并触发 toast", async () => {
    mockExportAll.mockRejectedValueOnce(new Error("网络错误"));

    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "数据导出" }));
    await user.click(screen.getByRole("button", { name: "下载备份 JSON" }));

    // ErrorBanner 展示错误消息（msg = "网络错误"）
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("网络错误");
    });
  });

  it("数据导出：上传文件成功后展示导入结果", async () => {
    const result = {
      status: "imported",
      version: "1.0",
      counts: { documents: 5, chunks: 12 },
      failed_counts: {},
      errors: [],
      unknown_fields: {},
      total: 17,
      total_failed: 0,
    };
    mockImportBackup.mockResolvedValueOnce(result);

    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "数据导出" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "上传恢复" })).toBeInTheDocument()
    );

    // 找到隐藏的 file input 并触发 change
    const input = screen.getByLabelText("选择备份 JSON 文件") as HTMLInputElement;
    const file = new File(["{}"], "backup.json", { type: "application/json" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(mockImportBackup).toHaveBeenCalledWith(file);
    });

    // 展示结果：版本号、总成功行数
    await waitFor(() => {
      expect(screen.getByText("IMPORT RESULT")).toBeInTheDocument();
      expect(screen.getByText("17")).toBeInTheDocument();
    });
  });

  it("数据导出：上传文件失败时显示错误", async () => {
    mockImportBackup.mockRejectedValueOnce(new Error("文件格式错误"));

    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "数据导出" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "上传恢复" })).toBeInTheDocument()
    );

    const input = screen.getByLabelText("选择备份 JSON 文件") as HTMLInputElement;
    const file = new File(["{}"], "backup.json", { type: "application/json" });
    fireEvent.change(input, { target: { files: [file] } });

    // ErrorBanner 展示错误消息（msg = "文件格式错误"）
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("文件格式错误");
    });
  });

  it("审计日志：空列表时展示 EMPTY 占位", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "审计日志" }));

    await waitFor(() => {
      expect(screen.getByText("暂无审计日志")).toBeInTheDocument();
    });
  });

  it("审计日志：渲染列表项并展示 action/target/user", async () => {
    mockListAudit.mockResolvedValueOnce({
      total: 2,
      limit: 20,
      offset: 0,
      items: [
        {
          id: 1,
          action: "import",
          target_type: "document",
          target_id: "doc_abc",
          user: "admin",
          meta: { filename: "test.md" },
          created_at: "2026-07-29T10:00:00Z",
        },
        {
          id: 2,
          action: "delete",
          target_type: "document",
          target_id: "doc_xyz",
          user: "anonymous",
          meta: {},
          created_at: "2026-07-29T11:00:00Z",
        },
      ],
    });

    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "审计日志" }));

    // 等待 listAudit 调用完成
    await waitFor(() => {
      expect(mockListAudit).toHaveBeenCalledTimes(1);
    });

    // 列表项中应展示：target_id（doc_abc / doc_xyz）与 meta 内容
    // 注意：action 文本（import/delete）也出现在 select 选项中，需用 target_id 精确断言
    // 文本被 React 渲染为 "document · doc_abc"，需用 regex 匹配
    await waitFor(() => {
      expect(screen.getByText(/doc_abc/)).toBeInTheDocument();
      expect(screen.getByText(/doc_xyz/)).toBeInTheDocument();
    });
    // meta JSON 应渲染
    expect(screen.getByText(/test\.md/)).toBeInTheDocument();
  });

  it("审计日志：切换 action 筛选触发重新加载并重置 offset", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "审计日志" }));

    await waitFor(() => {
      expect(mockListAudit).toHaveBeenCalledTimes(1);
    });

    // 选择 action = import
    const select = screen.getByLabelText("动作") as HTMLSelectElement;
    await user.selectOptions(select, "import");

    await waitFor(() => {
      expect(mockListAudit).toHaveBeenCalledTimes(2);
    });

    // 最后一次调用应携带 action=import, offset=0
    const calls = mockListAudit.mock.calls;
    const lastCall = calls[calls.length - 1]?.[0];
    expect(lastCall).toMatchObject({ action: "import", offset: 0 });
  });

  it("审计日志：分页 — 点击「下一页」增加 offset", async () => {
    // 25 条数据，PAGE_SIZE=20，应展示分页
    mockListAudit.mockResolvedValue({
      total: 25,
      limit: 20,
      offset: 0,
      items: Array.from({ length: 20 }, (_, i) => ({
        id: i + 1,
        action: "ask",
        target_type: "query",
        target_id: "",
        user: "anonymous",
        meta: {},
        created_at: "2026-07-29T10:00:00Z",
      })),
    });

    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("创建新标签")).toBeInTheDocument()
    );

    await user.click(screen.getByRole("button", { name: "审计日志" }));

    await waitFor(() => {
      expect(screen.getByText(/共 25 条/)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "下一页" }));

    await waitFor(() => {
      const calls = mockListAudit.mock.calls;
      const lastCall = calls[calls.length - 1]?.[0];
      expect(lastCall).toMatchObject({ offset: 20 });
    });
  });

  // -------------------------------------------------------------------------
  // V4-Phase1：Obsidian vault tab 集成
  // -------------------------------------------------------------------------
  it("vault 未启用时不渲染 Obsidian tab", async () => {
    vi.mocked(api.health).mockResolvedValue({ multiuser: false, vault_enabled: false } as any);
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() => expect(api.health).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Obsidian" })).not.toBeInTheDocument();
  });

  it("vault 启用时渲染 Obsidian tab 并可切换", async () => {
    const user = userEvent.setup();
    vi.mocked(api.health).mockResolvedValue({
      multiuser: false,
      vault_enabled: true,
    } as any);
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() => expect(screen.getByRole("button", { name: "Obsidian" })).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Obsidian" }));

    // ObsidianPanel 内部会调用 obsidianStatus
    await waitFor(() => {
      expect(api.obsidianStatus).toHaveBeenCalled();
    });
  });
});

// ==========================================================================
// V5：意见反馈汇总子模块（FeedbackListPanel）
// ==========================================================================
describe("SettingsPanel 意见反馈子模块", () => {
  beforeEach(() => {
    mockFeedbackList.mockReset();
    mockFeedbackList.mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    vi.mocked(api.health).mockResolvedValue({ multiuser: false } as any);
  });

  it("渲染「意见反馈」tab 并可切换", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() => expect(screen.getByText("创建新标签")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "意见反馈" }));

    // FeedbackListPanel 描述文本出现（说明面板已渲染）
    await waitFor(() => {
      expect(screen.getByText(/查看用户提交的结构化反馈/)).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: "意见反馈" }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("空列表展示 EMPTY 占位", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() => expect(screen.getByText("创建新标签")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "意见反馈" }));

    await waitFor(() => {
      expect(screen.getByText("暂无反馈")).toBeInTheDocument();
    });
  });

  it("渲染列表项（👍/👎 + 标签 + query + comment）", async () => {
    mockFeedbackList.mockResolvedValueOnce({
      items: [
        {
          log_id: 101,
          query: "金酒的核心风味是什么？",
          feedback: -1,
          comment: "答案把伏特加和金酒搞混了",
          tag: "inaccurate",
          created_at: "2026-07-31T10:00:00Z",
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });

    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() => expect(screen.getByText("创建新标签")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "意见反馈" }));

    await waitFor(() => {
      expect(screen.getByText("金酒的核心风味是什么？")).toBeInTheDocument();
    });
    expect(screen.getByText("答案把伏特加和金酒搞混了")).toBeInTheDocument();
    // log_id 渲染为 #101
    expect(screen.getByText("#101")).toBeInTheDocument();
  });

  it("点击标签筛选触发重新加载并重置 offset", async () => {
    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() => expect(screen.getByText("创建新标签")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "意见反馈" }));

    await waitFor(() => expect(mockFeedbackList).toHaveBeenCalledTimes(1));

    // 点击「答案不准」筛选按钮
    await user.click(screen.getByRole("button", { name: "答案不准" }));

    await waitFor(() => expect(mockFeedbackList).toHaveBeenCalledTimes(2));
    const calls = mockFeedbackList.mock.calls;
    const lastCall = calls[calls.length - 1];
    // feedbackList(tag?, limit?, offset?) — tag="inaccurate", offset=0
    expect(lastCall[0]).toBe("inaccurate");
    expect(lastCall[2]).toBe(0);
  });

  it("加载失败显示错误", async () => {
    mockFeedbackList.mockRejectedValueOnce(new Error("网络错误"));

    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() => expect(screen.getByText("创建新标签")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "意见反馈" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("网络错误");
    });
  });

  it("分页 — 点击下一页增加 offset", async () => {
    // FEEDBACK_PAGE_SIZE=50，需要 total > 50 才显示分页
    mockFeedbackList.mockResolvedValue({
      items: Array.from({ length: 50 }, (_, i) => ({
        log_id: i + 1,
        query: `问题 ${i}`,
        feedback: -1,
        comment: `评论 ${i}`,
        tag: "other",
        created_at: "2026-07-31T10:00:00Z",
      })),
      total: 75,
      limit: 50,
      offset: 0,
    });

    const user = userEvent.setup();
    render(<SettingsPanel onChange={() => {}} />);

    await waitFor(() => expect(screen.getByText("创建新标签")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "意见反馈" }));

    await waitFor(() => {
      expect(screen.getByText(/共 75 条/)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "下一页" }));

    await waitFor(() => {
      const calls = mockFeedbackList.mock.calls;
      const lastCall = calls[calls.length - 1];
      expect(lastCall[2]).toBe(50); // offset=50
    });
  });
});
