import { useState } from "react";
import { api } from "../api";
import { Logo, BauhausSectionLabel, BauhausButton, MetaText } from "./ui";

interface MultiLoginProps {
  onLogin: () => void;
}

/**
 * V3-Task10：多用户模式登录页（用户名 + 密码）。
 *
 * - 启用 KB_MULTIUSER=true 时由 App 渲染此组件替代单用户 Login
 * - 首次登录触发 owner 初始化（后端自动完成）
 * - 支持切换到注册模式（邀请码注册）
 */
export function MultiLogin({ onLogin }: MultiLoginProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "login") {
        const result = await api.multiLogin(username, password);
        api.setToken(result.token);
        onLogin();
      } else {
        // 注册模式
        if (!inviteCode.trim()) {
          setError("请输入邀请码");
          return;
        }
        if (password.length < 6) {
          setError("密码至少 6 位");
          return;
        }
        const result = await api.register(inviteCode.trim(), username, password);
        api.setToken(result.token);
        onLogin();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-gradient bg-noise">
      <div
        className="max-w-md w-full mx-6 p-10 relative"
        style={{
          background: "rgba(255, 255, 255, 0.06)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(201, 162, 39, 0.3)",
          borderRadius: "var(--r-lg)",
        }}
      >
        <hr className="divider-gold mb-8" />

        <div className="text-center mb-8">
          <div className="mb-4" style={{ color: "var(--amber)" }}>
            <Logo size={56} />
          </div>
          <BauhausSectionLabel
            className="mb-3"
            style={{ color: "var(--gold-300)" }}
          >
            {mode === "login" ? "SIGN IN" : "REGISTER"}
          </BauhausSectionLabel>
          <h2
            className="text-gold-foil mb-3"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "1.75rem",
              fontWeight: 600,
            }}
          >
            Hermes 知识库
          </h2>
          <p
            className="text-sm"
            style={{
              color: "rgba(250, 243, 220, 0.6)",
              fontFamily: "var(--font-ui)",
            }}
          >
            {mode === "login"
              ? "多用户协作模式，请输入用户名和密码"
              : "输入邀请码注册新账户"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <input
              type="text"
              className="input"
              placeholder="邀请码"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              autoFocus
              disabled={loading}
              style={{
                background: "rgba(255, 255, 255, 0.08)",
                borderColor: "rgba(201, 162, 39, 0.4)",
                color: "#fff",
              }}
              aria-label="邀请码"
            />
          )}
          <input
            type="text"
            className="input"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus={mode === "login"}
            disabled={loading}
            style={{
              background: "rgba(255, 255, 255, 0.08)",
              borderColor: "rgba(201, 162, 39, 0.4)",
              color: "#fff",
            }}
            aria-label="用户名"
          />
          <input
            type="password"
            className="input"
            placeholder={mode === "register" ? "密码（至少 6 位）" : "密码"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            style={{
              background: "rgba(255, 255, 255, 0.08)",
              borderColor: "rgba(201, 162, 39, 0.4)",
              color: "#fff",
            }}
            aria-label="密码"
          />
          {error && (
            <p
              className="text-sm px-3 py-2 rounded"
              style={{
                background: "rgba(179, 38, 30, 0.2)",
                color: "var(--danger)",
                fontFamily: "var(--font-ui)",
              }}
            >
              {error}
            </p>
          )}
          <BauhausButton
            variant="solid"
            type="submit"
            className="w-full"
            disabled={
              loading ||
              !username ||
              !password ||
              (mode === "register" && !inviteCode)
            }
          >
            {loading
              ? "处理中..."
              : mode === "login"
                ? "登录"
                : "注册"}
          </BauhausButton>
        </form>

        {/* 切换登录/注册模式 */}
        <div className="mt-4 text-center">
          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
              setInviteCode("");
            }}
            className="text-xs"
            style={{
              color: "rgba(250, 243, 220, 0.7)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              textDecoration: "underline",
              fontFamily: "var(--font-ui)",
            }}
          >
            {mode === "login"
              ? "有邀请码？点击注册新账户"
              : "已有账户？返回登录"}
          </button>
        </div>

        <hr className="divider-gold mt-8" />
      </div>
    </div>
  );
}
