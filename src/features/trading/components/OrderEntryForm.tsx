import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { submitOrder } from "@/features/trading/api/getTradingWorkspace";
import { ORDER_SIDE_OPTIONS, ORDER_TYPE_OPTIONS } from "@/shared/lib/enums";
import { formatCurrency } from "@/shared/lib/format";

const orderEntrySchema = z
  .object({
    symbol: z.string().min(1, "请输入交易标的").max(8, "标的代码过长"),
    side: z.enum(["BUY", "SELL"]),
    orderType: z.enum(["MARKET", "LIMIT", "STOP"]),
    quantity: z.coerce.number().int().min(1, "数量必须大于 0"),
    limitPrice: z.preprocess(
      (value) => (value === "" || value === null || value === undefined ? undefined : Number(value)),
      z.number().positive("价格必须大于 0").optional(),
    ),
  })
  .superRefine((value, context) => {
    if (value.orderType === "LIMIT" && !value.limitPrice) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "限价单必须填写价格",
        path: ["limitPrice"],
      });
    }
  });

type OrderEntryValues = z.infer<typeof orderEntrySchema>;
type OrderEntryFormInput = z.input<typeof orderEntrySchema>;

type OrderEntryFormProps = {
  brokerAccountId: string;
  buyingPower: number;
};

export function OrderEntryForm({ brokerAccountId, buyingPower }: OrderEntryFormProps) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
    reset,
  } = useForm<OrderEntryFormInput, unknown, OrderEntryValues>({
    resolver: zodResolver(orderEntrySchema),
    defaultValues: {
      symbol: "TSLA",
      side: "BUY",
      orderType: "LIMIT",
      quantity: 100,
      limitPrice: 245.5,
    },
  });

  const side = watch("side");

  const mutation = useMutation({
    mutationFn: async (values: OrderEntryValues) =>
      submitOrder({
        brokerAccountId,
        symbol: values.symbol.toUpperCase(),
        side: values.side,
        orderType: values.orderType,
        quantity: values.quantity,
        limitPrice: values.orderType === "LIMIT" ? values.limitPrice ?? null : null,
        timeInForce: "day",
        idempotencyKey: `ord-${Date.now()}`,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trading-workspace"] });
      reset({
        symbol: "TSLA",
        side,
        orderType: "LIMIT",
        quantity: 100,
        limitPrice: 245.5,
      });
    },
  });

  return (
    <form className="space-y-5" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
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

      <div className="rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-slate-400">
        Buying Power <span className="ml-2 font-mono text-white">{formatCurrency(buyingPower)}</span>
      </div>

      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {mutation.isPending ? "提交中..." : `${side === "BUY" ? "买入" : "卖出"}订单`}
      </button>

      {mutation.isSuccess ? (
        <p className="text-xs text-emerald-400">订单已进入 {mutation.data.status} 阶段，等待 Broker 确认。</p>
      ) : null}
      {mutation.error ? <p className="text-xs text-rose-400">{mutation.error.message}</p> : null}
    </form>
  );
}
