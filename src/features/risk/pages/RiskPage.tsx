import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  activateRiskRule,
  deactivateRiskRule,
  getRiskEvents,
  getRiskOverview,
  getRiskRules,
  RiskRule,
} from "@/features/risk/api/getRiskOverview";
import { riskQueryKeys } from "@/features/risk/hooks/riskQueryKeys";
import { useRiskRealtime } from "@/features/risk/hooks/useRiskRealtime";
import { formatCurrency, formatNumber } from "@/shared/lib/format";
import { DataState } from "@/shared/ui/DataState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionCard } from "@/shared/ui/SectionCard";

export function RiskPage() {
  const queryClient = useQueryClient();
  const summaryQuery = useQuery({
    queryKey: riskQueryKeys.summary(),
    queryFn: getRiskOverview,
  });
  const rulesQuery = useQuery({
    queryKey: riskQueryKeys.rules(),
    queryFn: getRiskRules,
    placeholderData: (previous) => previous,
  });
  const eventsQuery = useQuery({
    queryKey: riskQueryKeys.events(),
    queryFn: () => getRiskEvents({ accountId: summaryQuery.data?.accountId ?? undefined, limit: 20 }),
    enabled: Boolean(summaryQuery.data),
    placeholderData: (previous) => previous,
  });

  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);

  useRiskRealtime(summaryQuery.data?.accountId);

  useEffect(() => {
    if (!rulesQuery.data?.length) {
      setSelectedRuleId(null);
      return;
    }

    if (!selectedRuleId || !rulesQuery.data.some((rule) => rule.id === selectedRuleId)) {
      setSelectedRuleId(rulesQuery.data[0].id);
    }
  }, [rulesQuery.data, selectedRuleId]);

  const selectedRule = rulesQuery.data?.find((rule) => rule.id === selectedRuleId) ?? rulesQuery.data?.[0] ?? null;

  const refreshQueries = () => {
    queryClient.invalidateQueries({ queryKey: riskQueryKeys.summary() });
    queryClient.invalidateQueries({ queryKey: riskQueryKeys.rules() });
    queryClient.invalidateQueries({ queryKey: riskQueryKeys.events() });
  };

  const activateMutation = useMutation({
    mutationFn: activateRiskRule,
    onSuccess: (result) => {
      if (result) {
        queryClient.setQueryData<RiskRule[] | undefined>(riskQueryKeys.rules(), (current) =>
          current?.map((rule) => (rule.id === result.id ? result : rule)) ?? current,
        );
      }

      refreshQueries();
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: deactivateRiskRule,
    onSuccess: (result) => {
      if (result) {
        queryClient.setQueryData<RiskRule[] | undefined>(riskQueryKeys.rules(), (current) =>
          current?.map((rule) => (rule.id === result.id ? result : rule)) ?? current,
        );
      }

      refreshQueries();
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Risk"
        title="风控规则与命中事件"
        description="规则列表、版本信息、启停状态和命中事件全部来自后端风险 DTO，启停操作会刷新当前视图。"
      />

      <DataState isLoading={summaryQuery.isPending} error={summaryQuery.error instanceof Error ? summaryQuery.error.message : null} isEmpty={!summaryQuery.data}>
        {summaryQuery.data ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Active Rules" value={formatNumber(summaryQuery.data.activeRules)} />
              <MetricCard label="Triggered Today" value={formatNumber(summaryQuery.data.triggeredToday)} />
              <MetricCard label="Blocked Orders" value={formatNumber(summaryQuery.data.blockedOrdersToday)} />
              <MetricCard label="Open Alerts" value={formatNumber(summaryQuery.data.unresolvedEvents)} />
            </div>

            <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
              <SectionCard title="规则列表" subtitle="点击规则查看阈值、适用范围和版本快照。">
                <DataState
                  isLoading={rulesQuery.isPending}
                  error={rulesQuery.error instanceof Error ? rulesQuery.error.message : null}
                  isEmpty={!rulesQuery.data?.length}
                  emptyTitle="暂无风控规则"
                >
                  <div className="space-y-3">
                    {rulesQuery.data?.map((rule) => (
                      <button
                        key={rule.id}
                        type="button"
                        onClick={() => setSelectedRuleId(rule.id)}
                        className={[
                          "w-full rounded-2xl border px-4 py-4 text-left transition",
                          selectedRule?.id === rule.id
                            ? "border-cyan-500/40 bg-cyan-500/10"
                            : "border-slate-800 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-900/70",
                        ].join(" ")}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-sm font-semibold text-white">{rule.name}</p>
                            <p className="mt-1 text-xs text-slate-500">
                              {rule.type} · v{rule.version}
                            </p>
                          </div>
                          <span className={`rounded-full border px-2.5 py-0.5 text-[11px] uppercase tracking-[0.18em] ${ruleTone(rule.status)}`}>
                            {rule.status}
                          </span>
                        </div>
                        <p className="mt-3 text-sm text-slate-300">{rule.description || "后端返回了规则定义，但未附带描述。"}</p>
                        <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-500">
                          {rule.scope.symbols.slice(0, 3).map((symbol) => (
                            <span key={symbol} className="rounded-full border border-slate-800 bg-slate-950/60 px-2.5 py-1">
                              {symbol}
                            </span>
                          ))}
                          {rule.scope.symbols.length === 0 ? <span className="rounded-full border border-slate-800 bg-slate-950/60 px-2.5 py-1">全标的</span> : null}
                        </div>
                      </button>
                    ))}
                  </div>
                </DataState>
              </SectionCard>

              <SectionCard
                title="规则详情与版本"
                subtitle="启停操作走真实 API；版本历史来自规则 DTO 的版本数组。"
                action={
                  selectedRule ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={activateMutation.isPending || selectedRule.enabled}
                        onClick={() => activateMutation.mutate(selectedRule.id)}
                        className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-200 transition disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        启用
                      </button>
                      <button
                        type="button"
                        disabled={deactivateMutation.isPending || !selectedRule.enabled}
                        onClick={() => deactivateMutation.mutate(selectedRule.id)}
                        className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-200 transition disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        停用
                      </button>
                    </div>
                  ) : null
                }
              >
                {selectedRule ? (
                  <div className="space-y-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <InfoBlock label="规则 ID" value={selectedRule.id} mono />
                      <InfoBlock label="当前版本" value={selectedRule.version} />
                      <InfoBlock
                        label="阈值"
                        value={
                          selectedRule.thresholdValue !== null
                            ? `${selectedRule.thresholdLabel} ${formatRuleThreshold(selectedRule.thresholdValue, selectedRule.thresholdUnit)}`
                            : selectedRule.thresholdLabel
                        }
                      />
                      <InfoBlock label="状态" value={selectedRule.status} />
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <InfoBlock label="适用账户" value={formatList(selectedRule.scope.accountIds, "全部账户")} />
                      <InfoBlock label="适用标的" value={formatList(selectedRule.scope.symbols, "全部标的")} />
                      <InfoBlock label="适用策略" value={formatList(selectedRule.scope.strategies, "全部策略")} />
                      <InfoBlock label="适用市场" value={formatList(selectedRule.scope.venues, "全部市场")} />
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">版本历史</p>
                      <div className="mt-4 space-y-3">
                        {selectedRule.versions.length > 0 ? (
                          selectedRule.versions.map((version) => (
                            <div key={version.version} className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
                              <div className="flex items-start justify-between gap-4">
                                <div>
                                  <p className="text-sm font-semibold text-white">{version.version}</p>
                                  <p className="mt-1 text-xs text-slate-500">{version.createdAt ?? "未知时间"}</p>
                                </div>
                                {version.changeReason ? <span className="text-xs text-slate-400">{version.changeReason}</span> : null}
                              </div>
                              {version.createdBy ? <p className="mt-2 text-sm text-slate-300">变更人：{version.createdBy}</p> : null}
                            </div>
                          ))
                        ) : (
                          <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-400">后端尚未返回版本历史，仅展示当前版本。</div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">请选择一条规则查看详情。</div>
                )}
              </SectionCard>
            </div>

            <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
              <SectionCard title="硬限制与约束" subtitle="来自 /risk/summary 的整体风控摘要。">
                <div className="space-y-3">
                  <InfoBlock
                    label="单笔下单金额上限"
                    value={summaryQuery.data.hardLimits.maxSingleOrderValue !== null ? formatCurrency(summaryQuery.data.hardLimits.maxSingleOrderValue) : "--"}
                  />
                  <InfoBlock
                    label="日亏损阈值"
                    value={summaryQuery.data.hardLimits.maxDailyLoss !== null ? formatCurrency(summaryQuery.data.hardLimits.maxDailyLoss) : "--"}
                  />
                  <InfoBlock
                    label="仓位上限"
                    value={summaryQuery.data.hardLimits.maxPositionSizePercent !== null ? `${summaryQuery.data.hardLimits.maxPositionSizePercent}%` : "--"}
                  />
                  <InfoBlock label="盘中交易限制" value={summaryQuery.data.restrictions.marketHoursOnly ? "仅允许交易时段内下单" : "未限制交易时段"} />
                  <InfoBlock label="受限标的" value={formatList(summaryQuery.data.restrictions.restrictedSymbols, "暂无")} />
                </div>
              </SectionCard>

              <SectionCard title="最近命中事件" subtitle="事件流会跟随 WebSocket 追加，页面刷新后由查询层补齐。">
                <DataState
                  isLoading={eventsQuery.isPending}
                  error={eventsQuery.error instanceof Error ? eventsQuery.error.message : null}
                  isEmpty={!eventsQuery.data?.length && !summaryQuery.data.recentEvents.length}
                  emptyTitle="暂无命中事件"
                >
                  <div className="space-y-3">
                    {(eventsQuery.data?.length ? eventsQuery.data : summaryQuery.data.recentEvents).map((event) => (
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
                        <div className="mt-3 text-xs text-slate-500">
                          {event.orderId ? <span className="mr-3">Order: {event.orderId}</span> : null}
                          {event.clientOrderId ? <span>Client: {event.clientOrderId}</span> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                </DataState>
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

function InfoBlock({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={["mt-2 text-sm text-white", mono ? "font-mono" : ""].join(" ")}>{value}</p>
    </div>
  );
}

function formatRuleThreshold(value: number, unit: string | null) {
  if (unit) {
    const normalizedUnit = unit.trim().toLowerCase();

    if (normalizedUnit === "%" || normalizedUnit === "percent") {
      return `${value}%`;
    }

    if (normalizedUnit === "usd" || normalizedUnit === "$" || normalizedUnit === "currency") {
      return formatCurrency(value);
    }

    return `${formatNumber(value)} ${unit}`;
  }

  return formatCurrency(value);
}

function formatList(values: string[], fallback: string) {
  return values.length > 0 ? values.join(", ") : fallback;
}

function ruleTone(status: RiskRule["status"]) {
  switch (status) {
    case "ACTIVE":
      return "border-emerald-900/50 bg-emerald-950/30 text-emerald-300";
    case "PAUSED":
      return "border-amber-900/50 bg-amber-950/30 text-amber-300";
    case "INACTIVE":
      return "border-slate-800 bg-slate-900/40 text-slate-300";
    case "DRAFT":
      return "border-cyan-900/50 bg-cyan-950/30 text-cyan-300";
    default:
      return "border-slate-800 bg-slate-900/40 text-slate-300";
  }
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
