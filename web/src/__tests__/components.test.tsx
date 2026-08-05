// 核心组件渲染测试
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CitationList } from "../components/CitationList";
import type { Citation } from "../types";

// CitationList 是纯展示组件，适合做基础渲染测试
// UI 密度优化 Task 3.3：默认折叠，仅展示摘要；点击展开后渲染完整列表
describe("CitationList", () => {
  const mockCitations: Citation[] = [
    {
      id: 1,
      doc_id: "doc_001",
      title: "金酒知识",
      snippet: "金酒是以杜松子为主要香料的烈酒...",
      score: 0.95,
      chunk_rowid: 42,
    },
    {
      id: 2,
      doc_id: "doc_002",
      title: "威士忌入门",
      snippet: "威士忌由谷物发酵蒸馏而成...",
      score: 0.88,
      chunk_rowid: 58,
    },
  ];

  it("折叠状态展示摘要按钮", () => {
    render(<CitationList citations={mockCitations} />);
    // 折叠时显示「N 条引用」按钮
    expect(
      screen.getByRole("button", { name: /展开 2 条引用/ })
    ).toBeInTheDocument();
    // 首条标题在摘要中可见
    expect(screen.getByText(/金酒知识/)).toBeInTheDocument();
  });

  it("展开后渲染所有引用项与来源溯源标题", async () => {
    const user = userEvent.setup();
    render(<CitationList citations={mockCitations} />);
    // 点击展开按钮
    await user.click(
      screen.getByRole("button", { name: /展开 2 条引用/ })
    );
    // 展开后出现「来源溯源」标题
    expect(screen.getByText(/来源溯源/)).toBeInTheDocument();
    // 两条引用标题均可见
    expect(screen.getByText(/金酒知识/)).toBeInTheDocument();
    expect(screen.getByText(/威士忌入门/)).toBeInTheDocument();
  });

  it("空引用列表显示提示", () => {
    render(<CitationList citations={[]} />);
    // 空列表显示"无引用"
    expect(screen.getByText("无引用")).toBeInTheDocument();
  });

  it("展开后点击引用项触发 onJumpToDoc", async () => {
    const user = userEvent.setup();
    const onJumpToDoc = vi.fn();
    render(
      <CitationList citations={mockCitations} onJumpToDoc={onJumpToDoc} />
    );

    // 先展开引用列表
    await user.click(
      screen.getByRole("button", { name: /展开 2 条引用/ })
    );
    // 点击第一个引用（文本是 "金酒知识"）
    const item = screen.getByText(/金酒知识/);
    await user.click(item);
    expect(onJumpToDoc).toHaveBeenCalledWith("doc_001", 42);
  });

  it("无 onJumpToDoc 时不崩溃", () => {
    render(<CitationList citations={mockCitations} />);
    // 不传 onJumpToDoc，组件正常渲染摘要
    expect(screen.getByText(/金酒知识/)).toBeInTheDocument();
  });

  it("展开后渲染引用编号", async () => {
    const user = userEvent.setup();
    render(<CitationList citations={mockCitations} />);
    // 先展开引用列表
    await user.click(
      screen.getByRole("button", { name: /展开 2 条引用/ })
    );
    // 应包含 [1] [2] 编号（在 cite-num span 内）
    expect(screen.getByText(/\[1\]/)).toBeInTheDocument();
    expect(screen.getByText(/\[2\]/)).toBeInTheDocument();
  });

  it("收起按钮可切换回折叠状态", async () => {
    const user = userEvent.setup();
    render(<CitationList citations={mockCitations} />);
    // 展开
    await user.click(
      screen.getByRole("button", { name: /展开 2 条引用/ })
    );
    expect(screen.getByText(/来源溯源/)).toBeInTheDocument();
    // 收起
    await user.click(
      screen.getByRole("button", { name: /收起引用/ })
    );
    expect(screen.queryByText(/来源溯源/)).not.toBeInTheDocument();
    // 重新出现展开按钮
    expect(
      screen.getByRole("button", { name: /展开 2 条引用/ })
    ).toBeInTheDocument();
  });
});
