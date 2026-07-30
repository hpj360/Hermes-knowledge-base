/**
 * SubTask 13.4: OfflineBanner — 离线提示横幅
 *
 * 包豪斯风格：amber 实色背景 + ink-900 文字 + font-mono + uppercase + 3px 黑色底边。
 * 监听 window online/offline 事件，离线时在顶部显示提示，在线时不渲染。
 */
import { useEffect, useState } from "react";

export function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    // 初始检查（挂载时可能已处于离线）
    setIsOffline(!navigator.onLine);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (!isOffline) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="px-4 py-2 text-center text-xs"
      style={{
        background: "var(--amber)",
        color: "var(--ink-900)",
        borderBottom: "3px solid var(--ink-900)",
        fontFamily: "var(--font-mono)",
        textTransform: "uppercase",
        letterSpacing: "0.04em",
        fontWeight: 700,
      }}
    >
      离线模式 — 仅显示已缓存内容
    </div>
  );
}
