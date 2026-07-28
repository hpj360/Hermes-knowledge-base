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

/** usePrompt 返回值：prompt 触发函数 + 渲染到组件树的 dialog 节点 */
interface UsePromptReturn {
  /** 弹出输入对话框；返回用户输入的字符串，用户取消返回 null（空串确认为 ""） */
  prompt: (message: string, defaultValue?: string) => Promise<string | null>;
  /** 渲染到组件树中的 Modal 节点 */
  dialog: React.ReactNode;
}

/**
 * 输入对话框 Hook：替代 window.prompt
 *
 * 用法：
 *   const { prompt, dialog } = usePrompt();
 *   const reason = await prompt("请输入驳回理由");
 *   if (reason === null) return; // 用户取消
 *   // reason 为字符串（可能为空串）
 *
 * 实现要点（与 useConfirm 模式一致）：
 * - 标题固定「请输入」(font-serif via .modal-title)，message 作为独立段落 (font-body)
 * - input 用 .input 语义类 (font-ui)，aria-label 关联 message 保证 a11y
 * - 确定按钮 .btn-primary，取消按钮 .btn-ghost
 * - Enter 触发确定，Escape 触发取消（Modal 内置 ESC 监听 → onClose）
 * - 确定返回输入值（空串为 ""），取消返回 null
 */
export function usePrompt(): UsePromptReturn {
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
        setInputValue(defaultValue ?? "");
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

  // 延迟导入 Modal（Modal.tsx 是命名导出，需重命名为 default 以适配 React.lazy）
  const Modal = React.useMemo(() => {
    return React.lazy(() => import("./Modal").then((m) => ({ default: m.Modal })));
  }, []);

  const dialog = state.open ? (
    <React.Suspense fallback={null}>
      <Modal open={true} title="请输入" onClose={() => handleClose(null)}>
        <p
          className="mb-4"
          style={{ color: "var(--ink-900)", fontFamily: "var(--font-body)" }}
        >
          {state.message}
        </p>
        <input
          type="text"
          className="input mb-4"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleClose(inputValue);
            }
          }}
          aria-label={state.message || "请输入"}
          autoFocus
        />
        <div className="flex gap-3 justify-end">
          <button className="btn-ghost" onClick={() => handleClose(null)}>
            取消
          </button>
          <button
            className="btn-primary"
            onClick={() => handleClose(inputValue)}
          >
            确认
          </button>
        </div>
      </Modal>
    </React.Suspense>
  ) : null;

  return { prompt, dialog };
}

// ============================================================================
// MagazineCard / GoldFoilCard / LabMetric / DailyRecipeCard
// 杂志式语义卡片（对应 design/mockup/_components.css 语义类）
// 设计原则：语义类承载布局/装饰（_components.css），inline var(--*) 强化 token
// ============================================================================

// ----------------------------------------------------------------------------
// MagazineCard —— 杂志式配方卡片（对应 .recipe-card-magazine）
// 5 区结构：thumb / kicker / title / deck / meta
// ----------------------------------------------------------------------------

/** MagazineCard.Meta 子组件 Props：渲染 spirit + abv 两个子项或自定义 children */
interface MagazineCardMetaProps {
  spirit?: React.ReactNode;
  abv?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

/** MagazineCard.Meta：meta 区子组件，含 spirit/abv 两个子项或 children 兜底 */
function MagazineCardMeta({
  spirit,
  abv,
  children,
  className = "",
}: MagazineCardMetaProps) {
  return (
    <div className={`mag-meta ${className}`}>
      {spirit && (
        <span
          className="mag-spirit"
          style={{
            color: "var(--brand-700)",
            fontFamily: "var(--font-ui)",
          }}
        >
          {spirit}
        </span>
      )}
      {abv && (
        <span
          className="mag-abv"
          style={{
            color: "var(--gold-700)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {abv}
        </span>
      )}
      {children}
    </div>
  );
}

/** 杂志式配方卡片 Props */
interface MagazineCardProps {
  title: React.ReactNode;
  kicker?: string;
  deck?: React.ReactNode;
  thumb?: string;
  meta?: React.ReactNode;
  className?: string;
  onClick?: () => void;
  children?: React.ReactNode;
}

/** 杂志式配方卡片：5 区结构（thumb/kicker/title/deck/meta），对应 .recipe-card-magazine */
function MagazineCardImpl({
  title,
  kicker,
  deck,
  thumb,
  meta,
  className = "",
  onClick,
  children,
}: MagazineCardProps) {
  return (
    <div
      className={`recipe-card-magazine ${className}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {thumb ? (
        <img className="mag-thumb" src={thumb} alt="" />
      ) : (
        <div className="mag-thumb-placeholder" aria-hidden="true" />
      )}
      <div className="mag-body">
        {kicker && (
          <p
            className="mag-kicker"
            style={{
              color: "var(--gold-700)",
              fontFamily: "var(--font-ui)",
            }}
          >
            {kicker}
          </p>
        )}
        <h3
          className="mag-title"
          style={{
            color: "var(--ink-900)",
            fontFamily: "var(--font-serif)",
          }}
        >
          {title}
        </h3>
        {deck && (
          <p
            className="mag-deck"
            style={{
              color: "var(--ink-600)",
              fontFamily: "var(--font-serif)",
            }}
          >
            {deck}
          </p>
        )}
        {meta}
        {children}
      </div>
    </div>
  );
}

export const MagazineCard = Object.assign(MagazineCardImpl, {
  Meta: MagazineCardMeta,
});

// ----------------------------------------------------------------------------
// GoldFoilCard —— 金箔英雄卡片（对应 .gold-foil-card）
// ::before 伪元素金箔边框由 _components.css 实现，组件只需应用类名
// ----------------------------------------------------------------------------

/** 金箔英雄卡片 Props */
interface GoldFoilCardProps {
  title?: React.ReactNode;
  quote?: React.ReactNode;
  attribution?: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}

/** 金箔英雄卡片：金箔边框 + 金箔标题 + 斜体引文 + 归属，对应 .gold-foil-card */
export function GoldFoilCard({
  title,
  quote,
  attribution,
  className = "",
  children,
}: GoldFoilCardProps) {
  return (
    <div className={`gold-foil-card ${className}`}>
      {title && (
        <div className="foil-title" style={{ fontFamily: "var(--font-serif)" }}>
          {title}
        </div>
      )}
      {quote && (
        <div
          className="foil-quote"
          style={{
            color: "var(--ink-900)",
            fontFamily: "var(--font-serif)",
          }}
        >
          {quote}
        </div>
      )}
      {attribution && (
        <div
          className="foil-attribution"
          style={{
            color: "var(--ink-400)",
            fontFamily: "var(--font-ui)",
          }}
        >
          {attribution}
        </div>
      )}
      {children}
    </div>
  );
}

// ----------------------------------------------------------------------------
// LabMetric —— 实验室指标格（对应 .lab-metric）
// ----------------------------------------------------------------------------

/** 实验室指标格 Props */
interface LabMetricProps {
  label: string;
  num: React.ReactNode;
  sub?: string;
  alert?: boolean;
  className?: string;
}

/** 实验室指标格：label + num + sub，alert 变体 num 用 gold-700，对应 .lab-metric */
export function LabMetric({
  label,
  num,
  sub,
  alert = false,
  className = "",
}: LabMetricProps) {
  return (
    <div className={`lab-metric ${alert ? "alert" : ""} ${className}`}>
      <div
        className="lab-label"
        style={{
          color: "var(--ink-400)",
          fontFamily: "var(--font-ui)",
        }}
      >
        {label}
      </div>
      <div
        className="lab-num"
        style={{
          color: alert ? "var(--gold-700)" : "var(--ink-900)",
          fontFamily: "var(--font-serif)",
        }}
      >
        {num}
      </div>
      {sub && (
        <div
          className="lab-sub"
          style={{
            color: "var(--brand-700)",
            fontFamily: "var(--font-ui)",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------------
// DailyRecipeCard —— 今日推荐卡（对应 .daily-recipe）
// hover 抬升效果由 _components.css 实现
// ----------------------------------------------------------------------------

/** 今日推荐卡 Props */
interface DailyRecipeCardProps {
  badge?: string;
  name: React.ReactNode;
  reason?: string;
  className?: string;
  onClick?: () => void;
  href?: string;
}

/** 今日推荐卡：badge + name + reason，hover 抬升，对应 .daily-recipe */
export function DailyRecipeCard({
  badge,
  name,
  reason,
  className = "",
  onClick,
  href,
}: DailyRecipeCardProps) {
  const cls = `daily-recipe ${className}`;
  const inner = (
    <>
      {badge && (
        <span
          className="daily-badge"
          style={{
            background: "var(--gold-500)",
            color: "var(--ink-900)",
          }}
        >
          {badge}
        </span>
      )}
      <span
        className="daily-name"
        style={{
          color: "var(--ink-900)",
          fontFamily: "var(--font-serif)",
        }}
      >
        {name}
      </span>
      {reason && (
        <span
          className="daily-reason"
          style={{
            color: "var(--ink-400)",
            fontFamily: "var(--font-ui)",
          }}
        >
          {reason}
        </span>
      )}
    </>
  );

  if (href) {
    return (
      <a href={href} className={cls}>
        {inner}
      </a>
    );
  }

  return (
    <div
      className={cls}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {inner}
    </div>
  );
}

// ============================================================================
// P2 包豪斯几何 + 极简现代组件库
//
// 设计宪法：白底 + 粗体大写 + 3px 粗边框 + 领域色实色几何 + 微圆角 2px
// 全部使用 design tokens（var(--*)），无硬编码 hex，支持 className 透传。
// 语义类定义在 index.css 末尾（非 layer 区域，覆盖 _components.css 同名类）。
// ============================================================================

/** 包豪斯强调色变体 */
export type BauhausAccent = "wine" | "amber" | "bronze" | "ink";

/** 包豪斯卡片：2px 黑边框 + 左上角实色方块 + 大写标题 */
export function BauhausCard({
  title,
  meta,
  accent = "wine",
  className = "",
  children,
  ...rest
}: {
  title?: React.ReactNode;
  meta?: React.ReactNode;
  accent?: BauhausAccent;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "title">) {
  return (
    <div className={`bauhaus-card accent-${accent} ${className}`} {...rest}>
      {title && <div className="bauhaus-card-title">{title}</div>}
      {meta && <div className="bauhaus-card-meta">{meta}</div>}
      {children}
    </div>
  );
}

/** 包豪斯指标卡变体 */
export type BauhausMetricVariant = "wine" | "amber" | "bronze" | "outline";

/** 包豪斯指标卡：实色填充 + 反白数字 */
export function BauhausMetric({
  num,
  label,
  variant = "outline",
  className = "",
  ...rest
}: {
  num: React.ReactNode;
  label: React.ReactNode;
  variant?: BauhausMetricVariant;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`bauhaus-metric variant-${variant} ${className}`} {...rest}>
      <div className="bauhaus-metric-num">{num}</div>
      <div className="bauhaus-metric-label">{label}</div>
    </div>
  );
}

/** 包豪斯 chip：实色填充 + mono 大写 */
export function BauhausChip({
  variant = "wine",
  className = "",
  children,
  ...rest
}: {
  variant?: BauhausMetricVariant;
} & React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span className={`bauhaus-chip variant-${variant} ${className}`} {...rest}>
      {children}
    </span>
  );
}

/** 包豪斯按钮变体 */
export type BauhausBtnVariant = "solid" | "accent" | "outline";

/** 包豪斯按钮：mono 大写 + 2px 黑边 */
export function BauhausButton({
  variant = "solid",
  className = "",
  type = "button",
  children,
  ...rest
}: {
  variant?: BauhausBtnVariant;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={`bauhaus-btn variant-${variant} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}

/** 包豪斯章节标签：mono 大写 + 44×4 黑色前条 */
export function BauhausSectionLabel({
  className = "",
  children,
  ...rest
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`bauhaus-section-label ${className}`} {...rest}>
      {children}
    </div>
  );
}

/** 包豪斯大标题：black 700 + 大写 + 微收紧 */
export function BauhausDisplay({
  className = "",
  as: Tag = "h2",
  children,
  ...rest
}: {
  as?: React.ElementType;
} & React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <Tag className={`bauhaus-display ${className}`} {...rest}>
      {children}
    </Tag>
  );
}

/** 几何装饰位置 */
export type BauhausGeometryPos = "tr" | "br" | "ml";

/** 几何装饰组件：角落圆形色块（适度密度，opacity 0.1-0.15） */
export function BauhausGeometry({
  positions = ["tr", "br"],
  className = "",
}: {
  positions?: BauhausGeometryPos[];
  className?: string;
}) {
  return (
    <>
      {positions.map((pos) => (
        <span
          key={pos}
          className={`bauhaus-geometry pos-${pos} ${className}`}
          aria-hidden="true"
        />
      ))}
    </>
  );
}

/** 包豪斯布局：主内容 + 右辅助面板（移动端折叠） */
export function BauhausLayout({
  main,
  aside,
  className = "",
}: {
  main: React.ReactNode;
  aside?: React.ReactNode;
  className?: string;
}) {
  if (!aside) {
    return <div className={className}>{main}</div>;
  }
  return (
    <div className={`bauhaus-layout ${className}`}>
      <div>{main}</div>
      <aside>{aside}</aside>
    </div>
  );
}

/** 包豪斯导航栏 brand mark：酒红实色方块 */
export function BauhausBrandMark({ className = "" }: { className?: string }) {
  return <span className={`brand-mark ${className}`} aria-hidden="true" />;
}
