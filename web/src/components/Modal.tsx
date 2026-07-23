import { useEffect } from "react";

interface ModalProps {
  open: boolean;
  title?: string;
  onClose: () => void;
  children: React.ReactNode;
  /** 自定义宽度（默认 480px） */
  maxWidth?: number;
  /** 底部操作区（按钮组） */
  footer?: React.ReactNode;
}

/**
 * 杂志式 Modal。
 * - 复用 _components.css 的 .modal-overlay / .modal / .modal-title 类
 * - ESC 关闭 + 点遮罩关闭 + 滚动锁定 + a11y role=dialog
 * - 不依赖任何 portal，直接 fixed 定位
 */
export function Modal({ open, title, onClose, children, maxWidth = 480, footer }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="modal-overlay active"
      role="dialog"
      aria-modal="true"
      aria-label={title || "对话框"}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="modal"
        style={{ maxWidth: `${maxWidth}px` }}
        onClick={(e) => e.stopPropagation()}
      >
        {title && <h3 className="modal-title">{title}</h3>}
        <div>{children}</div>
        {footer && (
          <div
            style={{
              marginTop: "var(--sp-5)",
              paddingTop: "var(--sp-4)",
              borderTop: "1px solid var(--ink-200)",
              display: "flex",
              justifyContent: "flex-end",
              gap: "var(--sp-2)",
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
