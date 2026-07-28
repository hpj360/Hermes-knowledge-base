import { Component, ErrorInfo, ReactNode } from "react";
import { MetaText } from "./ui";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * React Error Boundary：捕获子组件渲染期同步错误，
 * 显示深酒红主题的降级 UI，避免整页白屏。
 *
 * 注意：Error Boundary 只能捕获渲染期、生命周期与构造函数中的同步错误，
 * 不捕获事件回调、异步代码（setTimeout/Promise）中的错误。
 *
 * R2 重构：卡片容器/顶部条/pre 用 Tailwind 工具类 + design token；
 * 错误标题保留 text-gold-foil 金箔效果（与 HeadingText 默认 ink-900 冲突，故用 h1 + className）；
 * 错误描述用 p + font-body/text-ink-600；操作 summary 用 font-ui；
 * inline style 仅保留渐变背景上的 rgba 透明文字（无对应 token）。
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // 控制台留痕，便于调试；不做上报以避免引入额外依赖
    console.error("[ErrorBoundary] 渲染异常：", error, info.componentStack);
  }

  private handleReload = (): void => {
    this.setState({ hasError: false, error: null });
    // 软重载以重置 React 组件状态
    window.location.reload();
  };

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;

    const message = this.state.error?.message || "未知错误";

    return (
      <div
        role="alert"
        className="min-h-screen flex items-center justify-center bg-brand-gradient bg-noise px-4"
      >
        <div className="max-w-md w-full overflow-hidden relative bg-[var(--paper)] border border-ink-200 rounded-[var(--r-lg)] shadow-drama">
          <div className="px-6 py-5 bg-brand-gradient border-b-2 border-gold-500">
            <p className="eyebrow mb-2 text-gold-300">ERROR</p>
            {/* 错误标题：保留 text-gold-foil 金箔效果（HeadingText 默认 ink-900 会覆盖金箔 transparent 色） */}
            <h1 className="text-gold-foil font-serif text-2xl font-semibold">
              页面出错了
            </h1>
            <MetaText
              as="p"
              className="text-sm mt-1"
              // 渐变背景上的透明文字：gold-100 75% 透明度，_tokens.css 未定义此色
              style={{ color: "rgba(250, 243, 220, 0.75)" }}
            >
              Hermes 知识库遇到了一个渲染异常
            </MetaText>
          </div>
          <div className="p-6">
            <p className="mb-4 font-body text-ink-600 text-sm">
              抱歉，应用在渲染时发生异常。您可以尝试重新加载页面；
              若问题持续，请联系管理员并附上下方错误信息。
            </p>
            <details className="mb-4 group">
              <summary className="cursor-pointer text-sm font-medium text-brand-700 font-ui">
                查看错误详情
              </summary>
              <pre className="mt-2 p-3 overflow-auto max-h-48 whitespace-pre-wrap break-all bg-ink-50 border border-ink-200 rounded text-ink-600 font-mono text-xs">
                {message}
              </pre>
            </details>
            <button
              type="button"
              onClick={this.handleReload}
              className="btn-primary w-full"
            >
              重新加载页面
            </button>
          </div>
        </div>
      </div>
    );
  }
}
