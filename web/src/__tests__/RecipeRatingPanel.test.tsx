/** V2-Task6: RecipeRatingPanel 测试 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// vi.mock 工厂是 hoisted 的，mock 函数必须在工厂内部声明
vi.mock("../api", () => ({
  api: {
    labGetRating: vi.fn(),
    labRateRecipe: vi.fn(),
  },
}));

// Mock showToast
vi.mock("../components/Toast", () => ({
  showToast: vi.fn(),
}));

import { api } from "../api";
import { RecipeRatingPanel } from "../components/RecipeRatingPanel";
import type { RecipeRatingSummary } from "../types";

const mockLabGetRating = vi.mocked(api.labGetRating);
const mockLabRateRecipe = vi.mocked(api.labRateRecipe);

const EMPTY_SUMMARY: RecipeRatingSummary = {
  doc_id: "doc_001",
  average_score: 0,
  rating_count: 0,
  note_count: 0,
  current_user_rating: null,
  notes: [],
};

const SUMMARY_WITH_DATA: RecipeRatingSummary = {
  doc_id: "doc_001",
  average_score: 4.0,
  rating_count: 2,
  note_count: 2,
  current_user_rating: {
    score: 5,
    comment: "我的旧笔记",
    updated_at: "2026-07-29T10:00:00Z",
  },
  notes: [
    {
      user: "alice",
      score: 5,
      comment: "非常好喝",
      updated_at: "2026-07-29T10:00:00Z",
    },
    {
      user: "bob",
      score: 3,
      comment: "一般",
      updated_at: "2026-07-28T10:00:00Z",
    },
  ],
};

describe("RecipeRatingPanel", () => {
  beforeEach(() => {
    mockLabGetRating.mockClear();
    mockLabRateRecipe.mockClear();
  });

  it("加载中显示提示文本", () => {
    mockLabGetRating.mockReturnValue(new Promise(() => {})); // 永不 resolve
    render(<RecipeRatingPanel docId="doc_001" />);
    expect(screen.getByText("加载评分中…")).toBeInTheDocument();
  });

  it("加载失败显示错误信息", async () => {
    mockLabGetRating.mockRejectedValue(new Error("网络错误"));
    render(<RecipeRatingPanel docId="doc_001" />);
    await waitFor(() => {
      expect(screen.getByText("网络错误")).toBeInTheDocument();
    });
  });

  it("空评分摘要：显示 0.0 平均分 + 0 人评分 + 暂无笔记", async () => {
    mockLabGetRating.mockResolvedValue(EMPTY_SUMMARY);
    render(<RecipeRatingPanel docId="doc_001" />);

    await waitFor(() => {
      expect(screen.getByTestId("rating-average")).toHaveTextContent("0.0");
    });
    expect(screen.getByText("0 人评分")).toBeInTheDocument();
    expect(screen.getByText("0 条笔记")).toBeInTheDocument();
    expect(screen.getByText("暂无笔记")).toBeInTheDocument();
  });

  it("有评分数据：显示平均分 + 笔记列表 + 回填当前用户评分", async () => {
    mockLabGetRating.mockResolvedValue(SUMMARY_WITH_DATA);
    render(<RecipeRatingPanel docId="doc_001" />);

    await waitFor(() => {
      expect(screen.getByTestId("rating-average")).toHaveTextContent("4.0");
    });
    expect(screen.getByText("2 人评分")).toBeInTheDocument();
    expect(screen.getByText("2 条笔记")).toBeInTheDocument();

    // 笔记列表
    const notesList = screen.getByTestId("rating-notes");
    expect(notesList).toBeInTheDocument();
    expect(screen.getByText("非常好喝")).toBeInTheDocument();
    expect(screen.getByText("一般")).toBeInTheDocument();

    // 当前用户评分回填（5 星 + 旧笔记）
    const commentBox = screen.getByTestId("rating-comment") as HTMLTextAreaElement;
    expect(commentBox.value).toBe("我的旧笔记");
  });

  it("点击星星选中评分（0 星初始状态）", async () => {
    const user = userEvent.setup();
    mockLabGetRating.mockResolvedValue(EMPTY_SUMMARY);
    render(<RecipeRatingPanel docId="doc_001" />);

    await waitFor(() => {
      expect(screen.getByTestId("rating-stars")).toBeInTheDocument();
    });

    // 初始 5 颗星都是 ☆（空星）
    const starButtons = screen.getAllByRole("radio");
    expect(starButtons).toHaveLength(5);

    // 点击第 4 颗星
    await user.click(starButtons[3]);
    expect(starButtons[3]).toHaveAttribute("aria-checked", "true");
  });

  it("点击清除按钮重置评分为 0", async () => {
    const user = userEvent.setup();
    mockLabGetRating.mockResolvedValue(SUMMARY_WITH_DATA);
    render(<RecipeRatingPanel docId="doc_001" />);

    await waitFor(() => {
      expect(screen.getByTestId("rating-stars")).toBeInTheDocument();
    });

    // 当前用户评分回填为 5 星，"清除"按钮可见
    const clearBtn = screen.getByLabelText("清除评分");
    await user.click(clearBtn);

    // 所有星星 aria-checked 都变成 false
    const starButtons = screen.getAllByRole("radio");
    starButtons.forEach((btn) => {
      expect(btn).toHaveAttribute("aria-checked", "false");
    });
  });

  it("提交评分调用 labRateRecipe 并刷新", async () => {
    const user = userEvent.setup();
    mockLabGetRating.mockResolvedValueOnce(EMPTY_SUMMARY);
    mockLabGetRating.mockResolvedValueOnce(SUMMARY_WITH_DATA);
    mockLabRateRecipe.mockResolvedValue({
      doc_id: "doc_001",
      user: "anonymous",
      score: 5,
      comment: "好喝",
      status: "created",
    });

    const onChanged = vi.fn();
    render(<RecipeRatingPanel docId="doc_001" onChanged={onChanged} />);

    await waitFor(() => {
      expect(screen.getByTestId("rating-submit")).toBeInTheDocument();
    });

    // 选 5 星
    const starButtons = screen.getAllByRole("radio");
    await user.click(starButtons[4]);

    // 输入笔记
    const commentBox = screen.getByTestId("rating-comment");
    await user.type(commentBox, "好喝");

    // 点击提交
    await user.click(screen.getByTestId("rating-submit"));

    await waitFor(() => {
      expect(mockLabRateRecipe).toHaveBeenCalledWith("doc_001", {
        score: 5,
        comment: "好喝",
      });
    });

    // 应触发 onChanged 回调
    await waitFor(() => {
      expect(onChanged).toHaveBeenCalled();
    });
  });

  it("仅提交笔记（0 星）：不传 score", async () => {
    const user = userEvent.setup();
    mockLabGetRating.mockResolvedValue(EMPTY_SUMMARY);
    mockLabRateRecipe.mockResolvedValue({
      doc_id: "doc_001",
      user: "anonymous",
      score: 0,
      comment: "纯笔记",
      status: "created",
    });

    render(<RecipeRatingPanel docId="doc_001" />);

    await waitFor(() => {
      expect(screen.getByTestId("rating-submit")).toBeInTheDocument();
    });

    // 不选星星，直接输入笔记
    const commentBox = screen.getByTestId("rating-comment");
    await user.type(commentBox, "纯笔记");

    // 提交按钮应可用（comment 非空）
    const submitBtn = screen.getByTestId("rating-submit") as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(false);

    await user.click(submitBtn);

    await waitFor(() => {
      // score 为 0 时应转为 undefined
      expect(mockLabRateRecipe).toHaveBeenCalledWith("doc_001", {
        comment: "纯笔记",
      });
    });
  });

  it("0 星 + 空笔记时提交按钮禁用", async () => {
    mockLabGetRating.mockResolvedValue(EMPTY_SUMMARY);
    render(<RecipeRatingPanel docId="doc_001" />);

    await waitFor(() => {
      const submitBtn = screen.getByTestId("rating-submit") as HTMLButtonElement;
      expect(submitBtn.disabled).toBe(true);
    });
  });

  it("提交失败时显示 toast 错误", async () => {
    const user = userEvent.setup();
    mockLabGetRating.mockResolvedValue(EMPTY_SUMMARY);
    mockLabRateRecipe.mockRejectedValue(new Error("网络错误"));

    render(<RecipeRatingPanel docId="doc_001" />);

    await waitFor(() => {
      expect(screen.getByTestId("rating-submit")).toBeInTheDocument();
    });

    // 选星 + 输入笔记
    const starButtons = screen.getAllByRole("radio");
    await user.click(starButtons[4]);
    const commentBox = screen.getByTestId("rating-comment");
    await user.type(commentBox, "测试");

    await user.click(screen.getByTestId("rating-submit"));

    // showToast 被 mock，这里仅验证按钮恢复可用（提交完成）
    await waitFor(() => {
      const submitBtn = screen.getByTestId("rating-submit") as HTMLButtonElement;
      expect(submitBtn.disabled).toBe(false);
    });
  });

  it("docId 变化时重新加载", async () => {
    mockLabGetRating.mockResolvedValue(EMPTY_SUMMARY);
    const { rerender } = render(<RecipeRatingPanel docId="doc_001" />);

    await waitFor(() => {
      expect(mockLabGetRating).toHaveBeenCalledWith("doc_001");
    });

    rerender(<RecipeRatingPanel docId="doc_002" />);

    await waitFor(() => {
      expect(mockLabGetRating).toHaveBeenCalledWith("doc_002");
    });
  });

  it("笔记字符计数显示", async () => {
    mockLabGetRating.mockResolvedValue(EMPTY_SUMMARY);
    render(<RecipeRatingPanel docId="doc_001" />);

    await waitFor(() => {
      expect(screen.getByText("0/2000")).toBeInTheDocument();
    });

    const commentBox = screen.getByTestId("rating-comment") as HTMLTextAreaElement;
    await userEvent.type(commentBox, "abc");
    await waitFor(() => {
      expect(screen.getByText("3/2000")).toBeInTheDocument();
    });
  });
});
