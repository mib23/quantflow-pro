import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  cancelTradingOrder,
  getTradingAccountSnapshot,
  getTradingExecutions,
  getTradingOrders,
  getTradingQuote,
  placeTradingOrder,
  TradingExecution,
  TradingOrder,
  TradingQuote,
} from "@/features/trading/api/tradingApi";
import { tradingQueryKeys } from "@/features/trading/hooks/tradingQueryKeys";

export function useTradingAccountQuery() {
  return useQuery({
    queryKey: tradingQueryKeys.account(),
    queryFn: getTradingAccountSnapshot,
  });
}

export function useTradingOrdersQuery() {
  return useQuery({
    queryKey: tradingQueryKeys.orders(),
    queryFn: getTradingOrders,
  });
}

export function useTradingExecutionsQuery() {
  return useQuery({
    queryKey: tradingQueryKeys.executions(),
    queryFn: getTradingExecutions,
  });
}

export function useTradingQuoteQuery(symbol: string) {
  const normalizedSymbol = symbol.trim().toUpperCase();

  return useQuery({
    queryKey: tradingQueryKeys.quote(normalizedSymbol),
    queryFn: () => getTradingQuote(normalizedSymbol),
    enabled: normalizedSymbol.length > 0,
    placeholderData: (previous) => previous,
    refetchInterval: 15_000,
  });
}

export function usePlaceTradingOrderMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: placeTradingOrder,
    onSuccess: (result, variables) => {
      const nextOrder: TradingOrder = {
        clientOrderId: result.clientOrderId,
        symbol: variables.symbol.toUpperCase(),
        side: variables.side,
        quantity: variables.quantity,
        limitPrice: variables.limitPrice ?? null,
        status: result.status,
        submittedAt: new Date().toISOString(),
      };

      queryClient.setQueryData<TradingOrder[]>(tradingQueryKeys.orders(), (current = []) => {
        const filtered = current.filter((order) => order.clientOrderId !== nextOrder.clientOrderId);
        return [nextOrder, ...filtered];
      });

      queryClient.invalidateQueries({ queryKey: tradingQueryKeys.account() });
      queryClient.invalidateQueries({ queryKey: tradingQueryKeys.orders() });
      queryClient.invalidateQueries({ queryKey: tradingQueryKeys.executions() });
    },
  });
}

export function useCancelTradingOrderMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cancelTradingOrder,
    onSuccess: (result) => {
      queryClient.setQueryData<TradingOrder[]>(tradingQueryKeys.orders(), (current = []) =>
        current.map((order) =>
          order.clientOrderId === result.clientOrderId
            ? {
                ...order,
                status: result.status,
              }
            : order,
        ),
      );

      queryClient.invalidateQueries({ queryKey: tradingQueryKeys.executions() });
    },
  });
}

type TradingStreamMessage =
  | {
      type?: string;
      kind?: string;
      event?: string;
      channel?: string;
      symbol?: string;
      data?: unknown;
      payload?: unknown;
    }
  | Record<string, unknown>;

function parseTradingStreamMessage(rawData: unknown): TradingStreamMessage | null {
  if (typeof rawData === "string") {
    try {
      return JSON.parse(rawData) as TradingStreamMessage;
    } catch {
      return null;
    }
  }

  if (typeof rawData === "object" && rawData !== null) {
    return rawData as TradingStreamMessage;
  }

  return null;
}

function extractStatus(rawValue: unknown): TradingOrder["status"] | null {
  if (typeof rawValue !== "string") {
    return null;
  }

  const normalized = rawValue.toUpperCase();

  if (normalized === "CANCELLED") {
    return "CANCELED";
  }

  if (
    normalized === "PENDING_SUBMIT" ||
    normalized === "SUBMITTED" ||
    normalized === "OPEN" ||
    normalized === "PARTIALLY_FILLED" ||
    normalized === "FILLED" ||
    normalized === "CANCEL_REQUESTED" ||
    normalized === "CANCELED" ||
    normalized === "REJECTED" ||
    normalized === "FAILED"
  ) {
    return normalized as TradingOrder["status"];
  }

  return null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

export function applyTradingStreamMessage(queryClient: ReturnType<typeof useQueryClient>, rawMessage: unknown): void {
  const message = parseTradingStreamMessage(rawMessage);

  if (!message) {
    return;
  }

  const record = asRecord(message.data) ?? asRecord(message.payload) ?? message;
  const messageType = String(message.type ?? message.kind ?? message.event ?? message.channel ?? "").toLowerCase();

  if (messageType.includes("quote") || ("bid" in record && "ask" in record)) {
    const symbol = String((record.symbol ?? message.symbol) || "").trim().toUpperCase();

    if (!symbol) {
      return;
    }

    queryClient.setQueryData<TradingQuote | undefined>(tradingQueryKeys.quote(symbol), (current) => ({
      symbol,
      bid: typeof record.bid === "number" ? record.bid : current?.bid ?? null,
      ask: typeof record.ask === "number" ? record.ask : current?.ask ?? null,
      last: typeof record.last === "number" ? record.last : current?.last ?? null,
      timestamp: typeof record.timestamp === "string" ? record.timestamp : new Date().toISOString(),
    }));

    return;
  }

  const clientOrderId = String(record.client_order_id ?? record.clientOrderId ?? record.order_id ?? record.orderId ?? "");

  if (clientOrderId) {
    const nextStatus = extractStatus(record.status);

    if (nextStatus) {
      queryClient.setQueryData<TradingOrder[]>(tradingQueryKeys.orders(), (current = []) =>
        current.map((order) =>
          order.clientOrderId === clientOrderId
            ? {
                ...order,
                status: nextStatus,
              }
            : order,
        ),
      );
    }
  }

  const executionId = String(record.execution_id ?? record.executionId ?? "");

  if (executionId) {
    const nextExecution: TradingExecution = {
      id: executionId,
      orderId: String(record.order_id ?? record.orderId ?? ""),
      clientOrderId,
      brokerExecutionId: String(record.broker_execution_id ?? record.brokerExecutionId ?? executionId),
      symbol: String(record.symbol ?? "").toUpperCase(),
      side: String(record.side ?? "BUY").toUpperCase() as TradingOrder["side"],
      filledQuantity:
        typeof record.filled_quantity === "number"
          ? record.filled_quantity
          : typeof record.quantity === "number"
            ? record.quantity
            : 0,
      filledPrice:
        typeof record.filled_price === "number"
          ? record.filled_price
          : typeof record.price === "number"
            ? record.price
            : 0,
      feeAmount: typeof record.fee_amount === "number" ? record.fee_amount : 0,
      executedAt: typeof record.executed_at === "string" ? record.executed_at : new Date().toISOString(),
    };

    queryClient.setQueryData<TradingExecution[]>(tradingQueryKeys.executions(), (current = []) => {
      const filtered = current.filter((execution) => execution.id !== nextExecution.id);
      return [nextExecution, ...filtered];
    });
    queryClient.invalidateQueries({ queryKey: tradingQueryKeys.orders() });
  }
}
