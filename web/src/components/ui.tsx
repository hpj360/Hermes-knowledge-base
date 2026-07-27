/**
 * R2 阶段：基础 UI 组件库
 *
 * 目的：消除 40+ 处重复的 inline style，建立语义化组件层。
 * 设计原则：
 * - 优先使用 design tokens（var(--*)），不硬编码颜色
 * - 字体：标题用 --font-serif，元信息/UI 用 --font-ui，数据用 --font-mono
 * - 所有组件支持 className 透传，便于 Tailwind 工具类补充
 * - 不引入 styled-components/emotion，纯 CSS-in-JS + tokens
 */
import React from "react";

// ============================================================================
// MetaText / MonoText —— 元信息文字（替换 40+ 处 inline style）
// ============================================================================

/** 元信息文字：ink-400 色 + UI 无衬线字体，用于提示/说明/meta */
export function MetaText({
  children,
  className = "",
  as: Tag = "p",
  ...rest
}: {
  children: React.ReactNode;
  className?: string;
  as?: React.ElementType;
} & React.HTMLAttributes<HTMLElement>) {
  return (
    <Tag
      className={className}
      style={{
        color: "var(--ink-400)",
        fontFamily: "var(--font-ui)",
        ...((rest as { style?: React.CSSProperties }).style || {}),
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}

/** 等宽数据文字：ink-400 色 + mono 字体，用于 doc_id/score/chunk 索引 */
export function MonoText({
  children,
  className = "",
  as: Tag = "span",
  ...rest
}: {
  children: React.ReactNode;
  className?: string;
  as?: React.ElementType;
} & React.HTMLAttributes<HTMLElement>) {
  return (
    <Tag
      className={className}
      style={{
        color: "var(--ink-400)",
        fontFamily: "var(--font-mono)",
        ...((rest as { style?: React.CSSProperties }).style || {}),
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}

/** 正文文字：ink-900 色 + body 衬线字体，用于正文段落 */
export function BodyText({
  children,
  className = "",
  as: Tag = "p",
  ...rest
}: {
  children: React.ReactNode;
  className?: string;
  as?: React.ElementType;
} & React.HTMLAttributes<HTMLElement>) {
  return (
    <Tag
      className={className}
      style={{
        color: "var(--ink-900)",
        fontFamily: "var(--font-body)",
        ...((rest as { style?: React.CSSProperties }).style || {}),
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}

/** 标题文字：ink-900 色 + serif 字体，用于卡片标题/区块标题 */
export function HeadingText({
  children,
  className = "",
  as: Tag = "h3",
  size = "1.05rem",
  ...rest
}: {
  children: React.ReactNode;
  className?: string;
  as?: React.ElementType;
  size?: string;
} & React.HTMLAttributes<HTMLElement>) {
  return (
    <Tag
      className={className}
      style={{
        fontFamily: "var(--font-serif)",
        color: "var(--ink-900)",
        fontSize: size,
        fontWeight: 600,
        ...((rest as { style?: React.CSSProperties }).style || {}),
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}

// ============================================================================
// StatusBadge / Chip —— 状态徽章与标签
// ============================================================================

type BadgeVariant =
  | "brand" // 品牌红
  | "gold" // 金色
  | "success" // 绿色（已审核/成功）
  | "danger" // 红色（隐藏/错误）
  | "warning" // 橙色（待审核/警告）
  | "ink" // 灰色（中性）
  | "info"; // 蓝色（信息）

const BADGE_STYLES: Record<BadgeVariant, React.CSSProperties> = {
  brand: { background: "var(--brand-50)", color: "var(--brand-700)" },
  gold: { background: "var(--gold-100)", color: "var(--gold-700)" },
  success: { background: "rgba(46, 125, 91, 0.12)", color: "var(--success)" },
  danger: { background: "rgba(179, 38, 30, 0.1)", color: "var(--danger)" },
  warning: { background: "rgba(199, 122, 26, 0.12)", color: "var(--warning)" },
  ink: { background: "var(--ink-100)", color: "var(--ink-600)" },
  info: { background: "rgba(44, 111, 181, 0.12)", color: "var(--info)" },
};

/** 状态徽章：圆角 pill，用于 status/verified/hidden/source/season 等状态标记 */
export function StatusBadge({
  children,
  variant = "ink",
  className = "",
  pill = true,
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
  pill?: boolean;
}) {
  return (
    <span
      className={`text-xs px-1.5 py-0.5 ${pill ? "rounded-full" : "rounded"} ${className}`}
      style={BADGE_STYLES[variant]}
    >
      {children}
    </span>
  );
}

/** 标签 Chip：可选中，用于材料选择/标签筛选 */
export function Chip({
  children,
  selected = false,
  onClick,
  className = "",
  disabled = false,
}: {
  children: React.ReactNode;
  selected?: boolean;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`text-xs px-3 py-1 rounded-full border transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      style={
        selected
          ? { background: "var(--brand-700)", color: "#fff", borderColor: "var(--brand-700)" }
          : {
              background: "var(--ink-100)",
              color: "var(--ink-600)",
              borderColor: "var(--ink-200)",
              cursor: "pointer",
            }
      }
    >
      {children}
    </button>
  );
}

// ============================================================================
// EmptyState / ErrorBanner —— 状态占位
// ============================================================================

/** 空状态：居中 + eyebrow + 标题 + 描述，用于列表为空时 */
export function EmptyState({
  eyebrow = "EMPTY",
  title,
  description,
  className = "",
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  className?: string;
}) {
  return (
    <div className={`card p-6 mb-4 text-center ${className}`}>
      <p className="eyebrow mb-2">{eyebrow}</p>
      <p className="section-title mb-2">{title}</p>
      {description && <MetaText className="text-sm">{description}</MetaText>}
    </div>
  );
}

/** 错误横幅：红色背景 + 错误信息，用于 API 失败/表单错误 */
export function ErrorBanner({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      className={`mb-3 ${className}`}
      style={{ color: "var(--danger)", fontFamily: "var(--font-ui)" }}
      role="alert"
    >
      {children}
    </p>
  );
}

// ============================================================================
// FormField —— 表单字段（label + input/select/textarea）
// ============================================================================

export function FormField({
  label,
  children,
  className = "",
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <label
        className="text-xs block mb-1"
        style={{ color: "var(--ink-600)", fontFamily: "var(--font-ui)" }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}

// ============================================================================
// Logo —— SVG 酒杯图标（替代 emoji 🍷）
// ============================================================================

/** Hermes 品牌 Logo：高脚杯 SVG，替代 emoji 🍷 */
export function Logo({
  size = 24,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      {/* 高脚杯轮廓 */}
      <path
        d="M5 3 L19 3 L13 11 L13 20 L16 20 L16 21 L8 21 L8 20 L11 20 L11 11 Z"
        fill="currentColor"
        opacity="0.9"
      />
      {/* 杯身金色高光 */}
      <path
        d="M7 4 L17 4 L13 10 L11 10 Z"
        fill="var(--gold-500)"
        opacity="0.6"
      />
    </svg>
  );
}

// ============================================================================
// ConfirmDialog —— 确认对话框（替代 window.confirm）
// ============================================================================

/**
 * 确认对话框 Hook：替代 window.confirm
 *
 * 用法：
 *   const { confirm, dialog } = useConfirm();
 *   if (await confirm("确定删除？")) { ... }
 *   return <>{dialog}</>;
 */
export function useConfirm() {
  // 延迟导入 Modal 避免循环依赖
  const [state, setState] = React.useState<{
    open: boolean;
    message: string;
    resolve?: (value: boolean) => void;
  }>({ open: false, message: "" });

  const confirm = React.useCallback((message: string): Promise<boolean> => {
    return new Promise((resolve) => {
      setState({ open: true, message, resolve });
    });
  }, []);

  const handleClose = React.useCallback(
    (result: boolean) => {
      state.resolve?.(result);
      setState({ open: false, message: "" });
    },
    [state]
  );

  // 延迟导入 Modal（Modal.tsx 是命名导出，需重命名为 default 以适配 React.lazy）
  const Modal = React.useMemo(() => {
    return React.lazy(() => import("./Modal").then((m) => ({ default: m.Modal })));
  }, []);

  const dialog = state.open ? (
    <React.Suspense fallback={null}>
      <Modal
        open={true}
        title="请确认"
        onClose={() => handleClose(false)}
      >
        <p
          className="mb-6"
          style={{ color: "var(--ink-900)", fontFamily: "var(--font-body)" }}
        >
          {state.message}
        </p>
        <div className="flex gap-3 justify-end">
          <button className="btn-secondary" onClick={() => handleClose(false)}>
            取消
          </button>
          <button className="btn-primary" onClick={() => handleClose(true)}>
            确认
          </button>
        </div>
      </Modal>
    </React.Suspense>
  ) : null;

  return { confirm, dialog };
}

// ============================================================================
// PromptDialog —— 输入对话框（替代 window.prompt）
// ============================================================================

/**
 * 输入对话框 Hook：替代 window.prompt
 *
 * 用法：
 *   const { prompt, dialog } = usePrompt();
 *   const reason = await prompt("请输入驳回理由");
 *   if (reason) { ... }
 */
export function usePrompt() {
  const [state, setState] = React.useState<{
    open: boolean;
    message: string;
    defaultValue?: string;
    resolve?: (value: string | null) => void;
  }>({ open: false, message: "" });

  const [inputValue, setInputValue] = React.useState("");

  const prompt = React.useCallback(
    (message: string, defaultValue?: string): Promise<string | null> => {
      return new Promise((resolve) => {
        setState({ open: true, message, defaultValue, resolve });
        setInputValue(defaultValue || "");
      });
    },
    []
  );

  const handleClose = React.useCallback(
    (result: string | null) => {
      state.resolve?.(result);
      setState({ open: false, message: "" });
      setInputValue("");
    },
    [state]
  );

  const Modal = React.useMemo(() => {
    return React.lazy(() => import("./Modal").then((m) => ({ default: m.Modal })));
  }, []);

  const dialog = state.open ? (
    <React.Suspense fallback={null}>
      <Modal
        open={true}
        title={state.message}
        onClose={() => handleClose(null)}
      >
        <textarea
          className="input mb-4"
          style={{ minHeight: "80px" }}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          autoFocus
        />
        <div className="flex gap-3 justify-end">
          <button className="btn-secondary" onClick={() => handleClose(null)}>
            取消
          </button>
          <button
            className="btn-primary"
            onClick={() => handleClose(inputValue || null)}
          >
            确认
          </button>
        </div>
      </Modal>
    </React.Suspense>
  ) : null;

  return { prompt, dialog };
}
