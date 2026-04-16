import { Component, ReactNode } from "react";

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
};

export class AppErrorBoundary extends Component<Props, State> {
  public state: State = { hasError: false };

  public static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-ink-950 px-6">
          <div className="w-full max-w-xl rounded-3xl border border-rose-900/40 bg-slate-950/80 p-8 text-left shadow-2xl shadow-black/30">
            <p className="text-xs uppercase tracking-[0.3em] text-rose-400">System Fault</p>
            <h1 className="mt-4 text-3xl font-semibold text-white">前端发生未处理异常</h1>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              请刷新页面。如果问题持续出现，检查 API 可用性、环境变量和最近的模块改动。
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
