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

type PlaceOrderResponse = {
  client_order_id: string;
  broker_order_id: string | null;
  status: string;
};

type CancelOrderResponse = {
  client_order_id: string;
  status: string;
};

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

export async function placeTradingOrder(input: PlaceOrderInput): Promise<{ clientOrderId: string; status: TradingOrderStatus }> {
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
