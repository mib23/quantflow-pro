import { ReactNode } from "react";

type DataStateProps = {
  isLoading?: boolean;
  error?: string | null;
  isEmpty?: boolean;
  emptyTitle?: string;
  children: ReactNode;
};

export function DataState({
  isLoading,
  error,
  isEmpty,
  emptyTitle = "暂无数据",
  children,
}: DataStateProps) {
  if (isLoading) {
    return <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-6 text-sm text-slate-400">数据加载中...</div>;
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-900/40 bg-rose-950/20 p-6 text-sm text-rose-300">
        {error}
      </div>
    );
  }

  if (isEmpty) {
    return <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-6 text-sm text-slate-400">{emptyTitle}</div>;
  }

  return <>{children}</>;
}
