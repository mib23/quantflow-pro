import { OrderEntryForm } from "@/features/trading/components/OrderEntryForm";
import { useTradingWorkspace } from "@/features/trading/hooks/useTradingWorkspace";
import { formatCurrency, formatNumber } from "@/shared/lib/format";
import { DataState } from "@/shared/ui/DataState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionCard } from "@/shared/ui/SectionCard";

export function TradePage() {
  const { data, isPending, error } = useTradingWorkspace();
  const spread = data ? data.askLevels.at(-1)!.price - data.bidLevels[0].price : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Trade"
        title="下单与订单状态工作台"
        description="下单表单已接入统一校验、查询失效和 mock/API 切换逻辑，Phase 1 只需要替换服务实现。"
      />

      <DataState isLoading={isPending} error={error instanceof Error ? error.message : null} isEmpty={!data}>
        {data ? (
          <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr_0.9fr]">
            <SectionCard title="Order Entry" subtitle="支持本地下单校验和幂等键预留。">
              <OrderEntryForm brokerAccountId={data.account.id} buyingPower={data.account.buyingPower} />
            </SectionCard>

            <SectionCard title={`Level 2 · ${data.activeSymbol}`} subtitle="盘口深度仍使用 mock，可随行情流替换。">
              <div className="space-y-3 font-mono text-sm">
                <div className="rounded-2xl border border-slate-800 bg-ink-950 p-3">
                  <p className="mb-2 text-xs uppercase tracking-[0.18em] text-slate-500">Asks</p>
                  <DepthTable levels={[...data.askLevels].reverse()} tone="text-rose-400" fillClass="bg-rose-500/10" />
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-center text-xs uppercase tracking-[0.22em] text-slate-400">
                  Spread {spread.toFixed(2)}
                </div>
                <div className="rounded-2xl border border-slate-800 bg-ink-950 p-3">
                  <p className="mb-2 text-xs uppercase tracking-[0.18em] text-slate-500">Bids</p>
                  <DepthTable levels={data.bidLevels} tone="text-emerald-400" fillClass="bg-emerald-500/10" />
                </div>
              </div>
            </SectionCard>

            <SectionCard
              title="Active Orders"
              subtitle="订单列表查询已经独立，后续可直接接成交回报与取消操作。"
              action={
                <button className="rounded-full border border-rose-900/50 bg-rose-950/30 px-3 py-1 text-xs text-rose-300">
                  Cancel All
                </button>
              }
            >
              <div className="space-y-3">
                {data.orders.map((order) => (
                  <div key={order.clientOrderId} className="rounded-2xl border border-slate-800 bg-ink-950 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-white">{order.symbol}</p>
                        <p className="mt-1 text-xs text-slate-500">{order.clientOrderId}</p>
                      </div>
                      <p className="text-xs uppercase tracking-[0.18em] text-cyan-300">{order.status}</p>
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

function DepthTable({
  levels,
  tone,
  fillClass,
}: {
  levels: Array<{ price: number; size: number; total: number }>;
  tone: string;
  fillClass: string;
}) {
  return (
    <div className="space-y-2">
      {levels.map((level) => (
        <div key={`${level.price}-${level.total}`} className="relative overflow-hidden rounded-xl border border-slate-900 px-3 py-2">
          <div className={`absolute inset-y-0 right-0 ${fillClass}`} style={{ width: `${(level.total / 2000) * 100}%` }} />
          <div className="relative z-10 grid grid-cols-3 gap-2">
            <span className={tone}>{level.price.toFixed(2)}</span>
            <span className="text-right text-slate-300">{level.size}</span>
            <span className="text-right text-slate-500">{level.total}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
