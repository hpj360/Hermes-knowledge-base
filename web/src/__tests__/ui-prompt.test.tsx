// usePrompt Hook 测试：替代 window.prompt 的输入对话框
// 验证规范：标题/message 分离、.input 语义类、btn-primary/btn-ghost、
//          Enter 确认 / Escape 取消、空串确认返回 ""（不转 null）、a11y aria-label
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { usePrompt } from "../components/ui";

/** 测试夹具：渲染按钮触发 prompt，展示 resolve 结果。
 *  result 编码：undefined→"none"，null→"NULL"，string→"STR:<value>"（空串→"STR:"） */
function PromptHarness({
  message = "请填写理由",
  defaultValue,
}: {
  message?: string;
  defaultValue?: string;
}) {
  const { prompt, dialog } = usePrompt();
  const [result, setResult] = useState<string | null | undefined>(undefined);
  return (
    <>
      <button onClick={() => prompt(message, defaultValue).then(setResult)}>
        open
      </button>
      <span data-testid="result">
        {result === undefined ? "none" : result === null ? "NULL" : `STR:${result}`}
      </span>
      {dialog}
    </>
  );
}

/** 把 promise.then(setState) 的微任务刷新到 act 作用域内，消除 act 警告 */
function flushMicrotasks(): Promise<void> {
  return act(async () => {
    await Promise.resolve();
  });
}

describe("usePrompt", () => {
  it("prompt() 打开对话框：含独立标题、message 段落、input 字段", async () => {
    const user = userEvent.setup();
    render(<PromptHarness message="请填写驳回理由" />);
    await user.click(screen.getByText("open"));

    // 标题为固定文案（区别于 message，不把 message 当 title）
    expect(await screen.findByText("请输入")).toBeInTheDocument();
    // message 作为独立段落渲染
    expect(screen.getByText("请填写驳回理由")).toBeInTheDocument();
    // input 字段存在（通过 aria-label 关联）
    expect(screen.getByLabelText(/请填写驳回理由/)).toBeInTheDocument();
  });

  it("对话框具备 role=dialog（a11y）", async () => {
    const user = userEvent.setup();
    render(<PromptHarness />);
    await user.click(screen.getByText("open"));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("确认：返回输入的字符串", async () => {
    const user = userEvent.setup();
    render(<PromptHarness />);
    await user.click(screen.getByText("open"));
    const input = await screen.findByLabelText(/请填写理由/);
    await user.type(input, "材料不合规");
    await user.click(screen.getByRole("button", { name: "确认" }));
    await flushMicrotasks();
    expect(screen.getByTestId("result").textContent).toBe("STR:材料不合规");
  });

  it("取消：返回 null", async () => {
    const user = userEvent.setup();
    render(<PromptHarness />);
    await user.click(screen.getByText("open"));
    await user.click(await screen.findByRole("button", { name: "取消" }));
    await flushMicrotasks();
    expect(screen.getByTestId("result").textContent).toBe("NULL");
  });

  it("确认空输入：返回空字符串（不转 null）", async () => {
    const user = userEvent.setup();
    render(<PromptHarness />);
    await user.click(screen.getByText("open"));
    await user.click(await screen.findByRole("button", { name: "确认" }));
    await flushMicrotasks();
    expect(screen.getByTestId("result").textContent).toBe("STR:");
  });

  it("Enter 键触发确认", async () => {
    const user = userEvent.setup();
    render(<PromptHarness />);
    await user.click(screen.getByText("open"));
    const input = await screen.findByLabelText(/请填写理由/);
    await user.type(input, "xyz");
    fireEvent.keyDown(input, { key: "Enter" });
    await flushMicrotasks();
    expect(screen.getByTestId("result").textContent).toBe("STR:xyz");
  });

  it("Escape 键触发取消", async () => {
    const user = userEvent.setup();
    render(<PromptHarness />);
    await user.click(screen.getByText("open"));
    const input = await screen.findByLabelText(/请填写理由/);
    fireEvent.keyDown(input, { key: "Escape" });
    await flushMicrotasks();
    expect(screen.getByTestId("result").textContent).toBe("NULL");
  });

  it("defaultValue 预填输入框", async () => {
    const user = userEvent.setup();
    render(<PromptHarness defaultValue="默认理由" />);
    await user.click(screen.getByText("open"));
    expect(await screen.findByLabelText(/请填写理由/)).toHaveValue("默认理由");
  });

  it("确定按钮用 .btn-primary，取消按钮用 .btn-ghost", async () => {
    const user = userEvent.setup();
    render(<PromptHarness />);
    await user.click(screen.getByText("open"));
    const confirmBtn = await screen.findByRole("button", { name: "确认" });
    const cancelBtn = await screen.findByRole("button", { name: "取消" });
    expect(confirmBtn.className).toContain("btn-primary");
    expect(cancelBtn.className).toContain("btn-ghost");
  });

  it("input 用 .input 语义类且有 aria-label（a11y）", async () => {
    const user = userEvent.setup();
    render(<PromptHarness message="请填写理由" />);
    await user.click(screen.getByText("open"));
    const input = await screen.findByLabelText(/请填写理由/);
    expect(input.className).toContain("input");
  });
});
