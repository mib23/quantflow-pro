import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { getDashboardOverview } from "@/features/dashboard/api/getDashboardOverview";
import { formatCurrency, formatPercent, formatNumber } from "@/shared/lib/format";
import { DataState } from "@/shared/ui/DataState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionCard } from "@/shared/ui/SectionCard";

export function DashboardPage() {
  const { data, isPending, error } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: getDashboardOverview,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Dashboard"
        title="账户与运行概览"
        description="当前页面已经切到路由结构，账户、持仓和关键指标通过统一查询层读取，后续可以平滑替换为真实 API。"
      />

      <DataState isLoading={isPending} error={error instanceof Error ? error.message : null} isEmpty={!data}>
        {data ? (
          <>
            <div className="grid gap-4 md:grid-cols-4">
              <MetricCard label="Equity" value={formatCurrency(data.account.equity)} />
              <MetricCard label="Cash" value={formatCurrency(data.account.cash)} />
              <MetricCard label="Buying Power" value={formatCurrency(data.account.buyingPower)} />
              <MetricCard label="Day P&L" value={`${formatCurrency(data.account.dayPnl)} (${formatPercent(data.account.dayPnlPercent)})`} />
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
              <SectionCard title="Equity Curve" subtitle="Query 层已预留真实指标接入点。">
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.equityCurve}>
                      <defs>
                        <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#172036" vertical={false} />
                      <XAxis dataKey="time" stroke="#64748b" tickLine={false} axisLine={false} />
                      <YAxis stroke="#64748b" tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ backgroundColor: "#020617", border: "1px solid #1e293b" }} />
                      <Area type="monotone" dataKey="value" stroke="#22d3ee" fill="url(#equityGradient)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </SectionCard>

              <SectionCard title="Strategies" subtitle="研究与交易角色后续按权限裁剪。">
                <div className="space-y-3">
                  {data.strategies.map((strategy) => (
                    <div key={strategy.id} className="rounded-2xl border border-slate-800 bg-ink-950 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold text-white">{strategy.name}</p>
                          <p className="mt-1 text-xs text-slate-500">{strategy.symbols.join(", ")}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{strategy.status}</p>
                          <p className="mt-1 text-sm font-mono text-cyan-300">{formatCurrency(strategy.dailyPnl)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </SectionCard>
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
              <SectionCard title="Positions" subtitle="真实接入时只替换查询函数，不改页面结构。">
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-[0.18em] text-slate-500">
                      <tr>
                        <th className="pb-3">Symbol</th>
                        <th className="pb-3 text-right">Qty</th>
                        <th className="pb-3 text-right">Avg</th>
                        <th className="pb-3 text-right">Last</th>
                        <th className="pb-3 text-right">Unrealized P&L</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900">
                      {data.positions.map((position) => (
                        <tr key={position.symbol}>
                          <td className="py-3 font-semibold text-white">{position.symbol}</td>
                          <td className="py-3 text-right font-mono text-slate-300">{formatNumber(position.quantity)}</td>
                          <td className="py-3 text-right font-mono text-slate-300">{formatCurrency(position.avgPrice)}</td>
                          <td className="py-3 text-right font-mono text-slate-300">{formatCurrency(position.marketPrice)}</td>
                          <td className="py-3 text-right font-mono text-cyan-300">{formatCurrency(position.unrealizedPnl)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </SectionCard>

              <SectionCard title="System Logs" subtitle="异常态与审计留痕后续从服务端事件流接入。">
                <div className="space-y-3">
                  {data.logs.map((entry) => (
                    <div key={entry.id} className="rounded-2xl border border-slate-800 bg-ink-950 p-3 text-sm">
                      <div className="flex items-center gap-3 font-mono text-xs text-slate-500">
                        <span>{entry.timestamp}</span>
                        <span>{entry.level}</span>
                      </div>
                      <p className="mt-2 text-slate-300">{entry.message}</p>
                    </div>
                  ))}
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
