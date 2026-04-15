import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { getDashboardEquityCurve, getDashboardOverview } from "@/features/dashboard/api/getDashboardOverview";
import { dashboardQueryKeys } from "@/features/dashboard/hooks/dashboardQueryKeys";
import { useDashboardRealtime } from "@/features/dashboard/hooks/useDashboardRealtime";
import { formatCurrency, formatNumber, formatPercent } from "@/shared/lib/format";
import { DataState } from "@/shared/ui/DataState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionCard } from "@/shared/ui/SectionCard";

export function DashboardPage() {
  const overviewQuery = useQuery({
    queryKey: dashboardQueryKeys.overview(),
    queryFn: getDashboardOverview,
  });

  const equityCurveQuery = useQuery({
    queryKey: dashboardQueryKeys.equityCurve(),
    queryFn: getDashboardEquityCurve,
    placeholderData: (previous) => previous,
  });

  useDashboardRealtime(overviewQuery.data?.account.id);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Dashboard"
        title="账户与风险概览"
        description="Dashboard 直接读取后端聚合接口，账户、持仓、PnL、风险告警和净值曲线都会随真实数据刷新。"
      />

      <DataState isLoading={overviewQuery.isPending} error={overviewQuery.error instanceof Error ? overviewQuery.error.message : null} isEmpty={!overviewQuery.data}>
        {overviewQuery.data ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="净值" value={formatCurrency(overviewQuery.data.account.equity)} />
              <MetricCard label="现金" value={formatCurrency(overviewQuery.data.account.cash)} />
              <MetricCard label="购买力" value={formatCurrency(overviewQuery.data.account.buyingPower)} />
              <MetricCard label="日内 PnL" value={`${formatCurrency(overviewQuery.data.account.dayPnl)} (${formatPercent(overviewQuery.data.account.dayPnlPercent)})`} />
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
              <SectionCard title="净值曲线" subtitle="直接读取 /dashboard/equity-curve 的时间序列，不再使用本地示例数据。">
                <DataState
                  isLoading={equityCurveQuery.isPending}
                  error={equityCurveQuery.error instanceof Error ? equityCurveQuery.error.message : null}
                  isEmpty={!equityCurveQuery.data?.length}
                  emptyTitle="暂无净值曲线数据"
                >
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={equityCurveQuery.data ?? []}>
                        <defs>
                          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.32} />
                            <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid stroke="#172036" vertical={false} />
                        <XAxis dataKey="label" stroke="#64748b" tickLine={false} axisLine={false} minTickGap={24} />
                        <YAxis stroke="#64748b" tickLine={false} axisLine={false} width={72} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#020617", border: "1px solid #1e293b", borderRadius: "16px" }}
                          labelStyle={{ color: "#e2e8f0" }}
                          formatter={(value) => formatCurrency(Number(value))}
                        />
                        <Area type="monotone" dataKey="value" stroke="#22d3ee" fill="url(#equityGradient)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </DataState>
              </SectionCard>

              <SectionCard
                title="PnL 与持仓摘要"
                subtitle="后端聚合数据直接驱动，供运营和交易两个角色共享。"
                action={
                  <div className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs uppercase tracking-[0.18em] text-cyan-200">
                    {overviewQuery.data.health.label}
                  </div>
                }
              >
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <MiniStat label="当日 PnL" value={formatCurrency(overviewQuery.data.pnl.day)} />
                    <MiniStat label="总损益" value={formatCurrency(overviewQuery.data.pnl.total)} />
                    <MiniStat label="未实现 PnL" value={formatCurrency(overviewQuery.data.pnl.unrealized)} />
                    <MiniStat label="持仓总数" value={formatNumber(overviewQuery.data.positionStats.totalPositions)} />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <MiniStat label="多头 / 空头" value={`${overviewQuery.data.positionStats.longPositions} / ${overviewQuery.data.positionStats.shortPositions}`} />
                    <MiniStat label="总敞口" value={formatCurrency(overviewQuery.data.positionStats.grossExposure)} />
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">实时健康</p>
                    <p className="mt-2 text-sm text-slate-200">{overviewQuery.data.health.message}</p>
                    <p className="mt-3 text-xs text-slate-500">最后更新：{overviewQuery.data.updatedAt ?? "实时查询"}</p>
                  </div>
                </div>
              </SectionCard>
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
              <SectionCard title="持仓明细" subtitle="标准化持仓 DTO 直接来自后端聚合接口。">
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-[0.18em] text-slate-500">
                      <tr>
                        <th className="pb-3">Symbol</th>
                        <th className="pb-3 text-right">Qty</th>
                        <th className="pb-3 text-right">Avg</th>
                        <th className="pb-3 text-right">Mark</th>
                        <th className="pb-3 text-right">Value</th>
                        <th className="pb-3 text-right">Unrealized</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900">
                      {overviewQuery.data.positions.map((position) => (
                        <tr key={position.symbol}>
                          <td className="py-3 font-semibold text-white">{position.symbol}</td>
                          <td className="py-3 text-right font-mono text-slate-300">{formatNumber(position.quantity)}</td>
                          <td className="py-3 text-right font-mono text-slate-300">{formatCurrency(position.avgPrice)}</td>
                          <td className="py-3 text-right font-mono text-slate-300">{formatCurrency(position.marketPrice)}</td>
                          <td className="py-3 text-right font-mono text-slate-300">{formatCurrency(position.marketValue)}</td>
                          <td className="py-3 text-right font-mono text-cyan-300">{formatCurrency(position.unrealizedPnl)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </SectionCard>

              <SectionCard title="最近风险告警" subtitle="risk.events.<account_id> 实时频道会把新事件追加到这里。">
                <div className="space-y-3">
                  {overviewQuery.data.recentAlerts.length > 0 ? (
                    overviewQuery.data.recentAlerts.map((event) => (
                      <div key={event.id} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold text-white">{event.ruleName ?? event.title}</p>
                              <span className={`rounded-full border px-2.5 py-0.5 text-[11px] uppercase tracking-[0.18em] ${severityTone(event.severity)}`}>
                                {event.severity}
                              </span>
                            </div>
                            <p className="mt-2 text-sm text-slate-300">{event.message}</p>
                          </div>
                          <div className="text-right text-xs text-slate-500">
                            <p>{event.occurredAt}</p>
                            <p className="mt-1">{event.status}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">当前没有风险告警事件。</div>
                  )}
                </div>
              </SectionCard>
            </div>
          </>
        ) : null}
      </DataState>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-5">
      <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

function severityTone(severity: string) {
  switch (severity) {
    case "CRITICAL":
      return "border-rose-900/50 bg-rose-950/30 text-rose-300";
    case "HIGH":
      return "border-orange-900/50 bg-orange-950/30 text-orange-300";
    case "MEDIUM":
      return "border-amber-900/50 bg-amber-950/30 text-amber-300";
    case "LOW":
      return "border-cyan-900/50 bg-cyan-950/30 text-cyan-300";
    default:
      return "border-slate-800 bg-slate-900/40 text-slate-300";
  }
}
