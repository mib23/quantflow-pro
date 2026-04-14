import { httpClient } from "@/shared/api/http";
import { env } from "@/shared/config/env";
import { mockTradingWorkspace } from "@/shared/mocks/data";
import { AccountOverview, ApiEnvelope, Order, TradingWorkspace } from "@/shared/types/domain";

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
};

type OrdersResponse = {
  items: Array<{
    client_order_id: string;
    symbol: string;
    side: Order["side"];
    quantity: number;
    limit_price: number | null;
    status: Order["status"];
    submitted_at: string;
  }>;
};

type PlaceOrderInput = {
  brokerAccountId: string;
  symbol: string;
  side: Order["side"];
  orderType: "MARKET" | "LIMIT" | "STOP";
  quantity: number;
  limitPrice?: number | null;
  timeInForce: string;
  idempotencyKey: string;
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

function mapOrders(input: OrdersResponse["items"]): Order[] {
  return input.map((order) => ({
    clientOrderId: order.client_order_id,
    symbol: order.symbol,
    side: order.side,
    quantity: order.quantity,
    limitPrice: order.limit_price,
    status: order.status,
    submittedAt: order.submitted_at,
  }));
}

export async function getTradingWorkspace(): Promise<TradingWorkspace> {
  if (env.dataSource === "mock") {
    return mockTradingWorkspace;
  }

  const [accountResponse, ordersResponse] = await Promise.all([
    httpClient.get<ApiEnvelope<AccountsOverviewResponse>>("/accounts/overview"),
    httpClient.get<ApiEnvelope<OrdersResponse>>("/orders"),
  ]);

  return {
    account: mapAccount(accountResponse.data.data.account),
    activeSymbol: mockTradingWorkspace.activeSymbol,
    bidLevels: mockTradingWorkspace.bidLevels,
    askLevels: mockTradingWorkspace.askLevels,
    orders: mapOrders(ordersResponse.data.data.items),
  };
}

export async function submitOrder(input: PlaceOrderInput) {
  if (env.dataSource === "mock") {
    return {
      clientOrderId: `ord_${input.symbol.toLowerCase()}_${input.idempotencyKey.slice(-4)}`,
      status: "PENDING_SUBMIT",
    };
  }

  const response = await httpClient.post<
    ApiEnvelope<{
      client_order_id: string;
      status: string;
    }>
  >("/orders", {
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
    status: response.data.data.status,
  };
}
