import { useState } from "react";

import { OrderEntryForm } from "@/features/trading/components/OrderEntryForm";
import { useCancelTradingOrderMutation, useTradingAccountQuery, useTradingExecutionsQuery, useTradingOrdersQuery, useTradingQuoteQuery } from "@/features/trading/hooks/useTradingQueries";
import { useTradingRealtime } from "@/features/trading/hooks/useTradingRealtime";
import { formatCurrency, formatNumber } from "@/shared/lib/format";
import { DataState } from "@/shared/ui/DataState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionCard } from "@/shared/ui/SectionCard";

export function TradePage() {
  const [activeSymbol, setActiveSymbol] = useState("TSLA");
  const accountQuery = useTradingAccountQuery();
  const ordersQuery = useTradingOrdersQuery();
  const executionsQuery = useTradingExecutionsQuery();
  const quoteQuery = useTradingQuoteQuery(activeSymbol);
  const cancelOrderMutation = useCancelTradingOrderMutation();

  useTradingRealtime(activeSymbol, account?.id ?? null);

  const account = accountQuery.data?.account ?? null;
  const positions = accountQuery.data?.positions ?? [];
  const quote = quoteQuery.data ?? null;
  const referencePrice = quote?.last ?? quote?.ask ?? quote?.bid ?? null;
  const quoteSpread = quote?.ask != null && quote?.bid != null ? quote.ask - quote.bid : null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Trade"
        title="下单与订单状态工作台"
        description="账户、订单、成交和行情已拆成独立查询；提交与撤单都走真实 API，实时更新在 WebSocket 可用时自动接管。"
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-6">
          <SectionCard title="Market Snapshot" subtitle="当前标的的独立 quote 查询，不再依赖共享 mock。">
            <DataState
              isLoading={quoteQuery.isPending && !quote}
              error={quoteQuery.error instanceof Error ? quoteQuery.error.message : null}
              isEmpty={!quote}
              emptyTitle="请输入标的后加载行情。"
            >
              {quote ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Symbol</p>
                      <p className="mt-1 text-2xl font-semibold text-white">{quote.symbol}</p>
                    </div>
                    <div className="rounded-full border border-slate-800 bg-slate-950 px-3 py-1 text-xs uppercase tracking-[0.18em] text-cyan-300">
                      {quote.timestamp}
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-3">
                    <Metric label="Bid" value={quote.bid != null ? formatCurrency(quote.bid) : "N/A"} />
                    <Metric label="Ask" value={quote.ask != null ? formatCurrency(quote.ask) : "N/A"} />
                    <Metric label="Last" value={quote.last != null ? formatCurrency(quote.last) : "N/A"} />
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <Metric label="Spread" value={quoteSpread != null ? formatCurrency(quoteSpread) : "N/A"} />
                    <Metric label="Reference" value={referencePrice != null ? formatCurrency(referencePrice) : "N/A"} />
                  </div>
                </div>
              ) : null}
            </DataState>
          </SectionCard>

          <SectionCard title="Order Entry" subtitle="本地校验、提交 pending 状态和 idempotency key 均在 trading 目录内处理。">
            <OrderEntryForm
              brokerAccountId={account?.id ?? null}
              buyingPower={account?.buyingPower ?? 0}
              referencePrice={referencePrice}
              disabled={accountQuery.isPending || accountQuery.isError}
              onSymbolChange={setActiveSymbol}
            />
          </SectionCard>
        </div>

        <div className="space-y-6">
          <SectionCard title="Account Overview" subtitle="账户摘要与持仓来自独立查询。">
            <DataState
              isLoading={accountQuery.isPending}
              error={accountQuery.error instanceof Error ? accountQuery.error.message : null}
              isEmpty={!account}
              emptyTitle="暂无账户数据。"
            >
              {account ? (
                <div className="space-y-5">
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    <Metric label="Equity" value={formatCurrency(account.equity)} />
                    <Metric label="Cash" value={formatCurrency(account.cash)} />
                    <Metric label="Buying Power" value={formatCurrency(account.buyingPower)} />
                    <Metric label="Day PnL" value={formatCurrency(account.dayPnl)} />
                    <Metric label="Day PnL %" value={`${account.dayPnlPercent >= 0 ? "+" : ""}${account.dayPnlPercent.toFixed(2)}%`} />
                    <Metric label="Broker" value={`${account.broker} · ${account.environment}`} />
                  </div>

                  <div>
                    <p className="mb-3 text-xs uppercase tracking-[0.18em] text-slate-500">Positions</p>
                    {positions.length > 0 ? (
                      <div className="space-y-2">
                        {positions.map((position) => (
                          <div
                            key={position.symbol}
                            className="grid grid-cols-4 gap-3 rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm"
                          >
                            <div>
                              <p className="text-white">{position.symbol}</p>
                              <p className="text-xs text-slate-500">Avg {formatCurrency(position.avgPrice)}</p>
                            </div>
                            <p className="text-right font-mono text-slate-300">{formatNumber(position.quantity)}</p>
                            <p className="text-right font-mono text-slate-300">{formatCurrency(position.marketPrice)}</p>
                            <p className={`text-right font-mono ${position.unrealizedPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {formatCurrency(position.unrealizedPnl)}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">暂无持仓。</p>
                    )}
                  </div>
                </div>
              ) : null}
            </DataState>
          </SectionCard>

          <SectionCard title="Active Orders" subtitle="订单状态和撤单在交易页内闭环，后续由实时通道覆盖。">
            <DataState
              isLoading={ordersQuery.isPending}
              error={ordersQuery.error instanceof Error ? ordersQuery.error.message : null}
              isEmpty={!ordersQuery.data?.length}
              emptyTitle="暂无活跃订单。"
            >
              <div className="space-y-3">
                {ordersQuery.data?.map((order) => {
                  const canceling = cancelOrderMutation.isPending && cancelOrderMutation.variables === order.clientOrderId;

                  return (
                    <div key={order.clientOrderId} className="rounded-2xl border border-slate-800 bg-ink-950 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold text-white">{order.symbol}</p>
                          <p className="mt-1 text-xs text-slate-500">{order.clientOrderId}</p>
                        </div>
                        <p className={`text-xs uppercase tracking-[0.18em] ${getOrderStatusTone(order.status)}`}>{order.status}</p>
                      </div>
                      <div className="mt-4 grid grid-cols-3 gap-3 text-sm text-slate-300">
                        <div>
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Side</p>
                          <p className={order.side === "BUY" ? "text-emerald-400" : "text-rose-400"}>{order.side}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Qty</p>
                          <p className="font-mono">{formatNumber(order.quantity)}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Limit</p>
                          <p className="font-mono">{order.limitPrice ? formatCurrency(order.limitPrice) : "MKT"}</p>
                        </div>
                      </div>
                      <div className="mt-4 flex items-center justify-between gap-3">
                        <p className="text-xs text-slate-500">Submitted {order.submittedAt}</p>
                        <button
                          type="button"
                          disabled={canceling || order.status === "CANCELED" || order.status === "FILLED"}
                          onClick={() => cancelOrderMutation.mutate(order.clientOrderId)}
                          className="rounded-full border border-rose-900/50 bg-rose-950/30 px-3 py-1 text-xs text-rose-300 transition disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {canceling ? "撤单中..." : "Cancel"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </DataState>
          </SectionCard>

          <SectionCard title="Executions" subtitle="成交记录单独查询，若后端暂未提供该端点则显示为空。">
            <DataState
              isLoading={executionsQuery.isPending}
              error={executionsQuery.error instanceof Error ? executionsQuery.error.message : null}
              isEmpty={!executionsQuery.data?.length}
              emptyTitle="暂无成交记录。"
            >
              <div className="space-y-3">
                {executionsQuery.data?.map((execution) => (
                  <div key={execution.id} className="rounded-2xl border border-slate-800 bg-ink-950 p-4 text-sm">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-semibold text-white">{execution.symbol}</p>
                        <p className="mt-1 text-xs text-slate-500">{execution.clientOrderId}</p>
                      </div>
                      <p className="text-xs uppercase tracking-[0.18em] text-cyan-300">{execution.brokerExecutionId}</p>
                    </div>
                    <div className="mt-4 grid grid-cols-4 gap-3 text-slate-300">
                      <Metric label="Side" value={execution.side} compact />
                      <Metric label="Qty" value={formatNumber(execution.filledQuantity)} compact />
                      <Metric label="Price" value={formatCurrency(execution.filledPrice)} compact />
                      <Metric label="Time" value={execution.executedAt} compact />
                    </div>
                  </div>
                ))}
              </div>
            </DataState>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className={`rounded-2xl border border-slate-800 bg-ink-950 ${compact ? "px-3 py-2" : "px-4 py-3"}`}>
      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={`mt-1 font-mono text-white ${compact ? "text-sm" : "text-base"}`}>{value}</p>
    </div>
  );
}

function getOrderStatusTone(status: string) {
  if (status === "FILLED") {
    return "text-emerald-400";
  }

  if (status === "CANCELED" || status === "REJECTED" || status === "FAILED") {
    return "text-rose-400";
  }

  if (status === "CANCEL_REQUESTED" || status === "PENDING_SUBMIT") {
    return "text-amber-300";
  }

  return "text-cyan-300";
}
