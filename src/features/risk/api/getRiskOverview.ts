import { httpClient } from "@/shared/api/http";
import { env } from "@/shared/config/env";
import { mockRiskSummary } from "@/shared/mocks/data";
import { ApiEnvelope, RiskSummary } from "@/shared/types/domain";

type RiskResponse = {
  hard_limits: {
    max_daily_loss: number;
    max_single_order_value: number;
    max_position_size_percent: number;
  };
  restrictions: {
    restricted_symbols: string[];
    market_hours_only: boolean;
  };
  recent_events: Array<{
    id: string;
    severity: string;
    message: string;
    occurred_at: string;
  }>;
};

export async function getRiskOverview(): Promise<RiskSummary> {
  if (env.dataSource === "mock") {
    return mockRiskSummary;
  }

  const response = await httpClient.get<ApiEnvelope<RiskResponse>>("/risk/summary");
  return {
    hardLimits: {
      maxDailyLoss: response.data.data.hard_limits.max_daily_loss,
      maxSingleOrderValue: response.data.data.hard_limits.max_single_order_value,
      maxPositionSizePercent: response.data.data.hard_limits.max_position_size_percent,
    },
    restrictions: {
      restrictedSymbols: response.data.data.restrictions.restricted_symbols,
      marketHoursOnly: response.data.data.restrictions.market_hours_only,
    },
    recentEvents: response.data.data.recent_events.map((event) => ({
      id: event.id,
      severity: event.severity,
      message: event.message,
      occurredAt: event.occurred_at,
    })),
  };
}
