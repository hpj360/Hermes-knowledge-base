// DashboardPanel 单测
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Router } from "wouter";

// Mock api
vi.mock("../api", () => ({
  api: {
    health: vi.fn().mockResolvedValue({
      doc_count: 5,
      llm_available: true,
      auth_enabled: false,
    }),
    labDashboard: vi.fn().mockResolvedValue({
      total_queries: 42,
      avg_citations: 2.5,
      total_recipes: 57,
    }),
    labDaily: vi.fn().mockResolvedValue({ title: null, reason: "empty" }),
    history: vi.fn().mockResolvedValue({
      total: 2,
      items: [
        {
          log_id: 1,
          query: "金酒和威士忌的区别",
          answer: "金酒是蒸馏酒...",
          created_at: "2026-07-28T10:00:00Z",
          citations: [{ doc_id: "doc-1", chunk_rowid: 0, title: "金酒百科", text: "..." }],
        },
        {
          log_id: 2,
          query: "如何调制马天尼",
          answer: "马天尼配方...",
          created_at: "2026-07-27T15:00:00Z",
          citations: [],
        },
      ],
    }),
  },
}));

import { DashboardPanel } from "../components/DashboardPanel";
import { api } from "../api";

function renderDashboard(props: Partial<Parameters<typeof DashboardPanel>[0]> = {}) {
  return render(
    <Router>
      <DashboardPanel
        health={{ doc_count: 5, llm_available: true, auth_enabled: false } as any}
        onSeed={vi.fn()}
        seeding={false}
        onShowImport={vi.fn()}
        {...props}
      />
    </Router>
  );
}

describe("DashboardPanel", () => {
  it("Hero 区展示价值主张「从知识到实践」", async () => {
    renderDashboard();
    expect(screen.getByText("从知识到实践")).toBeInTheDocument();
  });

  it("展示三张实时数据卡（文档/问答/配方）", async () => {
    renderDashboard();
    // Hero banner 内 3 张 BauhausMetric 实时数据卡（替换原静态能力卡）
    expect(screen.getByText("文档")).toBeInTheDocument();
    expect(screen.getByText("问答")).toBeInTheDocument();
    expect(screen.getByText("配方")).toBeInTheDocument();
  });

  it("展示飞轮健康度指标卡", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("文档总数")).toBeInTheDocument();
      expect(screen.getByText("问答次数")).toBeInTheDocument();
      expect(screen.getByText("平均引用数")).toBeInTheDocument();
      expect(screen.getByText("配方总数")).toBeInTheDocument();
    });
  });

  it("展示快捷操作按钮", async () => {
    renderDashboard();
    expect(screen.getByText("开始提问")).toBeInTheDocument();
    expect(screen.getByText("导入文档")).toBeInTheDocument();
    expect(screen.getByText("浏览配方")).toBeInTheDocument();
    expect(screen.getByText("进入实验室")).toBeInTheDocument();
  });

  it("空库时展示种子导入引导卡片", async () => {
    renderDashboard({
      health: { doc_count: 0, llm_available: false, auth_enabled: false } as any,
    });
    expect(screen.getByText("开始你的知识库")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "导入种子知识" })).toBeInTheDocument();
  });

  it("非空库时不展示种子导入引导卡片", async () => {
    renderDashboard({
      health: { doc_count: 5, llm_available: true, auth_enabled: false } as any,
    });
    expect(screen.queryByText("开始你的知识库")).not.toBeInTheDocument();
  });

  it("空库时点击「导入种子知识」触发 onSeed", async () => {
    const user = userEvent.setup();
    const onSeed = vi.fn();
    renderDashboard({
      health: { doc_count: 0, llm_available: false, auth_enabled: false } as any,
      onSeed,
    });
    await user.click(screen.getByRole("button", { name: "导入种子知识" }));
    expect(onSeed).toHaveBeenCalledTimes(1);
  });

  it("点击「导入文档」触发 onShowImport", async () => {
    const user = userEvent.setup();
    const onShowImport = vi.fn();
    renderDashboard({ onShowImport });
    await user.click(screen.getByText("导入文档"));
    expect(onShowImport).toHaveBeenCalledTimes(1);
  });

  it("seeding=true 时按钮显示「导入中...」且禁用", async () => {
    renderDashboard({
      health: { doc_count: 0, llm_available: false, auth_enabled: false } as any,
      seeding: true,
    });
    const btn = screen.getByRole("button", { name: "导入中..." });
    expect(btn).toBeDisabled();
  });

  it("有历史时展示最近问答", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("金酒和威士忌的区别")).toBeInTheDocument();
      expect(screen.getByText("如何调制马天尼")).toBeInTheDocument();
    });
  });

  it("调用 labDashboard 和 history API", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(api.labDashboard).toHaveBeenCalled();
      expect(api.history).toHaveBeenCalledWith(3);
    });
  });

  it("调用 labDaily API 获取每日推荐", async () => {
    renderDashboard();
    await waitFor(() => expect(api.labDaily).toHaveBeenCalled());
  });

  it("今日推荐：labDaily 返回 season reason 时展示「应季推荐」徽章", async () => {
    vi.mocked(api.labDaily).mockResolvedValueOnce({
      title: "Mojito",
      reason: "season",
      doc_id: "doc-mojito",
      base_spirit: "rum",
      difficulty: "easy",
    });
    renderDashboard();
    // 应展示 Mojito 标题与「应季推荐」徽章
    await waitFor(() => {
      expect(screen.getByText("Mojito")).toBeInTheDocument();
    });
    expect(screen.getByText("应季推荐")).toBeInTheDocument();
    // 应展示 base_spirit 元信息
    expect(screen.getByText("rum")).toBeInTheDocument();
  });

  it("今日推荐：labDaily 返回 hot reason 时展示「本周热门」徽章", async () => {
    vi.mocked(api.labDaily).mockResolvedValueOnce({
      title: "Old Fashioned",
      reason: "hot",
    });
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Old Fashioned")).toBeInTheDocument();
    });
    expect(screen.getByText("本周热门")).toBeInTheDocument();
  });

  it("今日推荐：labDaily 返回空时不展示推荐卡片", async () => {
    // mockResolvedValue 默认就是 { title: null, reason: "empty" }
    renderDashboard();
    // 等待 useEffect 完成
    await waitFor(() => expect(api.labDaily).toHaveBeenCalled());
    // labDaily 返回空 title 时不展示推荐 reason 徽章
    expect(screen.queryByText("应季推荐")).not.toBeInTheDocument();
    expect(screen.queryByText("本周热门")).not.toBeInTheDocument();
    expect(screen.queryByText("随机发现")).not.toBeInTheDocument();
  });
});
