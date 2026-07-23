import { Component, ErrorInfo, ReactNode } from "react";

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
        <div
          className="max-w-md w-full overflow-hidden relative"
          style={{
            background: "#fff",
            border: "1px solid var(--ink-200)",
            borderRadius: "var(--r-lg)",
            boxShadow: "var(--shadow-drama)",
          }}
        >
          <div
            className="px-6 py-5"
            style={{
              background: "var(--brand-gradient)",
              borderBottom: "2px solid var(--gold-500)",
            }}
          >
            <p
              className="eyebrow mb-2"
              style={{ color: "var(--gold-300)" }}
            >
              ERROR
            </p>
            <h1
              className="text-gold-foil"
              style={{ fontFamily: "var(--font-serif)", fontSize: "1.5rem", fontWeight: 600 }}
            >
              页面出错了
            </h1>
            <p
              className="text-sm mt-1"
              style={{ color: "rgba(250, 243, 220, 0.75)", fontFamily: "var(--font-sans)" }}
            >
              Hermes 知识库遇到了一个渲染异常
            </p>
          </div>
          <div className="p-6">
            <p
              className="mb-4"
              style={{ color: "var(--ink-600)", fontFamily: "var(--font-sans)", fontSize: "var(--fs-sm)" }}
            >
              抱歉，应用在渲染时发生异常。您可以尝试重新加载页面；
              若问题持续，请联系管理员并附上下方错误信息。
            </p>
            <details className="mb-4 group">
              <summary
                className="cursor-pointer text-sm font-medium"
                style={{ color: "var(--brand-700)", fontFamily: "var(--font-sans)" }}
              >
                查看错误详情
              </summary>
              <pre
                className="mt-2 p-3 overflow-auto max-h-48 whitespace-pre-wrap break-all"
                style={{
                  background: "var(--ink-50)",
                  border: "1px solid var(--ink-200)",
                  borderRadius: "var(--r-sm)",
                  color: "var(--ink-600)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--fs-xs)",
                }}
              >
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
