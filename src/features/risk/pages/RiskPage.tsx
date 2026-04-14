import { useQuery } from "@tanstack/react-query";

import { getRiskOverview } from "@/features/risk/api/getRiskOverview";
import { formatCurrency } from "@/shared/lib/format";
import { DataState } from "@/shared/ui/DataState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionCard } from "@/shared/ui/SectionCard";

export function RiskPage() {
  const { data, isPending, error } = useQuery({
    queryKey: ["risk-summary"],
    queryFn: getRiskOverview,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Risk"
        title="风控规则与命中事件"
        description="风控页面已经切换到统一查询层，Phase 1 可以在此基础上接入预检查和命中事件流。"
      />

      <DataState isLoading={isPending} error={error instanceof Error ? error.message : null} isEmpty={!data}>
        {data ? (
          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <SectionCard title="Hard Limits" subtitle="一期保留全局/账户级硬限制。">
              <div className="space-y-4">
                <RiskMetric label="Max Daily Loss" value={formatCurrency(data.hardLimits.maxDailyLoss)} />
                <RiskMetric label="Max Single Order Value" value={formatCurrency(data.hardLimits.maxSingleOrderValue)} />
                <RiskMetric label="Max Position Size" value={`${data.hardLimits.maxPositionSizePercent}%`} />
              </div>
            </SectionCard>

            <SectionCard title="Restrictions" subtitle="用于标的黑名单和交易时段限制。">
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-800 bg-ink-950 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Restricted Symbols</p>
                  <p className="mt-3 font-mono text-sm text-white">{data.restrictions.restrictedSymbols.join(", ")}</p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-ink-950 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Market Hours Only</p>
                  <p className="mt-3 text-sm text-white">{data.restrictions.marketHoursOnly ? "Enabled" : "Disabled"}</p>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Recent Events" subtitle="后续可直接接 WebSocket 风险频道。" className="xl:col-span-2">
              <div className="space-y-3">
                {data.recentEvents.map((event) => (
                  <div key={event.id} className="rounded-2xl border border-slate-800 bg-ink-950 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-white">{event.message}</p>
                        <p className="mt-2 text-xs text-slate-500">{event.occurredAt}</p>
                      </div>
                      <span className="rounded-full border border-amber-900/40 bg-amber-950/30 px-3 py-1 text-xs uppercase tracking-[0.18em] text-amber-300">
                        {event.severity}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>
        ) : null}
      </DataState>
    </div>
  );
}

function RiskMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-ink-950 p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}
