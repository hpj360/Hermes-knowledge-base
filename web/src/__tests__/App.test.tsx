import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
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
    // 实验室相关方法
    labDaily: vi.fn().mockResolvedValue({ title: null, reason: "empty" }),
    labRecipes: vi.fn().mockResolvedValue({ items: [] }),
    labDashboard: vi.fn().mockResolvedValue(null),
    history: vi.fn().mockResolvedValue({ total: 0, items: [] }),
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

/**
 * 在主导航中查找链接文本。
 * 作用域限定在 nav 内，避免与 DashboardPanel 数据卡标签（文档/问答/配方）
 * 发生全局 getByText 多匹配冲突。
 */
function getNavLink(text: string) {
  return within(screen.getByLabelText("主导航")).getByText(text);
}

describe("App", () => {
  it("冒烟测试：能渲染不崩溃", async () => {
    const { container } = render(<App />);
    expect(container).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText("Hermes 知识库")).toBeInTheDocument();
    });
  });

  it("侧边导航包含实验室与配方入口", async () => {
    render(<App />);
    await waitFor(() => {
      expect(getNavLink("实验室")).toBeInTheDocument();
      expect(getNavLink("配方")).toBeInTheDocument();
    });
  });

  it("点击「实验室」切换到 LabPanel", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(getNavLink("实验室")).toBeInTheDocument());
    await user.click(getNavLink("实验室"));
    await waitFor(() => {
      expect(screen.getByText("🧪 鸡尾酒实验室")).toBeInTheDocument();
    });
  });

  it("点击「配方」切换到 RecipePanel", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(getNavLink("配方")).toBeInTheDocument());
    await user.click(getNavLink("配方"));
    await waitFor(() => {
      expect(screen.getByText("📝 配方治理")).toBeInTheDocument();
    });
  });
});

// ════════════════════════════════════════════════════════════════════
// 产品重构：分组导航 + 首页 Dashboard + 设置中心
// ════════════════════════════════════════════════════════════════════
describe("产品重构：分组导航与 IA", () => {
  it("IA：导航包含首页 + 知识区(问答/文档) + 调酒区(配方/实验室) + 设置", async () => {
    render(<App />);
    await waitForAppReady();
    const nav = screen.getByLabelText("主导航");
    expect(nav).toHaveTextContent("首页");
    expect(nav).toHaveTextContent("问答");
    expect(nav).toHaveTextContent("文档");
    expect(nav).toHaveTextContent("配方");
    expect(nav).toHaveTextContent("实验室");
    expect(nav).toHaveTextContent("设置");
    // 旧的「管理」tab 不应再出现
    expect(nav).not.toHaveTextContent("管理");
  });

  it("默认路径 / 展示首页 Dashboard", async () => {
    render(<App />);
    await waitForAppReady();
    // DashboardPanel 渲染：展示「从知识到实践」价值主张
    await waitFor(() => {
      expect(screen.getByText("从知识到实践")).toBeInTheDocument();
    });
  });

  it("点击「文档」切换到 DocumentList", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    await user.click(getNavLink("文档"));
    await waitFor(() => {
      expect(screen.getByText("知识库为空")).toBeInTheDocument();
    });
  });

  it("点击「设置」切换到 TagPanel", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    await user.click(screen.getByText("设置"));
    await waitFor(() => {
      // SettingsPanel 默认渲染 TagPanel；"标签管理"同时出现在子模块 tab 与 TagPanel 标题
      expect(screen.getAllByText("标签管理").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("导航 active 状态：点击实验室后实验室 tab 带 aria-current", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    await user.click(getNavLink("实验室"));
    await waitFor(() => {
      expect(screen.getByText("🧪 鸡尾酒实验室")).toBeInTheDocument();
    });
    const labLink = getNavLink("实验室").closest("a");
    expect(labLink).not.toBeNull();
    expect(labLink?.getAttribute("aria-current")).toBe("page");
  });

  it("深链接 /recipes/new 直接进入配方编辑器（创建模式）", async () => {
    window.history.replaceState({}, "", "/recipes/new");
    render(<App />);
    await waitForAppReady();
    await waitFor(() => {
      expect(screen.getByText("创作新配方")).toBeInTheDocument();
    });
  });

  it("深链接 /recipes/:id/edit 进入配方编辑器（编辑模式）", async () => {
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
    await waitFor(() => {
      expect(screen.getByText("返回列表")).toBeInTheDocument();
    });
  });

  it("URL chunk 参数同步：/docs/:id?chunk=5 解析为 highlightChunk", async () => {
    window.history.replaceState({}, "", "/docs/doc-1?chunk=5");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("返回列表")).toBeInTheDocument();
    });
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

  it("文档 tab 内有「导入文档」按钮（上下文感知导入）", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    await user.click(getNavLink("文档"));
    await waitFor(() => {
      expect(screen.getByText("知识库为空")).toBeInTheDocument();
    });
    // 文档 tab 筛选栏应有「导入文档」按钮
    expect(screen.getByRole("button", { name: "导入文档" })).toBeInTheDocument();
  });

  it("空库时首页与顶部都展示「导入种子知识」按钮", async () => {
    const { api } = await import("../api");
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    // 首页空库引导卡片 + 顶部都有「导入种子知识」按钮
    const seedBtns = screen.getAllByRole("button", { name: "导入种子知识" });
    expect(seedBtns.length).toBeGreaterThanOrEqual(1);
    await user.click(seedBtns[0]);
    await waitFor(() => {
      expect(screen.getByText("请确认")).toBeInTheDocument();
    });
    const confirmBtn = screen.getByRole("button", { name: "确认" });
    await user.click(confirmBtn);
    await waitFor(() => {
      expect(api.seed).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText(/导入完成：5 篇成功/)).toBeInTheDocument();
    });
  });

  it("auth_enabled=true 时展示「退出」按钮，点击触发 logout", async () => {
    const { api } = await import("../api");
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
    const logoutBtn = await screen.findByRole("button", { name: "退出" });
    await user.click(logoutBtn);
    expect(api.logout).toHaveBeenCalled();
  });

  it("导航 tab 数量恰好为 6（首页/问答/文档/配方/实验室/设置）", async () => {
    render(<App />);
    await waitForAppReady();
    const nav = screen.getByLabelText("主导航");
    const links = nav.querySelectorAll("a");
    expect(links.length).toBe(6);
  });

  it("导航分组：知识区与调酒区之间有分隔符", async () => {
    render(<App />);
    await waitForAppReady();
    const nav = screen.getByLabelText("主导航");
    // 分隔符为 aria-hidden 的 span
    const dividers = nav.querySelectorAll('span[aria-hidden="true"]');
    expect(dividers.length).toBeGreaterThanOrEqual(2);
  });

  // 覆盖 App.tsx line 153：handleSeed catch 块（导入种子失败时的错误处理）
  it("handleSeed 失败时 showToast 显示导入失败信息", async () => {
    const { api } = await import("../api");
    vi.mocked(api.seed).mockRejectedValueOnce(new Error("网络错误"));
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    const seedBtns = screen.getAllByRole("button", { name: "导入种子知识" });
    await user.click(seedBtns[0]);
    await waitFor(() => {
      expect(screen.getByText("请确认")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "确认" }));
    await waitFor(() => {
      expect(screen.getByText(/导入失败：网络错误/)).toBeInTheDocument();
    });
  });

  // 覆盖 App.tsx lines 301-304：ImportDialog 条件渲染（showImport=true）
  it("点击「导入文档」按钮渲染 ImportDialog 对话框", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    await user.click(getNavLink("文档"));
    await waitFor(() => {
      expect(screen.getByText("知识库为空")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "导入文档" }));
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    // ImportDialog 的 Modal 标题为「导入文档」，且包含纯文本/单文件/批量上传 tab
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("导入文档");
    expect(dialog).toHaveTextContent("纯文本");
    expect(dialog).toHaveTextContent("批量上传");
  });

  // 覆盖 App.tsx line 139：handleSelectDoc 中的 navigate(`/docs/${docId}`)
  it("handleSelectDoc：点击文档列表中的文档标题跳转到 /docs/:id", async () => {
    const { api } = await import("../api");
    vi.mocked(api.listDocuments).mockResolvedValueOnce({
      total: 1,
      items: [
        {
          doc_id: "doc-1",
          title: "测试文档一",
          source_type: "local",
          file_type: "md",
          chunk_count: 3,
          category: "wine",
          tags: [],
          created_at: "2026-01-01T00:00:00Z",
        },
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();
    await user.click(getNavLink("文档"));
    await waitFor(() => {
      expect(screen.getByText("测试文档一")).toBeInTheDocument();
    });
    await user.click(screen.getByText("测试文档一"));
    await waitFor(() => {
      expect(window.location.pathname).toBe("/docs/doc-1");
    });
  });

  // 覆盖 App.tsx lines 142-143：handleBackToList 中的 navigate("/docs")
  it("handleBackToList：详情页点击「返回列表」跳转到 /docs", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/docs/doc-1");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("返回列表")).toBeInTheDocument();
    });
    await user.click(screen.getByText("返回列表"));
    await waitFor(() => {
      expect(window.location.pathname).toBe("/docs");
    });
  });
});

// ════════════════════════════════════════════════════════════════════
// 移动端响应式导航：底部 tab bar 与顶部 nav 根据视口宽度切换
// ════════════════════════════════════════════════════════════════════
describe("响应式导航：底部 tab bar 与顶部 nav 切换", () => {
  /** mock window.matchMedia：jsdom 不实现媒体查询，需手动控制 matches 值 */
  function mockMatchMedia(matches: boolean) {
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })) as unknown as typeof window.matchMedia;
  }

  // 保存原始 matchMedia 以便 afterEach 恢复，避免污染其他 describe 块
  let originalMatchMedia: typeof window.matchMedia;

  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
    // 默认桌面端（与 setup.ts 一致）
    mockMatchMedia(false);
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  it("移动端 (<768px)：渲染底部 tab bar（移动导航），隐藏顶部主导航", async () => {
    mockMatchMedia(true);
    render(<App />);
    await waitForAppReady();

    // 底部 tab bar 渲染
    const bottomNav = screen.getByRole("navigation", { name: "移动导航" });
    expect(bottomNav).toBeInTheDocument();

    // 顶部主导航不渲染
    expect(screen.queryByRole("navigation", { name: "主导航" })).toBeNull();
  });

  it("移动端：底部 tab bar 包含 5 个 tab（首页/问答/配方/实验室/设置）", async () => {
    mockMatchMedia(true);
    render(<App />);
    await waitForAppReady();

    const bottomNav = screen.getByRole("navigation", { name: "移动导航" });
    const links = bottomNav.querySelectorAll("a");
    expect(links.length).toBe(5);
    expect(bottomNav).toHaveTextContent("首页");
    expect(bottomNav).toHaveTextContent("问答");
    expect(bottomNav).toHaveTextContent("配方");
    expect(bottomNav).toHaveTextContent("实验室");
    expect(bottomNav).toHaveTextContent("设置");
  });

  it("桌面端 (≥768px)：渲染顶部主导航，隐藏底部 tab bar", async () => {
    mockMatchMedia(false);
    render(<App />);
    await waitForAppReady();

    // 顶部主导航渲染
    const topNav = screen.getByRole("navigation", { name: "主导航" });
    expect(topNav).toBeInTheDocument();

    // 底部 tab bar 不渲染
    expect(screen.queryByRole("navigation", { name: "移动导航" })).toBeNull();
  });

  it("移动端：点击底部 tab「配方」导航到 /recipes", async () => {
    mockMatchMedia(true);
    const user = userEvent.setup();
    render(<App />);
    await waitForAppReady();

    const bottomNav = screen.getByRole("navigation", { name: "移动导航" });
    const recipeLink = bottomNav.querySelector('a[href="/recipes"]') as HTMLAnchorElement;
    expect(recipeLink).not.toBeNull();
    await user.click(recipeLink);
    await waitFor(() => {
      expect(window.location.pathname).toBe("/recipes");
    });
  });
});

