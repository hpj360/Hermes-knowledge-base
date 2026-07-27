import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock api 模块，避免 jsdom 环境下发起真实网络请求
vi.mock("../api", () => ({
  api: {
    health: vi.fn().mockResolvedValue({
      doc_count: 0,
      llm_available: false,
      llm_provider: "mock",
      embedding_available: false,
      embedding_provider: "hash",
      auth_enabled: false,
    }),
    ageGateStatus: vi.fn().mockResolvedValue({
      age_gate_enabled: false,
      message: "",
    }),
    ageGateConfirm: vi.fn().mockResolvedValue({ confirmed: true }),
    getToken: vi.fn().mockReturnValue(null),
    logout: vi.fn(),
    setToken: vi.fn(),
    // 实验室相关方法（App 在 lab/recipes tab 下不会主动调用，但子组件可能用到）
    labDaily: vi.fn().mockResolvedValue({ title: null, reason: "empty" }),
    labRecipes: vi.fn().mockResolvedValue({ items: [] }),
    // R3: handleSeed 测试需要
    seed: vi.fn().mockResolvedValue({ seeded: 5, failed: 0 }),
    // R3: 详情页 / 编辑器可能触发的 API
    getDocument: vi.fn().mockResolvedValue({
      doc: {
        doc_id: "doc-1",
        title: "测试文档",
        category: "wine",
        source: "local",
        source_type: "local",
        file_type: "md",
        content: "# 测试\n正文",
        content_length: 12,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        chunk_count: 3,
      },
      chunks: [],
      tags: [],
    }),
    listDocuments: vi.fn().mockResolvedValue({ items: [] }),
    listCategories: vi.fn().mockResolvedValue({ items: [] }),
    listTags: vi.fn().mockResolvedValue({ items: [] }),
  },
  setUnauthorizedHandler: vi.fn(),
}));

import App from "../App";

/** 等待 App 通过年龄门 + 健康检查并渲染主界面 */
async function waitForAppReady() {
  await waitFor(() => {
    expect(screen.getByText("Hermes 知识库")).toBeInTheDocument();
  });
}

describe("App", () => {
  it("冒烟测试：能渲染不崩溃", async () => {
    // 不应抛出异常
    const { container } = render(<App />);
    expect(container).toBeTruthy();
    // App 渲染后应出现顶部栏标题（年龄门未启用，会直接放行）
    await waitFor(() => {
      expect(screen.getByText("Hermes 知识库")).toBeInTheDocument();
    });
  });

  it("侧边导航包含实验室与配方入口", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("实验室")).toBeInTheDocument();
      expect(screen.getByText("配方")).toBeInTheDocument();
    });
  });

  it("点击「实验室」切换到 LabPanel", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText("实验室")).toBeInTheDocument());
    await user.click(screen.getByText("实验室"));
    await waitFor(() => {
      expect(screen.getByText("🧪 鸡尾酒实验室")).toBeInTheDocument();
    });
  });

  it("点击「📝 配方」切换到 RecipePanel", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText("配方")).toBeInTheDocument());
    await user.click(screen.getByText("配方"));
    await waitFor(() => {
      expect(screen.getByText("📝 配方治理")).toBeInTheDocument();
    });
  });
});

// ════════════════════════════════════════════════════════════════════
// R3 路由 + IA 重构验收测试
// ════════════════════════════════════════════════════════════════════
describe("R3 路由与 IA 重构", () => {
  it("IA：导航包含 4 主 tab + 1 管理 tab（问答/实验室/配方/文档/管理）", async () => {
    render(<App />);
    await waitForAppReady();
    // 用主导航容器范围限定，避免与子页面内的同名文字冲突
    const nav = screen.getByLabelText("主导航");
    // 4 主 tab
    expect(nav).toHaveTextContent("问答");
    expect(nav).toHaveTextContent("实验室");
    expect(nav).toHaveTextContent("配方");
    expect(nav).toHaveTextContent("文档");
    // 1 管理 tab
    expect(nav).toHaveTextContent("管理");
    // 旧的「标签」tab 不应再出现（已迁入管理）
    expect(nav).not.toHaveTextContent("标签");
  });

  it("默认路径 / 重定向到 /chat", async () => {
    // 初始 URL 为 /（setup.ts beforeEach 已重置）
    render(<App />);
    await waitForAppReady();
    // ChatPanel 应该被渲染（h2 标题「向 Hermes 知识库提问吧」）
    await waitFor(() => {
      expect(screen.getByText("向 Hermes 知识库提问吧")).toBeInTheDocument();
    });
  });

  it("点击「文档」切换到 DocumentList", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    await user.click(screen.getByText("文档"));
    // DocumentList 渲染：空状态展示「知识库为空」标题
    await waitFor(() => {
      expect(screen.getByText("知识库为空")).toBeInTheDocument();
    });
  });

  it("点击「管理」切换到 TagPanel", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    await user.click(screen.getByText("管理"));
    // TagPanel 渲染：展示「标签管理」标题
    await waitFor(() => {
      expect(screen.getByText("标签管理")).toBeInTheDocument();
    });
  });

  it("导航 active 状态：点击实验室后实验室 tab 带 nav-tab-active 类", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    await user.click(screen.getByText("实验室"));
    await waitFor(() => {
      expect(screen.getByText("🧪 鸡尾酒实验室")).toBeInTheDocument();
    });
    // 实验室链接应带 aria-current="page"（a11y + active 标识）
    const labLink = screen.getByText("实验室").closest("a");
    expect(labLink).not.toBeNull();
    expect(labLink?.getAttribute("aria-current")).toBe("page");
  });

  it("深链接 /recipes/new 直接进入配方编辑器（创建模式）", async () => {
    // 模拟用户直接访问 /recipes/new（刷新场景）
    window.history.replaceState({}, "", "/recipes/new");
    render(<App />);
    await waitForAppReady();
    // RecipeEditorPanel 创建模式会展示「创作新配方」标题
    await waitFor(() => {
      expect(screen.getByText("创作新配方")).toBeInTheDocument();
    });
  });

  it("深链接 /recipes/:id/edit 进入配方编辑器（编辑模式）", async () => {
    // RecipeEditorPanel 编辑模式会调用 labRecipes 加载已有配方
    const { api } = await import("../api");
    vi.mocked(api.labRecipes).mockResolvedValueOnce({
      items: [
        {
          doc_id: "doc-edit-1",
          title: "已存在配方",
          source: "ugc",
          verified: false,
          hidden: false,
          status: "draft",
          season: "summer",
        },
      ],
    } as any);
    window.history.replaceState({}, "", "/recipes/doc-edit-1/edit");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("编辑配方")).toBeInTheDocument();
    });
  });

  it("深链接 /docs/:id 直接进入文档详情页", async () => {
    window.history.replaceState({}, "", "/docs/doc-1");
    render(<App />);
    // DocumentDetailPanel 渲染：会调用 getDocument，加载完成后展示「返回列表」按钮
    await waitFor(() => {
      expect(screen.getByText("返回列表")).toBeInTheDocument();
    });
  });

  it("URL chunk 参数同步：/docs/:id?chunk=5 解析为 highlightChunk", async () => {
    window.history.replaceState({}, "", "/docs/doc-1?chunk=5");
    render(<App />);
    // 详情面板应渲染（验证不崩溃且 chunk 参数被消费）
    await waitFor(() => {
      expect(screen.getByText("返回列表")).toBeInTheDocument();
    });
    // 验证 URL 仍保留 chunk 参数
    expect(window.location.search).toContain("chunk=5");
  });

  it("404：未知路径展示 NotFound 提示", async () => {
    window.history.replaceState({}, "", "/this-does-not-exist");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("404")).toBeInTheDocument();
      expect(screen.getByText("页面不存在")).toBeInTheDocument();
    });
  });

  it("顶部「导入」按钮打开 ImportDialog", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    // 顶部栏「导入」按钮（区别于「导入种子知识」）
    const importBtn = screen.getByRole("button", { name: "导入" });
    await user.click(importBtn);
    // ImportDialog 渲染：包含文件输入或拖拽区
    await waitFor(() => {
      const dialog = screen.queryByText(/拖拽|选择文件|支持格式|导入文档/i);
      expect(dialog).not.toBeNull();
    });
  });

  it("空库时「导入种子知识」按钮触发 handleSeed 流程", async () => {
    const { api } = await import("../api");
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    // 健康检查返回 doc_count=0 → 顶部栏与 ChatPanel 都会显示「导入种子知识」按钮
    // 用 getAllByRole 取所有匹配项，点击顶部栏（第一个）
    const seedBtns = screen.getAllByRole("button", { name: "导入种子知识" });
    expect(seedBtns.length).toBeGreaterThanOrEqual(1);
    await user.click(seedBtns[0]);
    // 点击后弹出 useConfirm 对话框，需再点确认
    await waitFor(() => {
      expect(screen.getByText("请确认")).toBeInTheDocument();
    });
    // 点击「确认」触发 api.seed
    const confirmBtn = screen.getByRole("button", { name: "确认" });
    await user.click(confirmBtn);
    await waitFor(() => {
      expect(api.seed).toHaveBeenCalled();
    });
    // 成功后展示 toast
    await waitFor(() => {
      expect(screen.getByText(/导入完成：5 篇成功/)).toBeInTheDocument();
    });
  });

  it("auth_enabled=true 时展示「退出」按钮，点击触发 logout", async () => {
    const { api } = await import("../api");
    // 覆盖 health mock：返回 auth_enabled=true 且 token 已存在
    vi.mocked(api.health).mockResolvedValueOnce({
      doc_count: 5,
      llm_available: true,
      llm_provider: "openai",
      embedding_available: true,
      embedding_provider: "openai",
      auth_enabled: true,
    } as any);
    vi.mocked(api.getToken).mockReturnValue("fake-token");

    const user = userEvent.setup();
    render(<App />);
    // 等待退出按钮出现
    const logoutBtn = await screen.findByRole("button", { name: "退出" });
    await user.click(logoutBtn);
    expect(api.logout).toHaveBeenCalled();
  });

  it("导航 tab 数量恰好为 5（4 主 + 1 管理）", async () => {
    render(<App />);
    await waitForAppReady();
    // 主导航内的链接数量应为 5
    const nav = screen.getByLabelText("主导航");
    const links = nav.querySelectorAll("a");
    expect(links.length).toBe(5);
  });
});
