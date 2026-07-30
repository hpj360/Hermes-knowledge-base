/**
 * Task 14: ShareCardButton 测试
 *
 * 覆盖点：
 * 1. 渲染「分享」按钮
 * 2. 点击后显示「处理中...」（deferred toBlob 保持 pending）
 * 3. Canvas 生成调用（mock canvas.toBlob + ctx.fillRect/fillText）
 * 4. Web Share API 调用（mock navigator.canShare + navigator.share）
 * 5. 降级：canShare=false 时下载 PNG（mock URL.createObjectURL）
 *
 * mock 要点：
 * - HTMLCanvasElement.prototype.getContext 返回 ctx stub（jsdom 不实现 canvas）
 * - HTMLCanvasElement.prototype.toBlob 控制 immediate / deferred 回调
 * - navigator.canShare / navigator.share（jsdom 不实现 Web Share API）
 * - URL.createObjectURL / revokeObjectURL
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ShareCardButton } from "../components/ShareCardButton";
import type { LabRecipe } from "../types";

const mockRecipe = {
  doc_id: "test-1",
  title: "Old Fashioned",
  source: "iba_dataset",
  verified: true,
  hidden: false,
  status: "published",
  season: "winter",
  // 扩展字段（LabRecipe 运行时可能携带）：
  ingredients: ["Bourbon 60ml", "Sugar 1 cube", "Angostura Bitters 2 dashes"],
} as any as LabRecipe;

// ---------------------------------------------------------------------------
// Canvas mock 工具
// ---------------------------------------------------------------------------
function makeCtxStub() {
  return {
    fillRect: vi.fn(),
    fillText: vi.fn(),
    fillStyle: "" as string,
    font: "" as string,
    textBaseline: "" as CanvasTextBaseline,
    textAlign: "" as CanvasTextAlign,
  };
}

let ctxStub: ReturnType<typeof makeCtxStub>;
let toBlobCalls: Array<{ cb: (b: Blob | null) => void; type?: string }>;
let toBlobMode: "immediate" | "deferred";
let toBlobBlob: Blob;

const origGetContext = HTMLCanvasElement.prototype.getContext;
const origToBlob = HTMLCanvasElement.prototype.toBlob;

function installCanvasMocks() {
  // jsdom 默认 getContext 返回 null，需替换为 ctx stub
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ctxStub as any) as any;
  // toBlob：根据 toBlobMode 决定是否立即回调
  HTMLCanvasElement.prototype.toBlob = function (cb: any, type?: string) {
    toBlobCalls.push({ cb, type });
    if (toBlobMode === "immediate") cb(toBlobBlob);
  } as any;
}

function restoreCanvasMocks() {
  HTMLCanvasElement.prototype.getContext = origGetContext;
  HTMLCanvasElement.prototype.toBlob = origToBlob as any;
}

// ---------------------------------------------------------------------------
// Web Share API mock 工具
// ---------------------------------------------------------------------------
type ShareFn = (data?: ShareData) => Promise<void>;
type ShareMock = ReturnType<typeof vi.fn<ShareFn>>;
let shareMock: ShareMock | undefined;
let canShareValue: boolean;

const origCanShare = Object.getOwnPropertyDescriptor(navigator, "canShare");
const origShare = Object.getOwnPropertyDescriptor(navigator, "share");

function installShareMocks(opts: { canShare: boolean; shareResult?: "resolve" | "reject" }) {
  canShareValue = opts.canShare;
  shareMock = vi.fn<ShareFn>(async (_data?: ShareData) => {
    if (opts.shareResult === "reject") {
      throw new DOMException("share failed", "AbortError");
    }
  });
  Object.defineProperty(navigator, "canShare", {
    value: (_data?: ShareData) => canShareValue,
    configurable: true,
    writable: true,
  });
  Object.defineProperty(navigator, "share", {
    value: shareMock,
    configurable: true,
    writable: true,
  });
}

function restoreShareMocks() {
  if (origCanShare) {
    Object.defineProperty(navigator, "canShare", origCanShare);
  } else {
    delete (navigator as any).canShare;
  }
  if (origShare) {
    Object.defineProperty(navigator, "share", origShare);
  } else {
    delete (navigator as any).share;
  }
  shareMock = undefined;
}

// ---------------------------------------------------------------------------
// URL mock 工具
// ---------------------------------------------------------------------------
const origCreateObjectURL = URL.createObjectURL;
const origRevokeObjectURL = URL.revokeObjectURL;
// jsdom 对 <a>.click() 会触发 navigation（Not implemented 警告），下载降级用例中需屏蔽
const origAnchorClick = HTMLAnchorElement.prototype.click;
function installURLMocks() {
  URL.createObjectURL = vi.fn(() => "blob:mock-url");
  URL.revokeObjectURL = vi.fn();
  HTMLAnchorElement.prototype.click = vi.fn(() => {});
}
function restoreURLMocks() {
  URL.createObjectURL = origCreateObjectURL;
  URL.revokeObjectURL = origRevokeObjectURL;
  HTMLAnchorElement.prototype.click = origAnchorClick;
}

// ---------------------------------------------------------------------------
// 用例
// ---------------------------------------------------------------------------
beforeEach(() => {
  ctxStub = makeCtxStub();
  toBlobCalls = [];
  toBlobMode = "immediate";
  toBlobBlob = new Blob(["fake-png-bytes"], { type: "image/png" });
  installCanvasMocks();
  installURLMocks();
});

afterEach(() => {
  restoreCanvasMocks();
  restoreURLMocks();
  restoreShareMocks();
});

describe("ShareCardButton", () => {
  it("渲染「分享」按钮", () => {
    render(<ShareCardButton recipe={mockRecipe} />);
    expect(screen.getByRole("button", { name: "分享" })).toBeInTheDocument();
  });

  it("点击后显示「处理中...」，生成完成后恢复为「分享」", async () => {
    // deferred：toBlob 不立即回调，保持 generateShareCard pending
    toBlobMode = "deferred";
    installShareMocks({ canShare: false }); // 走下载降级路径

    const user = userEvent.setup();
    render(<ShareCardButton recipe={mockRecipe} />);
    const btn = screen.getByRole("button", { name: "分享" });
    await user.click(btn);

    // 生成中：按钮文案切换 + disabled
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "处理中..." })).toBeDisabled();
    });

    // 触发 toBlob 回调，让 Promise resolve
    expect(toBlobCalls.length).toBe(1);
    toBlobCalls[0].cb(toBlobBlob);

    // 完成后恢复
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "分享" })).not.toBeDisabled();
    });
  });

  it("Canvas 生成：调用 ctx.fillRect / fillText，并以 image/png 调用 canvas.toBlob", async () => {
    installShareMocks({ canShare: false });
    const user = userEvent.setup();
    render(<ShareCardButton recipe={mockRecipe} />);
    await user.click(screen.getByRole("button", { name: "分享" }));

    // toBlob 被调用一次，type 为 image/png
    await waitFor(() => expect(toBlobCalls.length).toBe(1));
    expect(toBlobCalls[0].type).toBe("image/png");

    // Canvas 绘制：fillRect（背景/色带/方块/分隔线）+ fillText（H 水印/标题/来源/材料/底部水印）
    expect(ctxStub.fillRect).toHaveBeenCalled();
    expect(ctxStub.fillText).toHaveBeenCalled();

    const texts = ctxStub.fillText.mock.calls.map((c) => c[0] as string);
    expect(texts).toContain("H");
    expect(texts).toContain("Old Fashioned");
    expect(texts).toContain("INGREDIENTS");
    expect(texts.some((t) => t.startsWith("SOURCE /"))).toBe(true);
    // 材料被渲染进 Canvas
    expect(texts.some((t) => t.includes("Bourbon 60ml"))).toBe(true);
  });

  it("Web Share API：canShare=true 时调用 navigator.share 并传入 File", async () => {
    installShareMocks({ canShare: true, shareResult: "resolve" });
    const user = userEvent.setup();
    render(<ShareCardButton recipe={mockRecipe} />);
    await user.click(screen.getByRole("button", { name: "分享" }));

    await waitFor(() => expect(shareMock!.mock.calls.length).toBe(1));

    const shareArg = shareMock!.mock.calls[0][0] as ShareData;
    expect(shareArg.title).toBe("Old Fashioned");
    expect(shareArg.text).toContain("Old Fashioned");
    expect(shareArg.files).toBeDefined();
    expect(shareArg.files!.length).toBe(1);
    const file = shareArg.files![0] as File;
    expect(file.name).toBe("hermes-test-1.png");
    expect(file.type).toBe("image/png");

    // 走分享路径，不应触发下载降级
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it("降级：canShare=false 时下载 PNG（createObjectURL + revokeObjectURL）", async () => {
    installShareMocks({ canShare: false });
    const user = userEvent.setup();
    render(<ShareCardButton recipe={mockRecipe} />);
    await user.click(screen.getByRole("button", { name: "分享" }));

    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalledTimes(1));
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(1);
    // share 不应被调用
    expect(shareMock!.mock.calls.length).toBe(0);
  });
});
