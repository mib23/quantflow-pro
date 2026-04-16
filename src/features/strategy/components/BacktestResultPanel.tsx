import { Download, TrendingUp } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { BacktestJob, BacktestResult } from "@/shared/types/domain";
import { formatCurrency, formatNumber, formatPercent } from "@/shared/lib/format";
import { SectionCard } from "@/shared/ui/SectionCard";

type BacktestResultPanelProps = {
  selectedJob: BacktestJob | null;
  result: BacktestResult | null;
  isLoading: boolean;
  error: string | null;
  onDownloadReport: (jobId: string) => Promise<void>;
};

export function BacktestResultPanel({ selectedJob, result, isLoading, error, onDownloadReport }: BacktestResultPanelProps) {
  return (
    <SectionCard
      title="结果详情"
      subtitle={selectedJob ? `${selectedJob.strategyName} ${selectedJob.strategyVersionTag} 的标准化回测结果。` : "选择一条回测任务查看权益曲线和交易明细。"}
      action={
        selectedJob && result ? (
          <button
            type="button"
            onClick={() => onDownloadReport(selectedJob.id)}
            className="inline-flex items-center gap-2 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200 transition"
          >
            <Download className="h-4 w-4" />
            下载报告
          </button>
        ) : null
      }
    >
      {isLoading ? <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 text-sm text-slate-400">结果加载中...</div> : null}
      {error ? <div className="rounded-2xl border border-rose-900/40 bg-rose-950/20 p-5 text-sm text-rose-300">{error}</div> : null}
      {!isLoading && !error && selectedJob && !result ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 text-sm text-slate-400">这条任务还没有结果，继续轮询即可。</div>
      ) : null}
      {!selectedJob ? <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 text-sm text-slate-400">还没有选中任务。</div> : null}

      {result ? (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="总收益" value={formatPercent(Number(result.metrics.totalReturn ?? 0) * 100)} />
            <MetricCard label="Sharpe" value={formatNumber(Number(result.metrics.sharpe ?? 0))} />
            <MetricCard label="最大回撤" value={formatPercent(Number(result.metrics.maxDrawdown ?? 0) * 100)} />
            <MetricCard label="胜率" value={formatPercent(Number(result.metrics.winRate ?? 0) * 100)} />
            <MetricCard label="交易次数" value={formatNumber(Number(result.metrics.tradeCount ?? 0))} />
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-cyan-300" />
              <p className="text-sm font-semibold text-white">权益曲线</p>
            </div>
            <div className="mt-5 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={result.equityCurve}>
                  <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 12 }} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 12 }} tickFormatter={(value) => formatCurrency(Number(value))} />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  <Line type="monotone" dataKey="equity" stroke="#22d3ee" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5">
            <p className="text-sm font-semibold text-white">交易明细</p>
            <div className="mt-4 space-y-3">
              {result.trades.length > 0 ? (
                result.trades.map((trade, index) => (
                  <div key={`${String(trade.symbol ?? "trade")}-${index}`} className="rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-slate-200">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-semibold text-white">{String(trade.symbol ?? "UNKNOWN")}</p>
                      <p className="text-xs text-slate-500">{String(trade.side ?? "N/A")}</p>
                    </div>
                    <p className="mt-2 text-xs text-slate-400">PnL: {trade.pnl != null ? formatCurrency(Number(trade.pnl)) : "--"}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-400">暂时没有交易明细。</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}
