import { useEffect, useState } from "react";

export interface ToastState {
  id: number;
  message: string;
  variant?: "info" | "success" | "warning" | "danger";
}

let _nextId = 1;
const listeners = new Set<(t: ToastState) => void>();

/** 触发一个 toast（无须 provider，全局单例）。 */
export function showToast(
  message: string,
  variant: ToastState["variant"] = "info"
): void {
  const t: ToastState = { id: _nextId++, message, variant };
  listeners.forEach((fn) => fn(t));
}

/**
 * 全局 Toast 容器。挂在 App 顶层一次即可。
 * 设计：参考 _components.css 的 .toast 类，固定右下角，2.5s 自动消失。
 */
export function ToastHost() {
  const [toasts, setToasts] = useState<ToastState[]>([]);

  useEffect(() => {
    const handler = (t: ToastState) => {
      setToasts((prev) => [...prev, t]);
      // 2.5s 后自动移除
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((x) => x.id !== t.id));
      }, 2500);
    };
    listeners.add(handler);
    return () => {
      listeners.delete(handler);
    };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      style={{
        position: "fixed",
        bottom: "var(--sp-8)",
        right: "var(--sp-8)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-2)",
        zIndex: 200,
      }}
    >
      {toasts.map((t) => {
        const color =
          t.variant === "success"
            ? "var(--success)"
            : t.variant === "warning"
              ? "var(--warning)"
              : t.variant === "danger"
                ? "var(--danger)"
                : "var(--ink-900)";
        return (
          <div
            key={t.id}
            className="toast show"
            role="status"
            style={{
              background: color,
              color: "#fff",
              padding: "var(--sp-3) var(--sp-6)",
              borderRadius: "var(--r-md)",
              fontSize: "var(--fs-sm)",
              boxShadow: "var(--shadow-lg)",
              opacity: 1,
              transform: "none",
              position: "relative",
              maxWidth: "360px",
            }}
          >
            {t.message}
          </div>
        );
      })}
    </div>
  );
}
