// 核心组件渲染测试
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CitationList } from "../components/CitationList";
import type { Citation } from "../types";

// CitationList 是纯展示组件，适合做基础渲染测试
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

  it("渲染引用列表标题", () => {
    render(<CitationList citations={mockCitations} />);
    expect(screen.getByText(/来源溯源/)).toBeInTheDocument();
  });

  it("渲染所有引用项", () => {
    render(<CitationList citations={mockCitations} />);
    // 文本是 "[1] 金酒知识" 整体在一个 span，用模糊匹配
    expect(screen.getByText(/金酒知识/)).toBeInTheDocument();
    expect(screen.getByText(/威士忌入门/)).toBeInTheDocument();
  });

  it("空引用列表显示提示", () => {
    render(<CitationList citations={[]} />);
    // 空列表显示"无引用"
    expect(screen.getByText("无引用")).toBeInTheDocument();
  });

  it("点击引用项触发 onJumpToDoc", async () => {
    const user = userEvent.setup();
    const onJumpToDoc = vi.fn();
    render(
      <CitationList citations={mockCitations} onJumpToDoc={onJumpToDoc} />
    );

    // 点击第一个引用（文本是 "[1] 金酒知识"）
    const item = screen.getByText(/金酒知识/);
    await user.click(item);
    expect(onJumpToDoc).toHaveBeenCalledWith("doc_001", 42);
  });

  it("无 onJumpToDoc 时不崩溃", () => {
    render(<CitationList citations={mockCitations} />);
    // 不传 onJumpToDoc，组件正常渲染
    expect(screen.getByText(/金酒知识/)).toBeInTheDocument();
  });

  it("渲染引用编号", () => {
    render(<CitationList citations={mockCitations} />);
    // 应包含 [1] [2] 编号（在标题 span 内）
    expect(screen.getByText(/\[1\]/)).toBeInTheDocument();
    expect(screen.getByText(/\[2\]/)).toBeInTheDocument();
  });
});
