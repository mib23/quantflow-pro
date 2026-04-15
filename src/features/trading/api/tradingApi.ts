import { isAxiosError } from "axios";

import { httpClient } from "@/shared/api/http";
import { AccountOverview, ApiEnvelope, BrokerQuote, Execution, Order, OrderBookLevel, Position, TradingWorkspace } from "@/shared/types/domain";

export type TradingOrderStatus =
  | "PENDING_SUBMIT"
  | "SUBMITTED"
  | "OPEN"
  | "PARTIALLY_FILLED"
  | "FILLED"
  | "CANCEL_REQUESTED"
  | "CANCELED"
  | "REJECTED"
  | "FAILED";

export type TradingQuote = BrokerQuote;

export type TradingExecution = Execution;

export type TradingOrder = {
  clientOrderId: string;
  symbol: string;
  side: Order["side"];
  quantity: number;
  limitPrice: number | null;
  status: TradingOrderStatus;
  submittedAt: string;
};

type AccountsOverviewResponse = {
  account: {
    id: string;
    broker: string;
    environment: string;
    equity: number;
    cash: number;
    buying_power: number;
    day_pnl: number;
    day_pnl_percent: number;
  };
  positions: Array<{
    symbol: string;
    quantity: number;
    avg_price: number;
    market_price: number;
    unrealized_pnl: number;
  }>;
};

type OrdersResponse = {
  items: Array<{
    client_order_id: string;
    symbol: string;
    side: Order["side"];
    quantity: number;
    limit_price: number | null;
    status: string;
    submitted_at: string;
  }>;
};

type ExecutionsResponse = {
  items: Array<{
    id: string;
    order_id: string;
    client_order_id: string;
    symbol: string;
    side: Order["side"];
    broker_execution_id: string;
    filled_quantity: number;
    filled_price: number;
    fee_amount: number;
    executed_at: string;
  }>;
};

type QuoteResponse = {
  symbol: string;
  bid: number | null;
  ask: number | null;
  last: number | null;
  timestamp: string;
};

type TradingApiErrorInfo = {
  code: string | null;
  message: string | null;
  details: Record<string, unknown>;
};

export type PlaceOrderInput = {
  brokerAccountId: string;
  symbol: string;
  side: Order["side"];
  orderType: "MARKET" | "LIMIT" | "STOP";
  quantity: number;
  limitPrice?: number | null;
  timeInForce: string;
  idempotencyKey: string;
};

export type TradingPreTradeRiskCheckInput = Omit<PlaceOrderInput, "idempotencyKey">;

export type TradingPreTradeRiskCheckResult = {
  allowed: boolean;
  decision: "ALLOW" | "REJECT";
  reasonCode: string | null;
  reason: string | null;
  message: string;
  ruleId: string | null;
  eventId: string | null;
  severity: string | null;
  checkedAt: string;
  symbol: string;
  side: Order["side"];
  orderType: PlaceOrderInput["orderType"];
  quantity: number;
  limitPrice: number | null;
  accountId: string | null;
  raw: Record<string, unknown>;
};

export type TradingRiskEvent = {
  id: string;
  accountId: string;
  ruleId: string | null;
  orderId: string | null;
  clientOrderId: string | null;
  severity: string;
  status: string | null;
  reasonCode: string | null;
  message: string;
  occurredAt: string;
  raw: Record<string, unknown>;
};

type PlaceOrderResponse = {
  client_order_id: string;
  broker_order_id: string | null;
  status: string;
};

type CancelOrderResponse = {
  client_order_id: string;
  status: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function readString(record: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];

    if (typeof value === "string" && value.trim().length > 0) {
      return value;
    }
  }

  return null;
}

function readBoolean(record: Record<string, unknown>, keys: string[]): boolean | null {
  for (const key of keys) {
    const value = record[key];

    if (typeof value === "boolean") {
      return value;
    }
  }

  return null;
}

function readNumber(record: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const value = record[key];

    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
  }

  return null;
}

function normalizeDecision(record: Record<string, unknown>): "ALLOW" | "REJECT" {
  const allowed = readBoolean(record, ["allowed", "approved", "passed", "pass", "ok", "success"]);

  if (allowed === true) {
    return "ALLOW";
  }

  if (allowed === false) {
    return "REJECT";
  }

  const decision = readString(record, ["decision", "status", "result", "state"])?.toLowerCase();

  if (decision && ["allow", "allowed", "approve", "approved", "pass", "passed", "ok", "success"].includes(decision)) {
    return "ALLOW";
  }

  return "REJECT";
}

function buildRiskReasonMessage(input: {
  code?: string | null;
  reason?: string | null;
  message?: string | null;
  details?: Record<string, unknown> | null;
  fallback: string;
}): string {
  const source = [input.code, input.reason, input.message, input.details ? JSON.stringify(input.details) : null]
    .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
    .join(" ")
    .toLowerCase();

  if (source.includes("daily_loss") || source.includes("day_loss")) {
    return "今日亏损已触发风控限制";
  }

  if (source.includes("single_order") || source.includes("order_value") || source.includes("notional")) {
    return "单笔订单金额超过风控上限";
  }

  if (source.includes("position_size") || source.includes("exposure")) {
    return "仓位规模超过风控限制";
  }

  if (source.includes("restricted_symbol") || source.includes("restricted_symbols") || source.includes("symbol_blacklist")) {
    return "该标的已被风控限制";
  }

  if (source.includes("market_hours") || source.includes("trading_hours")) {
    return "当前不在允许交易时段";
  }

  if (source.includes("buying_power") || source.includes("insufficient_funds")) {
    return "可用购买力不足，订单被拒绝";
  }

  if (input.reason) {
    return input.reason;
  }

  if (input.message) {
    return input.message;
  }

  return input.fallback;
}

function normalizeApiErrorInfo(error: unknown): TradingApiErrorInfo | null {
  if (!isAxiosError(error)) {
    return null;
  }

  const record = asRecord(error.response?.data);

  if (!record) {
    return {
      code: null,
      message: error.message,
      details: {},
    };
  }

  const envelopeError = asRecord(record.error);
  const payload = asRecord(record.data) ?? record;
  const details = asRecord(payload.details) ?? asRecord(envelopeError?.details) ?? {};

  return {
    code: readString(envelopeError ?? payload, ["code", "error_code", "reason_code", "reasonCode"]),
    message: readString(envelopeError ?? payload, ["message", "detail", "reason"]) ?? error.message,
    details,
  };
}

function normalizePreTradeRiskCheckResponse(
  input: unknown,
  fallbackInput: TradingPreTradeRiskCheckInput,
): TradingPreTradeRiskCheckResult {
  const record = asRecord(input) ?? {};
  const details = asRecord(record.details) ?? {};
  const allowed = normalizeDecision(record) === "ALLOW";
  const reasonCode = readString(record, ["reason_code", "reasonCode", "code"]);
  const reason = readString(record, ["reason", "rejection_reason", "rejectionReason"]);
  const message = buildRiskReasonMessage({
    code: reasonCode,
    reason,
    message: readString(record, ["message", "detail"]),
    details,
    fallback: allowed ? "风控预检通过" : "风控预检未通过",
  });

  return {
    allowed,
    decision: allowed ? "ALLOW" : "REJECT",
    reasonCode,
    reason,
    message,
    ruleId: readString(record, ["rule_id", "ruleId"]),
    eventId: readString(record, ["event_id", "eventId"]),
    severity: readString(record, ["severity"]),
    checkedAt: readString(record, ["checked_at", "checkedAt", "timestamp"]) ?? new Date().toISOString(),
    symbol: readString(record, ["symbol"]) ?? fallbackInput.symbol.toUpperCase(),
    side: (readString(record, ["side"])?.toUpperCase() as Order["side"] | undefined) ?? fallbackInput.side,
    orderType:
      (readString(record, ["order_type", "orderType"])?.toUpperCase() as PlaceOrderInput["orderType"] | undefined) ??
      fallbackInput.orderType,
    quantity: readNumber(record, ["quantity"]) ?? fallbackInput.quantity,
    limitPrice: readNumber(record, ["limit_price", "limitPrice"]) ?? (fallbackInput.limitPrice != null ? fallbackInput.limitPrice : null),
    accountId: readString(record, ["account_id", "accountId"]) ?? fallbackInput.brokerAccountId,
    raw: record,
  };
}

export function normalizeRiskEvent(recordInput: unknown, fallbackAccountId?: string | null): TradingRiskEvent | null {
  const record = asRecord(recordInput);

  if (!record) {
    return null;
  }

  const accountId = readString(record, ["account_id", "accountId"]) ?? fallbackAccountId ?? "";

  if (!accountId) {
    return null;
  }

  const reasonCode = readString(record, ["reason_code", "reasonCode", "code"]);
  const severity = readString(record, ["severity"]) ?? "INFO";
  const message = buildRiskReasonMessage({
    code: reasonCode,
    reason: readString(record, ["reason", "rejection_reason", "rejectionReason"]),
    message: readString(record, ["message", "detail"]),
    details: asRecord(record.details),
    fallback: "已收到风险事件",
  });

  return {
    id: readString(record, ["id", "event_id", "eventId"]) ?? `risk_${Date.now()}`,
    accountId,
    ruleId: readString(record, ["rule_id", "ruleId"]),
    orderId: readString(record, ["order_id", "orderId"]),
    clientOrderId: readString(record, ["client_order_id", "clientOrderId"]),
    severity,
    status: readString(record, ["status"]),
    reasonCode,
    message,
    occurredAt: readString(record, ["occurred_at", "occurredAt", "timestamp"]) ?? new Date().toISOString(),
    raw: record,
  };
}

function createTradingApiError(
  message: string,
  code?: string | null,
  details?: Record<string, unknown>,
): Error & { code?: string | null; details?: Record<string, unknown> } {
  const error = new Error(message) as Error & { code?: string | null; details?: Record<string, unknown> };
  error.code = code ?? null;
  error.details = details ?? {};
  return error;
}

function mapAccount(input: AccountsOverviewResponse["account"]): AccountOverview {
  return {
    id: input.id,
    broker: input.broker,
    environment: input.environment,
    equity: input.equity,
    cash: input.cash,
    buyingPower: input.buying_power,
    dayPnl: input.day_pnl,
    dayPnlPercent: input.day_pnl_percent,
  };
}

function mapPositions(input: AccountsOverviewResponse["positions"]): Position[] {
  return input.map((position) => ({
    symbol: position.symbol,
    quantity: position.quantity,
    avgPrice: position.avg_price,
    marketPrice: position.market_price,
    unrealizedPnl: position.unrealized_pnl,
  }));
}

export function normalizeTradingOrderStatus(status: string): TradingOrderStatus {
  const normalized = status.toUpperCase();

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
    return normalized;
  }

  return "FAILED";
}

function mapOrders(input: OrdersResponse["items"]): TradingOrder[] {
  return input.map((order) => ({
    clientOrderId: order.client_order_id,
    symbol: order.symbol,
    side: order.side,
    quantity: order.quantity,
    limitPrice: order.limit_price,
    status: normalizeTradingOrderStatus(order.status),
    submittedAt: order.submitted_at,
  }));
}

function mapExecutions(input: ExecutionsResponse["items"]): TradingExecution[] {
  return input.map((execution) => ({
    id: execution.id,
    orderId: execution.order_id,
    clientOrderId: execution.client_order_id,
    brokerExecutionId: execution.broker_execution_id,
    symbol: execution.symbol,
    side: execution.side,
    filledQuantity: execution.filled_quantity,
    filledPrice: execution.filled_price,
    feeAmount: execution.fee_amount,
    executedAt: execution.executed_at,
  }));
}

function mapQuote(input: QuoteResponse): TradingQuote {
  return {
    symbol: input.symbol.toUpperCase(),
    bid: input.bid,
    ask: input.ask,
    last: input.last,
    timestamp: input.timestamp,
  };
}

export function buildSyntheticDepth(quote: TradingQuote): { bidLevels: OrderBookLevel[]; askLevels: OrderBookLevel[] } {
  const referencePrice = quote.last ?? quote.bid ?? quote.ask ?? 0;

  if (!referencePrice) {
    return { bidLevels: [], askLevels: [] };
  }

  const offsets = [0.04, 0.02, 0.01, 0];

  return {
    bidLevels: offsets.map((offset, index) => ({
      price: Number((referencePrice - offset).toFixed(2)),
      size: 100 + index * 75,
      total: 200 + index * 250,
    })),
    askLevels: offsets
      .slice()
      .reverse()
      .map((offset, index) => ({
        price: Number((referencePrice + offset).toFixed(2)),
        size: 110 + index * 65,
        total: 200 + index * 250,
      })),
  };
}

export async function getTradingAccountSnapshot(): Promise<{ account: AccountOverview; positions: Position[] }> {
  const response = await httpClient.get<ApiEnvelope<AccountsOverviewResponse>>("/accounts/overview");

  return {
    account: mapAccount(response.data.data.account),
    positions: mapPositions(response.data.data.positions),
  };
}

export async function getTradingOrders(): Promise<Order[]> {
  const response = await httpClient.get<ApiEnvelope<OrdersResponse>>("/orders");

  return mapOrders(response.data.data.items);
}

export async function getTradingExecutions(): Promise<TradingExecution[]> {
  try {
    const response = await httpClient.get<ApiEnvelope<ExecutionsResponse>>("/orders/executions");
    return mapExecutions(response.data.data.items);
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      return [];
    }

    throw error;
  }
}

export async function getTradingQuote(symbol: string): Promise<TradingQuote> {
  const normalizedSymbol = symbol.trim().toUpperCase();
  const response = await httpClient.get<ApiEnvelope<QuoteResponse>>(`/market-data/quote/${encodeURIComponent(normalizedSymbol)}`);

  return mapQuote(response.data.data);
}

export async function checkTradingPreTradeRisk(
  input: TradingPreTradeRiskCheckInput,
): Promise<TradingPreTradeRiskCheckResult> {
  const payload = {
    broker_account_id: input.brokerAccountId,
    symbol: input.symbol,
    side: input.side,
    order_type: input.orderType,
    quantity: input.quantity,
    limit_price: input.limitPrice,
    time_in_force: input.timeInForce,
  };

  try {
    const response = await httpClient.post<ApiEnvelope<unknown>>("/risk/checks/pre-trade", payload);
    return normalizePreTradeRiskCheckResponse(response.data.data, input);
  } catch (error) {
    const apiError = normalizeApiErrorInfo(error);

    if (apiError && apiError.code && ["PRE_TRADE_RISK_REJECTED", "ORDER_RISK_REJECTED", "RISK_REJECTED"].includes(apiError.code)) {
      return {
        allowed: false,
        decision: "REJECT",
        reasonCode: apiError.code,
        reason: readString(apiError.details, ["reason", "rejection_reason", "rejectionReason"]),
        message: buildRiskReasonMessage({
          code: apiError.code,
          reason: readString(apiError.details, ["reason", "rejection_reason", "rejectionReason"]),
          message: apiError.message,
          details: apiError.details,
          fallback: "风控预检未通过",
        }),
        ruleId: readString(apiError.details, ["rule_id", "ruleId"]),
        eventId: readString(apiError.details, ["event_id", "eventId"]),
        severity: readString(apiError.details, ["severity"]),
        checkedAt: new Date().toISOString(),
        symbol: input.symbol.toUpperCase(),
        side: input.side,
        orderType: input.orderType,
        quantity: input.quantity,
        limitPrice: input.limitPrice != null ? input.limitPrice : null,
        accountId: input.brokerAccountId,
        raw: apiError.details,
      };
    }

    throw error;
  }
}

export async function placeTradingOrder(input: PlaceOrderInput): Promise<{ clientOrderId: string; status: TradingOrderStatus }> {
  try {
    const response = await httpClient.post<ApiEnvelope<PlaceOrderResponse>>("/orders", {
      broker_account_id: input.brokerAccountId,
      symbol: input.symbol,
      side: input.side,
      order_type: input.orderType,
      quantity: input.quantity,
      limit_price: input.limitPrice,
      time_in_force: input.timeInForce,
      idempotency_key: input.idempotencyKey,
    });

    return {
      clientOrderId: response.data.data.client_order_id,
      status: normalizeTradingOrderStatus(response.data.data.status),
    };
  } catch (error) {
    const apiError = normalizeApiErrorInfo(error);

    if (apiError && apiError.code === "ORDER_RISK_REJECTED") {
      throw createTradingApiError(
        buildRiskReasonMessage({
          code: apiError.code,
          reason: readString(apiError.details, ["reason", "rejection_reason", "rejectionReason"]),
          message: apiError.message,
          details: apiError.details,
          fallback: "订单被风控拒绝",
        }),
        apiError.code,
        apiError.details,
      );
    }

    if (apiError) {
      throw createTradingApiError(apiError.message ?? "订单提交失败", apiError.code, apiError.details);
    }

    throw error;
  }
}

export async function cancelTradingOrder(clientOrderId: string): Promise<{ clientOrderId: string; status: TradingOrderStatus }> {
  const response = await httpClient.post<ApiEnvelope<CancelOrderResponse>>(`/orders/${encodeURIComponent(clientOrderId)}/cancel`);

  return {
    clientOrderId: response.data.data.client_order_id,
    status: normalizeTradingOrderStatus(response.data.data.status),
  };
}

export async function getTradingWorkspace(symbol = "TSLA"): Promise<TradingWorkspace> {
  const [accountSnapshot, orders, quote] = await Promise.all([
    getTradingAccountSnapshot(),
    getTradingOrders(),
    getTradingQuote(symbol),
  ]);

  const { bidLevels, askLevels } = buildSyntheticDepth(quote);

  return {
    account: accountSnapshot.account,
    activeSymbol: quote.symbol,
    bidLevels,
    askLevels,
    orders,
  };
}
