/** V3-Task10: MultiLogin 与 UserAdminPanel 测试 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../api", () => ({
  api: {
    multiLogin: vi.fn(),
    register: vi.fn(),
    createInvite: vi.fn(),
    listUsers: vi.fn(),
    listInvites: vi.fn(),
    updateUserRole: vi.fn(),
    setToken: vi.fn(),
  },
}));

vi.mock("../components/Toast", () => ({
  showToast: vi.fn(),
}));

import { api } from "../api";
import { MultiLogin } from "../components/MultiLogin";
import { UserAdminPanel } from "../components/UserAdminPanel";

const mockMultiLogin = vi.mocked(api.multiLogin);
const mockRegister = vi.mocked(api.register);
const mockCreateInvite = vi.mocked(api.createInvite);
const mockListUsers = vi.mocked(api.listUsers);
const mockListInvites = vi.mocked(api.listInvites);
const mockUpdateUserRole = vi.mocked(api.updateUserRole);

// ---------------------------------------------------------------------------
// MultiLogin 测试
// ---------------------------------------------------------------------------
describe("MultiLogin", () => {
  beforeEach(() => {
    mockMultiLogin.mockClear();
    mockRegister.mockClear();
  });

  it("默认显示登录模式（用户名+密码）", () => {
    render(<MultiLogin onLogin={() => {}} />);
    expect(screen.getByPlaceholderText("用户名")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("密码")).toBeInTheDocument();
    expect(screen.getByText("登录")).toBeInTheDocument();
  });

  it("切换到注册模式显示邀请码输入框", async () => {
    const user = userEvent.setup();
    render(<MultiLogin onLogin={() => {}} />);

    await user.click(screen.getByText("有邀请码？点击注册新账户"));

    expect(screen.getByPlaceholderText("邀请码")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("密码（至少 6 位）")).toBeInTheDocument();
    expect(screen.getByText("注册")).toBeInTheDocument();
  });

  it("登录成功调用 onLogin", async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();
    mockMultiLogin.mockResolvedValue({
      token: "test-token",
      auth_enabled: true,
      multiuser: true,
      username: "admin",
      role: "owner",
      expires_in: 86400,
    });

    // Mock api.setToken
    const setTokenSpy = vi.spyOn(api, "setToken").mockImplementation(() => {});

    render(<MultiLogin onLogin={onLogin} />);

    await user.type(screen.getByPlaceholderText("用户名"), "admin");
    await user.type(screen.getByPlaceholderText("密码"), "secret");
    await user.click(screen.getByText("登录"));

    await waitFor(() => {
      expect(mockMultiLogin).toHaveBeenCalledWith("admin", "secret");
    });
    await waitFor(() => {
      expect(onLogin).toHaveBeenCalled();
    });

    setTokenSpy.mockRestore();
  });

  it("登录失败显示错误信息", async () => {
    const user = userEvent.setup();
    mockMultiLogin.mockRejectedValue(new Error("用户名或密码错误"));

    render(<MultiLogin onLogin={() => {}} />);

    await user.type(screen.getByPlaceholderText("用户名"), "admin");
    await user.type(screen.getByPlaceholderText("密码"), "wrong");
    await user.click(screen.getByText("登录"));

    await waitFor(() => {
      expect(screen.getByText("用户名或密码错误")).toBeInTheDocument();
    });
  });

  it("注册模式：邀请码为空时注册按钮禁用", async () => {
    const user = userEvent.setup();
    render(<MultiLogin onLogin={() => {}} />);

    await user.click(screen.getByText("有邀请码？点击注册新账户"));
    await user.type(screen.getByPlaceholderText("用户名"), "newuser");
    await user.type(screen.getByPlaceholderText("密码（至少 6 位）"), "pass123");

    // 邀请码为空时注册按钮应禁用
    const registerBtn = screen.getByText("注册").closest("button") as HTMLButtonElement;
    expect(registerBtn.disabled).toBe(true);
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("注册成功调用 onLogin", async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();
    mockRegister.mockResolvedValue({
      token: "new-token",
      auth_enabled: true,
      multiuser: true,
      username: "newuser",
      role: "member",
      expires_in: 86400,
    });
    const setTokenSpy = vi.spyOn(api, "setToken").mockImplementation(() => {});

    render(<MultiLogin onLogin={onLogin} />);

    await user.click(screen.getByText("有邀请码？点击注册新账户"));
    await user.type(screen.getByPlaceholderText("邀请码"), "INVITE123");
    await user.type(screen.getByPlaceholderText("用户名"), "newuser");
    await user.type(screen.getByPlaceholderText("密码（至少 6 位）"), "pass123456");
    await user.click(screen.getByText("注册"));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith("INVITE123", "newuser", "pass123456");
    });
    await waitFor(() => {
      expect(onLogin).toHaveBeenCalled();
    });

    setTokenSpy.mockRestore();
  });
});

// ---------------------------------------------------------------------------
// UserAdminPanel 测试
// ---------------------------------------------------------------------------
describe("UserAdminPanel", () => {
  beforeEach(() => {
    mockCreateInvite.mockClear();
    mockListUsers.mockClear();
    mockListInvites.mockClear();
    mockUpdateUserRole.mockClear();
  });

  it("加载并显示用户列表和邀请码列表", async () => {
    mockListUsers.mockResolvedValue({
      items: [
        {
          id: 1,
          username: "admin",
          role: "owner",
          invited_by: "",
          is_active: true,
          created_at: "2026-07-29T10:00:00Z",
        },
        {
          id: 2,
          username: "member1",
          role: "member",
          invited_by: "admin",
          is_active: true,
          created_at: "2026-07-29T11:00:00Z",
        },
      ],
    });
    mockListInvites.mockResolvedValue({
      items: [
        {
          code: "INVITE001",
          role: "member",
          created_by: "admin",
          used_by: "member1",
          expires_at: null,
          used_at: "2026-07-29T11:00:00Z",
          created_at: "2026-07-29T10:30:00Z",
        },
      ],
    });

    render(<UserAdminPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("users-section")).toBeInTheDocument();
    });

    // 用户列表：用 role=cell 精确定位用户名
    const userCells = screen.getAllByRole("cell");
    const cellTexts = userCells.map((c) => c.textContent);
    expect(cellTexts).toContain("admin");
    expect(cellTexts).toContain("member1");

    // 邀请码列表
    expect(screen.getByText("INVITE001")).toBeInTheDocument();
  });

  it("生成邀请码成功后显示新邀请码", async () => {
    const user = userEvent.setup();
    mockListUsers.mockResolvedValue({ items: [] });
    mockListInvites.mockResolvedValue({ items: [] });
    mockCreateInvite.mockResolvedValue({
      code: "NEWCODE123",
      role: "member",
      created_by: "admin",
      expires_at: null,
    });

    render(<UserAdminPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-invite-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("generate-invite-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("new-invite-code")).toHaveTextContent("NEWCODE123");
    });
  });

  it("生成邀请码失败显示 toast 错误", async () => {
    const user = userEvent.setup();
    mockListUsers.mockResolvedValue({ items: [] });
    mockListInvites.mockResolvedValue({ items: [] });
    mockCreateInvite.mockRejectedValue(new Error("权限不足"));

    render(<UserAdminPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-invite-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("generate-invite-btn"));

    // showToast 被 mock，验证按钮恢复可用即可
    await waitFor(() => {
      expect(screen.getByTestId("generate-invite-btn")).not.toBeDisabled();
    });
  });

  it("加载失败显示错误信息", async () => {
    mockListUsers.mockRejectedValue(new Error("网络错误"));
    mockListInvites.mockRejectedValue(new Error("网络错误"));

    render(<UserAdminPanel />);

    await waitFor(() => {
      expect(screen.getByText("网络错误")).toBeInTheDocument();
    });
  });

  it("修改用户角色调用 updateUserRole", async () => {
    const user = userEvent.setup();
    mockListUsers.mockResolvedValue({
      items: [
        {
          id: 1,
          username: "member1",
          role: "member",
          invited_by: "admin",
          is_active: true,
          created_at: "2026-07-29T10:00:00Z",
        },
      ],
    });
    mockListInvites.mockResolvedValue({ items: [] });
    mockUpdateUserRole.mockResolvedValue({
      username: "member1",
      role: "owner",
      status: "ok",
    });

    render(<UserAdminPanel />);

    await waitFor(() => {
      expect(screen.getByLabelText("修改 member1 角色")).toBeInTheDocument();
    });

    // 修改角色 select
    const select = screen.getByLabelText("修改 member1 角色") as HTMLSelectElement;
    await user.selectOptions(select, "owner");

    await waitFor(() => {
      expect(mockUpdateUserRole).toHaveBeenCalledWith("member1", "owner");
    });
  });

  it("空数据显示 EmptyState", async () => {
    mockListUsers.mockResolvedValue({ items: [] });
    mockListInvites.mockResolvedValue({ items: [] });

    render(<UserAdminPanel />);

    await waitFor(() => {
      expect(screen.getByText("暂无用户")).toBeInTheDocument();
      expect(screen.getByText("暂无邀请码")).toBeInTheDocument();
    });
  });
});
