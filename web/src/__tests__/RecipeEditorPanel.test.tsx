/** RecipeEditorPanel 测试：表单 + 状态横幅 + 保存/提交审核 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../api", () => ({
  api: {
    labRecipes: vi.fn(),
    labCreateRecipe: vi.fn(),
    labUpdateRecipe: vi.fn(),
    labSubmitRecipe: vi.fn(),
    labResubmitRecipe: vi.fn(),
  },
}));

vi.mock("../components/Toast", () => ({
  showToast: vi.fn(),
}));

import { api } from "../api";
import { showToast } from "../components/Toast";
import { RecipeEditorPanel } from "../components/RecipeEditorPanel";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("RecipeEditorPanel", () => {
  it("冒烟测试：渲染不崩溃，新建模式展示草稿状态横幅", async () => {
    render(<RecipeEditorPanel />);
    expect(screen.getByText("创作新配方")).toBeInTheDocument();
    // 默认 draft 状态横幅
    expect(screen.getByText(/当前状态：草稿（draft）— 未提交/)).toBeInTheDocument();
    // 默认按钮为「创建草稿」
    expect(screen.getByRole("button", { name: "创建草稿" })).toBeInTheDocument();
  });

  it("校验：标题或正文为空时提示必填", async () => {
    const user = userEvent.setup();
    render(<RecipeEditorPanel />);
    await user.click(screen.getByRole("button", { name: "创建草稿" }));
    expect(await screen.findByText("配方名和正文为必填项。")).toBeInTheDocument();
    expect(api.labCreateRecipe).not.toHaveBeenCalled();
  });

  it("新建保存：调用 labCreateRecipe，成功后展示 doc_id", async () => {
    const user = userEvent.setup();
    vi.mocked(api.labCreateRecipe).mockResolvedValue({
      doc_id: "doc-new-1",
      status: "draft",
      title: "夏日清风",
    });

    render(<RecipeEditorPanel />);
    await user.type(screen.getByLabelText("配方名"), "夏日清风");
    await user.type(screen.getByLabelText("配方正文"), "# 配方\n- 金酒 50ml");

    await user.click(screen.getByRole("button", { name: "创建草稿" }));

    await waitFor(() => {
      expect(api.labCreateRecipe).toHaveBeenCalledWith(expect.objectContaining({
        title: "夏日清风",
        content: "# 配方\n- 金酒 50ml",
      }));
    });
    expect(await screen.findByText(/保存成功！配方 ID：doc-new-1（草稿）/)).toBeInTheDocument();
  });

  it("材料添加：回车 / 添加按钮，去重，删除 chip", async () => {
    const user = userEvent.setup();
    render(<RecipeEditorPanel />);

    const ingInput = screen.getByLabelText("材料输入");
    await user.type(ingInput, "金酒 50ml{Enter}");
    expect(screen.getByText("金酒 50ml")).toBeInTheDocument();

    await user.type(ingInput, "柠檬汁");
    await user.click(screen.getByRole("button", { name: "添加" }));
    expect(screen.getByText("柠檬汁")).toBeInTheDocument();

    // 重复添加 → 不新增（仍只有 1 个「金酒 50ml」chip）
    await user.type(ingInput, "金酒 50ml");
    await user.click(screen.getByRole("button", { name: "添加" }));
    expect(screen.getAllByText("金酒 50ml").length).toBe(1);

    // 删除 chip
    const removeBtn = screen.getByLabelText("移除 金酒 50ml");
    await user.click(removeBtn);
    expect(screen.queryByText("金酒 50ml")).not.toBeInTheDocument();
  });

  it("编辑模式：传入 docId 时加载已有配方（含 status）", async () => {
    vi.mocked(api.labRecipes).mockResolvedValue({
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
    });

    render(<RecipeEditorPanel docId="doc-edit-1" />);
    await waitFor(() => {
      expect(api.labRecipes).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText("编辑配方")).toBeInTheDocument();
      expect(screen.getByDisplayValue("已存在配方")).toBeInTheDocument();
      expect(screen.getByText(/当前状态：草稿（draft）— 未提交/)).toBeInTheDocument();
    });
  });

  it("编辑模式：pending 状态下控件被禁用", async () => {
    vi.mocked(api.labRecipes).mockResolvedValue({
      items: [
        {
          doc_id: "doc-pending-1",
          title: "待审核配方",
          source: "ugc",
          verified: false,
          hidden: false,
          status: "pending",
        },
      ],
    });

    render(<RecipeEditorPanel docId="doc-pending-1" />);
    await waitFor(() => {
      expect(screen.getByText(/当前状态：待审核（pending）/)).toBeInTheDocument();
    });
    // 标题输入被禁用（pending 不可编辑）
    const titleInput = screen.getByLabelText("配方名");
    expect(titleInput).toBeDisabled();
    // 保存草稿按钮被禁用
    const saveBtn = screen.getByRole("button", { name: "保存草稿" });
    expect(saveBtn).toBeDisabled();
  });

  it("保存失败：展示错误信息", async () => {
    const user = userEvent.setup();
    vi.mocked(api.labCreateRecipe).mockRejectedValue(new Error("后端 500"));

    render(<RecipeEditorPanel />);
    await user.type(screen.getByLabelText("配方名"), "Test");
    await user.type(screen.getByLabelText("配方正文"), "Content");

    await user.click(screen.getByRole("button", { name: "创建草稿" }));

    expect(await screen.findByText(/操作失败：后端 500/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// V3-Task11: RecipeEditorPanel「重新提交」按钮（rejected → draft）
// ---------------------------------------------------------------------------
describe("RecipeEditorPanel: V3-Task11 重新提交", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("rejected 状态下渲染「重新提交（回到草稿）」按钮", async () => {
    vi.mocked(api.labRecipes).mockResolvedValue({
      items: [
        {
          doc_id: "doc-rej-1",
          title: "被驳回配方",
          source: "ugc",
          verified: false,
          hidden: false,
          status: "rejected",
        },
      ],
    });

    render(<RecipeEditorPanel docId="doc-rej-1" />);
    await waitFor(() => {
      expect(screen.getByText(/当前状态：已驳回（rejected）/)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "重新提交（回到草稿状态）" })).toBeInTheDocument();
  });

  it("非 rejected 状态不渲染「重新提交」按钮", async () => {
    vi.mocked(api.labRecipes).mockResolvedValue({
      items: [
        {
          doc_id: "doc-draft-1",
          title: "草稿配方",
          source: "ugc",
          verified: false,
          hidden: false,
          status: "draft",
        },
      ],
    });

    render(<RecipeEditorPanel docId="doc-draft-1" />);
    await waitFor(() => {
      expect(screen.getByText(/当前状态：草稿（draft）/)).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "重新提交（回到草稿状态）" })).not.toBeInTheDocument();
  });

  it("点击重新提交：调用 labResubmitRecipe，成功后状态切回 draft 并展示提示", async () => {
    const user = userEvent.setup();
    vi.mocked(api.labRecipes).mockResolvedValue({
      items: [
        {
          doc_id: "doc-rej-2",
          title: "可重新提交",
          source: "ugc",
          verified: false,
          hidden: false,
          status: "rejected",
        },
      ],
    });
    vi.mocked(api.labResubmitRecipe).mockResolvedValue({
      doc_id: "doc-rej-2",
      status: "draft",
    });

    render(<RecipeEditorPanel docId="doc-rej-2" />);
    await waitFor(() => {
      expect(screen.getByText(/当前状态：已驳回（rejected）/)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "重新提交（回到草稿状态）" }));

    await waitFor(() => {
      expect(api.labResubmitRecipe).toHaveBeenCalledWith("doc-rej-2");
    });
    // 状态切回 draft
    await waitFor(() => {
      expect(screen.getByText(/当前状态：草稿（draft）— 未提交/)).toBeInTheDocument();
    });
    // 成功提示
    expect(screen.getByText(/已回到草稿状态（doc-rej-2），可编辑后重新提交审核。/)).toBeInTheDocument();
    // Toast 成功提示
    expect(showToast).toHaveBeenCalledWith("已回到草稿状态，可编辑后重新提交", "success");
  });

  it("重新提交失败：展示错误信息并保留 rejected 状态", async () => {
    const user = userEvent.setup();
    vi.mocked(api.labRecipes).mockResolvedValue({
      items: [
        {
          doc_id: "doc-rej-3",
          title: "重新提交失败",
          source: "ugc",
          verified: false,
          hidden: false,
          status: "rejected",
        },
      ],
    });
    vi.mocked(api.labResubmitRecipe).mockRejectedValue(new Error("无权限"));

    render(<RecipeEditorPanel docId="doc-rej-3" />);
    await waitFor(() => {
      expect(screen.getByText(/当前状态：已驳回（rejected）/)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "重新提交（回到草稿状态）" }));

    expect(await screen.findByText(/重新提交失败：无权限/)).toBeInTheDocument();
    // 状态仍为 rejected
    expect(screen.getByText(/当前状态：已驳回（rejected）/)).toBeInTheDocument();
    // Toast 错误提示
    expect(showToast).toHaveBeenCalledWith("重新提交失败：无权限", "danger");
  });

  it("重新提交进行中：按钮显示「处理中...」并禁用其他操作按钮", async () => {
    const user = userEvent.setup();
    vi.mocked(api.labRecipes).mockResolvedValue({
      items: [
        {
          doc_id: "doc-rej-4",
          title: "处理中测试",
          source: "ugc",
          verified: false,
          hidden: false,
          status: "rejected",
        },
      ],
    });
    // 让 promise 悬挂，保持 resubmitting 状态
    let resolveFn!: (v: unknown) => void;
    vi.mocked(api.labResubmitRecipe).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFn = resolve;
        }) as Promise<any>,
    );

    render(<RecipeEditorPanel docId="doc-rej-4" />);
    await waitFor(() => {
      expect(screen.getByText(/当前状态：已驳回（rejected）/)).toBeInTheDocument();
    });

    const resubmitBtn = screen.getByRole("button", { name: "重新提交（回到草稿状态）" });
    const saveBtn = screen.getByRole("button", { name: "保存草稿" });
    await user.click(resubmitBtn);

    await waitFor(() => {
      // resubmitting 时按钮文案变为「处理中...」且仍带 aria-label，按钮被禁用
      expect(resubmitBtn).toBeDisabled();
      expect(resubmitBtn).toHaveTextContent("处理中...");
      // 保存草稿 / 提交审核 也被禁用（resubmitting 时禁用）
      expect(saveBtn).toBeDisabled();
    });

    // 释放悬挂的 promise，避免后续测试泄漏
    resolveFn({ doc_id: "doc-rej-4", status: "draft" });
    await waitFor(() => expect(saveBtn).not.toBeDisabled());
  });
});
