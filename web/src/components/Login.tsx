import { useState } from "react";
import { api } from "../api";

interface LoginProps {
  onLogin: () => void;
}

/** 登录页（M1-07）：单用户密码认证。杂志式氛围登录卡。 */
export function Login({ onLogin }: LoginProps) {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await api.login(password);
      if (!result.auth_enabled) {
        // 未启用认证直接进入
        onLogin();
        return;
      }
      api.setToken(result.token);
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
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
        {/* 顶部金线 */}
        <hr className="divider-gold mb-8" />

        <div className="text-center mb-8">
          <div className="text-5xl mb-4">🍷</div>
          <p className="eyebrow mb-3" style={{ color: "var(--gold-300)" }}>ACCESS</p>
          <h2
            className="text-gold-foil mb-3"
            style={{ fontFamily: "var(--font-serif)", fontSize: "1.75rem", fontWeight: 600 }}
          >
            Hermes 知识库
          </h2>
          <p
            className="text-sm"
            style={{ color: "rgba(250, 243, 220, 0.6)", fontFamily: "var(--font-sans)" }}
          >
            请输入访问密码
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            className="input"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
            disabled={loading}
            style={{
              background: "rgba(255, 255, 255, 0.08)",
              borderColor: "rgba(201, 162, 39, 0.4)",
              color: "#fff",
            }}
          />
          {error && (
            <p
              className="text-sm px-3 py-2 rounded"
              style={{
                background: "rgba(179, 38, 30, 0.2)",
                color: "var(--danger)",
                fontFamily: "var(--font-sans)",
              }}
            >
              {error}
            </p>
          )}
          <button
            type="submit"
            className="btn-primary w-full"
            disabled={loading || !password}
          >
            {loading ? "登录中..." : "登录"}
          </button>
        </form>

        {/* 底部金线 */}
        <hr className="divider-gold mt-8" />
      </div>
    </div>
  );
}
