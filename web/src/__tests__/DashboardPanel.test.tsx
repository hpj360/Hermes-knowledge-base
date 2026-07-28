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

  it("展示三个核心能力卡片", async () => {
    renderDashboard();
    expect(screen.getByText("知识可信")).toBeInTheDocument();
    expect(screen.getByText("实践可用")).toBeInTheDocument();
    expect(screen.getByText("持续成长")).toBeInTheDocument();
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
});
