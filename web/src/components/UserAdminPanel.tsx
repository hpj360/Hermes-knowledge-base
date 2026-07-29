import { useEffect, useState } from "react";
import { api } from "../api";
import type { InviteCodeItem, InviteCodeListItem, UserItem } from "../types";
import { showToast } from "./Toast";
import {
  BauhausButton,
  BauhausChip,
  BauhausSectionLabel,
  EmptyState,
  ErrorBanner,
  MetaText,
} from "./ui";

/**
 * V3-Task10：用户管理面板（仅 owner 可见）。
 *
 * 功能：
 * - 生成邀请码（member/viewer 角色，可选有效期）
 * - 查看用户列表（用户名/角色/邀请人/状态）
 * - 修改用户角色（owner/member/viewer）
 * - 查看邀请码使用情况
 */
export function UserAdminPanel() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [invites, setInvites] = useState<InviteCodeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [newInvite, setNewInvite] = useState<InviteCodeItem | null>(null);
  const [inviteRole, setInviteRole] = useState("member");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [usersResp, invitesResp] = await Promise.all([
        api.listUsers(),
        api.listInvites(),
      ]);
      setUsers(usersResp.items);
      setInvites(invitesResp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleGenerateInvite = async () => {
    setGenerating(true);
    setNewInvite(null);
    try {
      const result = await api.createInvite(inviteRole);
      setNewInvite(result);
      showToast("邀请码已生成", "success");
      await load();
    } catch (err) {
      showToast(`生成失败：${err instanceof Error ? err.message : err}`, "danger");
    } finally {
      setGenerating(false);
    }
  };

  const handleUpdateRole = async (username: string, newRole: string) => {
    try {
      await api.updateUserRole(username, newRole);
      showToast(`已将 ${username} 角色改为 ${newRole}`, "success");
      await load();
    } catch (err) {
      showToast(`修改失败：${err instanceof Error ? err.message : err}`, "danger");
    }
  };

  if (loading) {
    return (
      <div className="p-4">
        <MetaText className="text-xs">加载中…</MetaText>
      </div>
    );
  }
  if (error) {
    return (
      <div className="p-4">
        <ErrorBanner>{error}</ErrorBanner>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="user-admin-panel">
      {/* 邀请码生成 */}
      <section
        className="bauhaus-card accent-amber p-4"
        data-testid="invite-section"
      >
        <BauhausSectionLabel className="mb-3">生成邀请码</BauhausSectionLabel>
        <div className="flex items-center gap-3 flex-wrap mb-3">
          <label
            className="text-xs"
            style={{ color: "var(--ink-700)", fontFamily: "var(--font-ui)" }}
          >
            角色：
          </label>
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            className="input"
            style={{ width: "auto", padding: "0.25rem 0.5rem" }}
            disabled={generating}
            aria-label="邀请角色"
          >
            <option value="member">member（可创建 UGC）</option>
            <option value="viewer">viewer（只读）</option>
          </select>
          <BauhausButton
            variant="solid"
            onClick={handleGenerateInvite}
            disabled={generating}
            data-testid="generate-invite-btn"
          >
            {generating ? "生成中…" : "生成邀请码"}
          </BauhausButton>
        </div>
        {newInvite && (
          <div
            className="p-3 mt-2"
            style={{
              background: "var(--paper)",
              border: "1px solid var(--amber)",
              borderRadius: "var(--r-sm)",
            }}
          >
            <MetaText className="text-xs mb-1">新邀请码（复制分享给被邀请人）：</MetaText>
            <code
              className="block p-2"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "1rem",
                fontWeight: 700,
                color: "var(--amber)",
                background: "var(--paper)",
                wordBreak: "break-all",
              }}
              data-testid="new-invite-code"
            >
              {newInvite.code}
            </code>
            <MetaText className="text-xs mt-1">
              角色：{newInvite.role} ·{" "}
              {newInvite.expires_at
                ? `过期：${new Date(newInvite.expires_at).toLocaleString("zh-CN")}`
                : "永久有效"}
            </MetaText>
          </div>
        )}
      </section>

      {/* 用户列表 */}
      <section
        className="bauhaus-card p-4"
        data-testid="users-section"
      >
        <BauhausSectionLabel className="mb-3">用户列表</BauhausSectionLabel>
        {users.length === 0 ? (
          <EmptyState title="暂无用户" description="" />
        ) : (
          <table
            className="w-full text-sm"
            style={{ borderCollapse: "collapse" }}
          >
            <thead>
              <tr style={{ borderBottom: "2px solid var(--ink-900)" }}>
                <th className="text-left py-2 px-2">用户名</th>
                <th className="text-left py-2 px-2">角色</th>
                <th className="text-left py-2 px-2">邀请人</th>
                <th className="text-left py-2 px-2">状态</th>
                <th className="text-left py-2 px-2">创建时间</th>
                <th className="text-left py-2 px-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.id}
                  style={{ borderBottom: "1px solid var(--ink-100)" }}
                >
                  <td
                    className="py-2 px-2"
                    style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}
                  >
                    {u.username}
                  </td>
                  <td className="py-2 px-2">
                    <BauhausChip
                      variant={u.role === "owner" ? "wine" : "outline"}
                    >
                      {u.role}
                    </BauhausChip>
                  </td>
                  <td className="py-2 px-2" style={{ color: "var(--ink-500)" }}>
                    {u.invited_by || "—"}
                  </td>
                  <td className="py-2 px-2">
                    {u.is_active ? (
                      <span style={{ color: "var(--bronze)" }}>活跃</span>
                    ) : (
                      <span style={{ color: "var(--danger)" }}>禁用</span>
                    )}
                  </td>
                  <td className="py-2 px-2" style={{ color: "var(--ink-500)" }}>
                    {u.created_at
                      ? new Date(u.created_at).toLocaleDateString("zh-CN")
                      : "—"}
                  </td>
                  <td className="py-2 px-2">
                    <select
                      value={u.role}
                      onChange={(e) => handleUpdateRole(u.username, e.target.value)}
                      className="input"
                      style={{
                        width: "auto",
                        padding: "0.15rem 0.3rem",
                        fontSize: "0.8rem",
                      }}
                      aria-label={`修改 ${u.username} 角色`}
                    >
                      <option value="owner">owner</option>
                      <option value="member">member</option>
                      <option value="viewer">viewer</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* 邀请码列表 */}
      <section
        className="bauhaus-card p-4"
        data-testid="invites-section"
      >
        <BauhausSectionLabel className="mb-3">邀请码记录</BauhausSectionLabel>
        {invites.length === 0 ? (
          <EmptyState title="暂无邀请码" description="" />
        ) : (
          <table
            className="w-full text-sm"
            style={{ borderCollapse: "collapse" }}
          >
            <thead>
              <tr style={{ borderBottom: "2px solid var(--ink-900)" }}>
                <th className="text-left py-2 px-2">邀请码</th>
                <th className="text-left py-2 px-2">角色</th>
                <th className="text-left py-2 px-2">创建者</th>
                <th className="text-left py-2 px-2">使用者</th>
                <th className="text-left py-2 px-2">状态</th>
              </tr>
            </thead>
            <tbody>
              {invites.map((inv) => {
                const isUsed = inv.used_by !== null;
                const isExpired =
                  inv.expires_at !== null &&
                  new Date(inv.expires_at) < new Date();
                return (
                  <tr
                    key={inv.code}
                    style={{ borderBottom: "1px solid var(--ink-100)" }}
                  >
                    <td
                      className="py-2 px-2"
                      style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}
                    >
                      {inv.code}
                    </td>
                    <td className="py-2 px-2">{inv.role}</td>
                    <td className="py-2 px-2" style={{ color: "var(--ink-500)" }}>
                      {inv.created_by}
                    </td>
                    <td className="py-2 px-2" style={{ color: "var(--ink-500)" }}>
                      {inv.used_by || "—"}
                    </td>
                    <td className="py-2 px-2">
                      {isUsed ? (
                        <span style={{ color: "var(--ink-400)" }}>已使用</span>
                      ) : isExpired ? (
                        <span style={{ color: "var(--danger)" }}>已过期</span>
                      ) : (
                        <span style={{ color: "var(--bronze)" }}>可用</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
