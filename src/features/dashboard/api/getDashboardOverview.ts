import { httpClient } from "@/shared/api/http";
import { env } from "@/shared/config/env";
import { mockDashboardOverview } from "@/shared/mocks/data";
import { AccountOverview, ApiEnvelope, DashboardOverview, Position } from "@/shared/types/domain";

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

function mapAccountOverview(input: AccountsOverviewResponse["account"]): AccountOverview {
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

export async function getDashboardOverview(): Promise<DashboardOverview> {
  if (env.dataSource === "mock") {
    return mockDashboardOverview;
  }

  const response = await httpClient.get<ApiEnvelope<AccountsOverviewResponse>>("/accounts/overview");

  return {
    account: mapAccountOverview(response.data.data.account),
    positions: mapPositions(response.data.data.positions),
    strategies: mockDashboardOverview.strategies,
    logs: mockDashboardOverview.logs,
    equityCurve: mockDashboardOverview.equityCurve,
  };
}
