import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";

import {
  usePlaceTradingOrderMutation,
  useTradingPreTradeRiskCheckMutation,
  useTradingPreTradeRiskCheckResultQuery,
} from "@/features/trading/hooks/useTradingQueries";
import { tradingQueryKeys } from "@/features/trading/hooks/tradingQueryKeys";
import { ORDER_SIDE_OPTIONS, ORDER_TYPE_OPTIONS } from "@/shared/lib/enums";
import { formatCurrency } from "@/shared/lib/format";

function createOrderEntrySchema(buyingPower: number, referencePrice: number | null) {
  return z
    .object({
      symbol: z.string().trim().min(1, "请输入交易标的").max(8, "标的代码过长"),
      side: z.enum(["BUY", "SELL"]),
      orderType: z.enum(["MARKET", "LIMIT", "STOP"]),
      quantity: z.coerce.number().int().min(1, "数量必须大于 0"),
      limitPrice: z.preprocess(
        (value) => (value === "" || value === null || value === undefined ? undefined : Number(value)),
        z.number().positive("价格必须大于 0").optional(),
      ),
    })
    .superRefine((value, context) => {
      const estimatedPrice = value.orderType === "MARKET" ? referencePrice : value.limitPrice ?? null;

      if (value.orderType === "LIMIT" && !value.limitPrice) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "限价单必须填写价格",
          path: ["limitPrice"],
        });
      }

      if (estimatedPrice && estimatedPrice * value.quantity > buyingPower) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "订单名义价值超过可用购买力",
          path: ["quantity"],
        });
      }
    });
}

type OrderEntryValues = z.infer<ReturnType<typeof createOrderEntrySchema>>;
type OrderEntryFormInput = z.input<ReturnType<typeof createOrderEntrySchema>>;

type OrderEntryFormProps = {
  brokerAccountId: string | null;
  buyingPower: number;
  referencePrice: number | null;
  disabled?: boolean;
  onSymbolChange?: (symbol: string) => void;
};

export function OrderEntryForm({
  brokerAccountId,
  buyingPower,
  referencePrice,
  disabled = false,
  onSymbolChange,
}: OrderEntryFormProps) {
  const schema = createOrderEntrySchema(buyingPower, referencePrice);
  const queryClient = useQueryClient();
  const preTradeRiskCheckMutation = useTradingPreTradeRiskCheckMutation();
  const placeOrderMutation = usePlaceTradingOrderMutation();
  const preTradeRiskCheckQuery = useTradingPreTradeRiskCheckResultQuery();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<OrderEntryFormInput, unknown, OrderEntryValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      symbol: "TSLA",
      side: "BUY",
      orderType: "LIMIT",
      quantity: 100,
      limitPrice: 245.5,
    },
  });

  const symbol = watch("symbol");
  const side = watch("side");
  const orderType = watch("orderType");
  const quantity = watch("quantity");
  const limitPrice = watch("limitPrice");
  const quantityValue = toNumber(quantity);
  const limitPriceValue = toNumber(limitPrice);

  useEffect(() => {
    onSymbolChange?.((symbol || "TSLA").toString().trim().toUpperCase());
  }, [onSymbolChange, symbol]);

  const estimatedPrice = orderType === "MARKET" ? referencePrice : limitPriceValue;
  const estimatedNotional = estimatedPrice ? estimatedPrice * quantityValue : null;
  const latestRiskCheck = preTradeRiskCheckQuery.data;
  const isDisabled = disabled || !brokerAccountId || placeOrderMutation.isPending || preTradeRiskCheckMutation.isPending;

  return (
    <form
      className="space-y-5"
      onSubmit={handleSubmit(async (values) => {
        if (!brokerAccountId) {
          return;
        }

        const orderDraft = {
          brokerAccountId,
          symbol: values.symbol.toUpperCase(),
          side: values.side,
          orderType: values.orderType,
          quantity: values.quantity,
          limitPrice: values.orderType === "LIMIT" ? values.limitPrice ?? null : null,
          timeInForce: "day",
          idempotencyKey: `ord-${Date.now()}-${values.symbol.toLowerCase()}`,
        };

        preTradeRiskCheckMutation.reset();
        placeOrderMutation.reset();
        queryClient.setQueryData(tradingQueryKeys.riskPreTradeLatest(), null);

        try {
          const preTradeRiskCheck = await preTradeRiskCheckMutation.mutateAsync(orderDraft);

          if (!preTradeRiskCheck.allowed) {
            return;
          }

          await placeOrderMutation.mutateAsync(orderDraft);
        } catch {
          return;
        }
      })}
    >
      <div>
        <label className="mb-1 block text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Symbol</label>
        <input
          {...register("symbol")}
          className="w-full rounded-2xl border border-slate-700 bg-ink-950 px-4 py-3 font-mono uppercase text-white outline-none transition focus:border-cyan-400"
        />
        {errors.symbol ? <p className="mt-2 text-xs text-rose-400">{errors.symbol.message}</p> : null}
      </div>

      <div className="grid grid-cols-2 gap-2 rounded-2xl border border-slate-800 bg-ink-950 p-1">
        {ORDER_SIDE_OPTIONS.map((option) => (
          <label key={option.value} className="cursor-pointer">
            <input {...register("side")} type="radio" value={option.value} className="peer sr-only" />
            <span className="block rounded-xl px-4 py-3 text-center text-sm font-semibold text-slate-400 transition peer-checked:bg-cyan-400 peer-checked:text-slate-950">
              {option.label}
            </span>
          </label>
        ))}
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Order Type</label>
        <select
          {...register("orderType")}
          className="w-full rounded-2xl border border-slate-700 bg-ink-950 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
        >
          {ORDER_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Quantity</label>
          <input
            {...register("quantity")}
            type="number"
            className="w-full rounded-2xl border border-slate-700 bg-ink-950 px-4 py-3 font-mono text-white outline-none transition focus:border-cyan-400"
          />
          {errors.quantity ? <p className="mt-2 text-xs text-rose-400">{errors.quantity.message}</p> : null}
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Limit Price</label>
          <input
            {...register("limitPrice")}
            type="number"
            step="0.01"
            className="w-full rounded-2xl border border-slate-700 bg-ink-950 px-4 py-3 font-mono text-white outline-none transition focus:border-cyan-400"
          />
          {errors.limitPrice ? <p className="mt-2 text-xs text-rose-400">{errors.limitPrice.message}</p> : null}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-slate-400">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Buying Power</p>
          <p className="mt-1 font-mono text-white">{formatCurrency(buyingPower)}</p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Est. Notional</p>
          <p className="mt-1 font-mono text-white">{estimatedNotional ? formatCurrency(estimatedNotional) : "N/A"}</p>
        </div>
      </div>

      <button
        type="submit"
        disabled={isDisabled}
        className="w-full rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {placeOrderMutation.isPending || preTradeRiskCheckMutation.isPending ? "处理中..." : `${side === "BUY" ? "买入" : "卖出"}订单`}
      </button>

      {latestRiskCheck ? (
        <div
          className={`rounded-2xl border px-4 py-3 text-sm ${
            latestRiskCheck.allowed ? "border-emerald-900/40 bg-emerald-950/30 text-emerald-200" : "border-rose-900/40 bg-rose-950/30 text-rose-200"
          }`}
        >
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">{latestRiskCheck.allowed ? "Pre-trade risk passed" : "Pre-trade risk rejected"}</p>
          <p className="mt-2 font-medium">{latestRiskCheck.message}</p>
          <p className="mt-2 text-xs text-slate-400">
            {latestRiskCheck.ruleId ? `Rule ${latestRiskCheck.ruleId} · ` : ""}
            {latestRiskCheck.reasonCode ? `Code ${latestRiskCheck.reasonCode}` : `Checked ${latestRiskCheck.checkedAt}`}
          </p>
        </div>
      ) : null}

      {placeOrderMutation.isSuccess ? (
        <p className="text-xs text-emerald-400">
          订单 {placeOrderMutation.data.clientOrderId} 已进入 {placeOrderMutation.data.status} 阶段。
        </p>
      ) : null}
      {preTradeRiskCheckMutation.error ? <p className="text-xs text-rose-400">{preTradeRiskCheckMutation.error.message}</p> : null}
      {placeOrderMutation.error ? <p className="text-xs text-rose-400">{placeOrderMutation.error.message}</p> : null}
      {!brokerAccountId ? <p className="text-xs text-amber-300">账户未加载完成，暂不能提交订单。</p> : null}
      {referencePrice ? (
        <p className="text-xs text-slate-500">
          参考价 {formatCurrency(referencePrice)} · {symbol ? symbol.toUpperCase() : "N/A"}
        </p>
      ) : null}
    </form>
  );
}

function toNumber(value: unknown) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }

  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  return 0;
}
