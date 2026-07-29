/** HistoryPanel 组件测试：渲染 / 时间筛选 / 搜索过滤 / 关键词高亮 / 空状态 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock api module — history 由测试控制返回值
vi.mock("../api", () => ({
  api: {
    history: vi.fn(),
  },
}));

import { api } from "../api";
import { HistoryPanel } from "../components/HistoryPanel";
import type { HistoryItem } from "../types";

// 两条测试数据：覆盖不同 query/answer/citations
const mockItems: HistoryItem[] = [
  {
    log_id: 1001,
    query: "金酒的核心风味是什么？",
    answer:
      "金酒（Gin）的核心风味来自杜松子（Juniper Berries），此外还常伴随芫荽、当归、柑橘皮等草本与香料气息。根据配方不同，风味可以从干燥辛香到柔和花香不等。",
    model: "gpt-4o-mini",
    latency_ms: 320,
    created_at: "2026-07-28T10:30:00Z",
    citations: [
      {
        doc_id: "doc_001",
        chunk_rowid: 3,
        title: "金酒百科",
        text: "金酒是一种以杜松子为核心的烈酒...",
      },
      {
        doc_id: "doc_002",
        chunk_rowid: 7,
        title: "烈酒风味指南",
        text: "杜松子是金酒风味的灵魂所在...",
      },
    ],
    feedback: 1,
  },
  {
    log_id: 1002,
    query: "威士忌和波本有什么区别？",
    answer:
      "波本威士忌（Bourbon）是美国特产，要求玉米占比≥51%；苏格兰威士忌（Scotch）以麦芽为原料，风味偏烟熏泥煤。",
    model: "gpt-4o-mini",
    latency_ms: 280,
    created_at: "2026-07-29T08:15:00Z",
    citations: [
      {
        doc_id: "doc_003",
        chunk_rowid: 12,
        title: "威士忌入门",
        text: "威士忌由谷物发酵蒸馏而成...",
      },
    ],
    feedback: 0,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe("HistoryPanel", () => {
  it("基本渲染：展示历史项的 query、答案摘要、时间、引用数", async () => {
    vi.mocked(api.history).mockResolvedValue({
      total: mockItems.length,
      items: mockItems,
    });

    render(<HistoryPanel />);

    // 等待 history 加载完成
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    // 应调用 history() 并传对象参数（默认 limit=50，无 date_from/date_to）
    expect(api.history).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 50 })
    );
    // 不应传 date_from/date_to（默认 all 模式）
    const callArgs = vi.mocked(api.history).mock.calls[0][0] as Record<string, unknown>;
    expect(callArgs.date_from).toBeUndefined();
    expect(callArgs.date_to).toBeUndefined();

    // 应展示两条历史项的 query
    expect(await screen.findByText(/金酒的核心风味是什么/)).toBeInTheDocument();
    expect(screen.getByText(/威士忌和波本有什么区别/)).toBeInTheDocument();

    // 应展示答案摘要（前 100 字片段）
    expect(screen.getByText(/杜松子/)).toBeInTheDocument();
    expect(screen.getByText(/玉米占比/)).toBeInTheDocument();

    // 应展示引用数：第一条 2 条引用，第二条 1 条引用
    expect(screen.getByText("引用 2")).toBeInTheDocument();
    expect(screen.getByText("引用 1")).toBeInTheDocument();

    // 应展示引用来源标题
    expect(screen.getByText("金酒百科")).toBeInTheDocument();
    expect(screen.getByText("威士忌入门")).toBeInTheDocument();

    // 应展示「共 2 条」计数
    expect(screen.getByText(/共 2 条/)).toBeInTheDocument();
  });

  it("时间筛选：默认「全部」模式不传 date_from/date_to", async () => {
    vi.mocked(api.history).mockResolvedValue({
      total: mockItems.length,
      items: mockItems,
    });

    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    const callArgs = vi.mocked(api.history).mock.calls[0][0] as Record<string, unknown>;
    expect(callArgs.date_from).toBeUndefined();
    expect(callArgs.date_to).toBeUndefined();
  });

  it("时间筛选：点击「近 7 天」触发重新加载并传 date_from/date_to", async () => {
    // 第一次：默认 all 模式
    vi.mocked(api.history).mockResolvedValueOnce({
      total: mockItems.length,
      items: mockItems,
    });
    // 第二次：7d 模式返回空
    vi.mocked(api.history).mockResolvedValueOnce({
      total: 0,
      items: [],
    });

    const user = userEvent.setup();
    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalledTimes(1));

    // 点击「近 7 天」按钮
    const btn7d = screen.getByRole("button", { name: "近 7 天" });
    await user.click(btn7d);

    // 应触发第二次调用，且带 date_from/date_to
    await waitFor(() => expect(api.history).toHaveBeenCalledTimes(2));
    const secondCallArgs = vi.mocked(api.history).mock.calls[1][0] as Record<string, unknown>;
    expect(secondCallArgs.date_from).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(secondCallArgs.date_to).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("时间筛选：「自定义」模式展示日期输入框并传自定义范围", async () => {
    vi.mocked(api.history).mockResolvedValue({
      total: mockItems.length,
      items: mockItems,
    });

    const user = userEvent.setup();
    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    // 初始不应展示自定义日期输入
    expect(screen.queryByLabelText("起始日期")).not.toBeInTheDocument();

    // 点击「自定义」按钮
    await user.click(screen.getByRole("button", { name: "自定义" }));

    // 应展示日期输入框
    expect(await screen.findByLabelText("起始日期")).toBeInTheDocument();
    expect(screen.getByLabelText("结束日期")).toBeInTheDocument();

    // 输入自定义日期范围
    fireEvent.change(screen.getByLabelText("起始日期"), {
      target: { value: "2026-07-01" },
    });
    fireEvent.change(screen.getByLabelText("结束日期"), {
      target: { value: "2026-07-31" },
    });

    // 应触发重新加载，传自定义 date_from/date_to
    await waitFor(() => {
      const lastCallArgs = vi.mocked(api.history).mock.calls[
        vi.mocked(api.history).mock.calls.length - 1
      ][0] as Record<string, unknown>;
      expect(lastCallArgs.date_from).toBe("2026-07-01");
      expect(lastCallArgs.date_to).toBe("2026-07-31");
    });
  });

  it("时间筛选：自定义模式无结果时展示范围提示", async () => {
    // 第一次：默认 all
    vi.mocked(api.history).mockResolvedValueOnce({
      total: mockItems.length,
      items: mockItems,
    });
    // 第二次：7d 返回空
    vi.mocked(api.history).mockResolvedValueOnce({
      total: 0,
      items: [],
    });

    const user = userEvent.setup();
    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    // 点击「近 7 天」
    await user.click(screen.getByRole("button", { name: "近 7 天" }));

    // 等待第二次加载完成，应展示「当前时间范围内无历史记录」
    await waitFor(() => {
      expect(screen.getByText("暂无问答历史")).toBeInTheDocument();
    });
    expect(screen.getByText(/当前时间范围内无历史记录/)).toBeInTheDocument();
  });

  it("搜索过滤：输入关键词后仅展示匹配项", async () => {
    vi.mocked(api.history).mockResolvedValue({
      total: mockItems.length,
      items: mockItems,
    });

    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    // 初始：两条都可见
    expect(await screen.findByText(/金酒的核心风味/)).toBeInTheDocument();
    expect(screen.getByText(/威士忌和波本有什么区别/)).toBeInTheDocument();

    // 输入「威士忌」过滤
    const searchInput = screen.getByLabelText("历史搜索框");
    fireEvent.change(searchInput, { target: { value: "威士忌" } });

    // 仅剩威士忌条目可见
    // 注：高亮会把 query 拆成 <span><mark></mark><span></span></span>，
    // getByText 无法匹配跨元素文本，改用 textContent 检查。
    await waitFor(() => {
      expect(document.body.textContent).toContain("威士忌和波本有什么区别");
    });
    expect(document.body.textContent).not.toContain("金酒的核心风味是什么");

    // 计数应更新为「共 1 条」
    expect(screen.getByText(/共 1 条/)).toBeInTheDocument();
  });

  it("搜索过滤：在 answer 中匹配关键词也能命中", async () => {
    vi.mocked(api.history).mockResolvedValue({
      total: mockItems.length,
      items: mockItems,
    });

    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    // 「杜松子」只出现在第一条的 answer 中
    const searchInput = screen.getByLabelText("历史搜索框");
    fireEvent.change(searchInput, { target: { value: "杜松子" } });

    // 第一条仍在文档中（query 文本未被高亮拆分，getByText 可匹配）
    await waitFor(() => {
      expect(screen.getByText(/金酒的核心风味是什么/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/威士忌和波本有什么区别/)).not.toBeInTheDocument();
  });

  it("关键词高亮：命中片段用 <mark> 包裹", async () => {
    vi.mocked(api.history).mockResolvedValue({
      total: mockItems.length,
      items: mockItems,
    });

    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    // 输入「金酒」应触发 query 与 answer 中的高亮
    const searchInput = screen.getByLabelText("历史搜索框");
    fireEvent.change(searchInput, { target: { value: "金酒" } });

    // 高亮会把 query 拆成多段，用 textContent 验证条目仍在文档中
    await waitFor(() => {
      expect(document.body.textContent).toContain("金酒的核心风味是什么");
    });

    // 至少应有一个 <mark> 元素（关键词高亮）
    const marks = document.querySelectorAll("mark");
    expect(marks.length).toBeGreaterThan(0);

    // 每个 mark 的文本都应是「金酒」（大小写不敏感）
    marks.forEach((m) => {
      expect(m.textContent?.toLowerCase()).toBe("金酒");
    });
  });

  it("空状态：history 返回空数组时展示「暂无问答历史」", async () => {
    vi.mocked(api.history).mockResolvedValue({ total: 0, items: [] });

    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    expect(await screen.findByText("暂无问答历史")).toBeInTheDocument();
    // 应展示引导文案
    expect(
      screen.getByText(/在问答面板提问后，历史记录会出现在这里/)
    ).toBeInTheDocument();
    // 不应展示「共 N 条」
    expect(screen.queryByText(/共 \d+ 条/)).not.toBeInTheDocument();
  });

  it("空状态：搜索无匹配时展示更换关键词提示", async () => {
    vi.mocked(api.history).mockResolvedValue({
      total: mockItems.length,
      items: mockItems,
    });

    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    // 等待数据加载
    await screen.findByText(/金酒的核心风味/);

    // 输入一个无匹配的关键词
    const searchInput = screen.getByLabelText("历史搜索框");
    fireEvent.change(searchInput, { target: { value: "龙舌兰xyz不存在的词" } });

    // 应展示空状态与「尝试更换搜索关键词」
    await waitFor(() => {
      expect(screen.getByText("暂无问答历史")).toBeInTheDocument();
    });
    expect(screen.getByText(/尝试更换搜索关键词/)).toBeInTheDocument();
  });

  it("onBack 回调：传入时渲染「返回问答」按钮并触发回调", async () => {
    vi.mocked(api.history).mockResolvedValue({
      total: mockItems.length,
      items: mockItems,
    });
    const user = userEvent.setup();
    const onBack = vi.fn();

    render(<HistoryPanel onBack={onBack} />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    const backBtn = screen.getByRole("button", { name: "返回问答" });
    await user.click(backBtn);
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("加载中：展示骨架屏，不展示历史项内容", async () => {
    // 让 history 永远 pending
    vi.mocked(api.history).mockImplementation(
      () => new Promise(() => {})  // never resolves
    );

    render(<HistoryPanel />);

    // 骨架屏容器 role="status"
    expect(await screen.findByRole("status", { name: /列表正在加载/ })).toBeInTheDocument();
    // 不应展示历史项 query
    expect(screen.queryByText(/金酒的核心风味/)).not.toBeInTheDocument();
  });

  it("API 失败：展示错误信息", async () => {
    vi.mocked(api.history).mockRejectedValue(new Error("网络异常"));

    render(<HistoryPanel />);
    await waitFor(() => expect(api.history).toHaveBeenCalled());

    expect(await screen.findByText("网络异常")).toBeInTheDocument();
  });
});
