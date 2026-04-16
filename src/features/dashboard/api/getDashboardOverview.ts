import { httpClient } from "@/shared/api/http";
import { ApiEnvelope } from "@/shared/types/domain";

import { normalizeRiskEvent, RiskEvent } from "@/entities/risk-rule/model";

export interface DashboardAccount {
  id: string;
  broker: string;
  environment: string;
  equity: number;
  cash: number;
  buyingPower: number;
  dayPnl: number;
  dayPnlPercent: number;
}

export interface DashboardPosition {
  symbol: string;
  quantity: number;
  avgPrice: number;
  marketPrice: number;
  marketValue: number;
  unrealizedPnl: number;
  realizedPnl: number | null;
  weight: number | null;
}

export interface DashboardPositionStats {
  totalPositions: number;
  longPositions: number;
  shortPositions: number;
  flatPositions: number;
  grossExposure: number;
  netExposure: number;
  unrealizedPnl: number;
}

export interface DashboardPnlSummary {
  day: number;
  dayPercent: number;
  unrealized: number;
  realized: number | null;
  total: number;
}

export interface DashboardHealthSummary {
  status: "healthy" | "warning" | "critical" | "unknown";
  label: string;
  message: string;
}

export interface DashboardOverview {
  account: DashboardAccount;
  positions: DashboardPosition[];
  positionStats: DashboardPositionStats;
  pnl: DashboardPnlSummary;
  recentAlerts: RiskEvent[];
  health: DashboardHealthSummary;
  updatedAt: string | null;
}

export interface DashboardEquityCurvePoint {
  timestamp: string;
  label: string;
  value: number;
  drawdown: number | null;
  source: string | null;
}

type JsonRecord = Record<string, unknown>;

function asRecord(value: unknown): JsonRecord | null {
  return typeof value === "object" && value !== null ? (value as JsonRecord) : null;
}

function firstValue(source: JsonRecord, keys: string[]): unknown {
  for (const key of keys) {
    if (key in source) {
      const value = source[key];
      if (value !== undefined && value !== null) {
        return value;
      }
    }
  }

  return undefined;
}

function readString(source: JsonRecord, keys: string[], fallback = ""): string {
  const value = firstValue(source, keys);

  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return fallback;
}

function readOptionalString(source: JsonRecord, keys: string[]): string | null {
  const value = firstValue(source, keys);

  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function readNumber(source: JsonRecord, keys: string[], fallback = 0): number {
  const value = firstValue(source, keys);

  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
}

function readOptionalNumber(source: JsonRecord, keys: string[]): number | null {
  const value = firstValue(source, keys);

  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return null;
}

function readBoolean(source: JsonRecord, keys: string[], fallback = false): boolean {
  const value = firstValue(source, keys);

  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "true" || normalized === "1" || normalized === "enabled" || normalized === "active" || normalized === "yes") {
      return true;
    }
    if (normalized === "false" || normalized === "0" || normalized === "disabled" || normalized === "inactive" || normalized === "no") {
      return false;
    }
  }

  if (typeof value === "number") {
    return value !== 0;
  }

  return fallback;
}

function readArray(source: JsonRecord, keys: string[]): unknown[] {
  const value = firstValue(source, keys);
  return Array.isArray(value) ? value : [];
}

function readRecord(source: JsonRecord, keys: string[]): JsonRecord | null {
  const value = firstValue(source, keys);
  return asRecord(value);
}

function unwrapEnvelope<T>(payload: ApiEnvelope<T> | T): T {
  const record = asRecord(payload);

  if (record && "data" in record && "error" in record) {
    return (record.data as T) ?? ({} as T);
  }

  return payload as T;
}

function normalizeAccount(source: JsonRecord): DashboardAccount {
  return {
    id: readString(source, ["id", "account_id", "accountId", "broker_account_id", "brokerAccountId"], "account"),
    broker: readString(source, ["broker", "broker_name", "brokerName"], "UNKNOWN"),
    environment: readString(source, ["environment", "env"], "paper"),
    equity: readNumber(source, ["equity", "net_liquidity", "netLiquidity", "account_value", "accountValue"], 0),
    cash: readNumber(source, ["cash", "available_cash", "availableCash", "buying_power_cash"], 0),
    buyingPower: readNumber(source, ["buying_power", "buyingPower", "buying_power_value", "buyingPowerValue"], 0),
    dayPnl: readNumber(source, ["day_pnl", "dayPnl", "daily_pnl", "dailyPnl"], 0),
    dayPnlPercent: readNumber(source, ["day_pnl_percent", "dayPnlPercent", "daily_pnl_percent", "dailyPnlPercent"], 0),
  };
}

function normalizePosition(source: JsonRecord): DashboardPosition {
  const quantity = readNumber(source, ["quantity", "qty", "position_size", "positionSize"], 0);
  const marketPrice = readNumber(source, ["market_price", "marketPrice", "last_price", "lastPrice"], 0);
  const marketValue = readOptionalNumber(source, ["market_value", "marketValue", "value"]) ?? quantity * marketPrice;

  return {
    symbol: readString(source, ["symbol", "ticker", "instrument", "asset"], "UNKNOWN"),
    quantity,
    avgPrice: readNumber(source, ["avg_price", "avgPrice", "average_price", "averagePrice", "cost_basis", "costBasis"], 0),
    marketPrice,
    marketValue,
    unrealizedPnl: readNumber(source, ["unrealized_pnl", "unrealizedPnl", "pnl_unrealized", "unrealized"], 0),
    realizedPnl: readOptionalNumber(source, ["realized_pnl", "realizedPnl", "pnl_realized", "realized"]),
    weight: readOptionalNumber(source, ["weight", "portfolio_weight", "portfolioWeight"]),
  };
}

function normalizePositions(payload: unknown): DashboardPosition[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["positions", "holdings", "items", "portfolio_positions", "portfolioPositions", "rows"])
        : [];

  return items.map((item) => normalizePosition(asRecord(item) ?? {})).filter((position) => position.symbol.length > 0);
}

function normalizeAlerts(payload: unknown): RiskEvent[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["recent_alerts", "recentAlerts", "recent_events", "recentEvents", "alerts", "events", "risk_events", "riskEvents"])
        : [];

  return items.map((item) => normalizeRiskEvent(item));
}

function calculatePositionStats(positions: DashboardPosition[]): DashboardPositionStats {
  return positions.reduce<DashboardPositionStats>(
    (stats, position) => {
      const signedValue = position.marketValue;
      const absoluteValue = Math.abs(signedValue);

      return {
        totalPositions: stats.totalPositions + 1,
        longPositions: stats.longPositions + (position.quantity > 0 ? 1 : 0),
        shortPositions: stats.shortPositions + (position.quantity < 0 ? 1 : 0),
        flatPositions: stats.flatPositions + (position.quantity === 0 ? 1 : 0),
        grossExposure: stats.grossExposure + absoluteValue,
        netExposure: stats.netExposure + signedValue,
        unrealizedPnl: stats.unrealizedPnl + position.unrealizedPnl,
      };
    },
    {
      totalPositions: 0,
      longPositions: 0,
      shortPositions: 0,
      flatPositions: 0,
      grossExposure: 0,
      netExposure: 0,
      unrealizedPnl: 0,
    },
  );
}

function normalizePnl(source: JsonRecord, positions: DashboardPosition[], account: DashboardAccount): DashboardPnlSummary {
  const unrealized = readNumber(source, ["unrealized_pnl", "unrealizedPnl", "positions_unrealized_pnl", "positionsUnrealizedPnl"], positions.reduce((sum, position) => sum + position.unrealizedPnl, 0));
  const realized = readOptionalNumber(source, ["realized_pnl", "realizedPnl", "closed_pnl", "closedPnl"]);
  const total = readOptionalNumber(source, ["total_pnl", "totalPnl", "pnl", "net_pnl", "netPnl"]) ?? account.dayPnl + unrealized + (realized ?? 0);

  return {
    day: readNumber(source, ["day_pnl", "dayPnl", "daily_pnl", "dailyPnl"], account.dayPnl),
    dayPercent: readNumber(source, ["day_pnl_percent", "dayPnlPercent", "daily_pnl_percent", "dailyPnlPercent"], account.dayPnlPercent),
    unrealized,
    realized,
    total,
  };
}

function normalizeHealth(source: JsonRecord, alerts: RiskEvent[]): DashboardHealthSummary {
  const rawStatus = readString(source, ["status", "health_status", "healthStatus"], "").toLowerCase();

  if (rawStatus === "healthy" || rawStatus === "warning" || rawStatus === "critical" || rawStatus === "unknown") {
    return {
      status: rawStatus,
      label: rawStatus === "healthy" ? "Healthy" : rawStatus === "warning" ? "Warning" : rawStatus === "critical" ? "Critical" : "Unknown",
      message: readString(source, ["message", "summary", "description"], rawStatus === "healthy" ? "当前没有高优先级风险告警。" : "风险事件由后端实时推送。"),
    };
  }

  const hasCritical = alerts.some((alert) => alert.severity === "CRITICAL");
  const hasHigh = alerts.some((alert) => alert.severity === "HIGH");
  const hasMedium = alerts.some((alert) => alert.severity === "MEDIUM");

  if (hasCritical) {
    return { status: "critical", label: "Critical", message: "存在 CRITICAL 级风险命中事件，需优先处理。" };
  }

  if (hasHigh || hasMedium) {
    return { status: "warning", label: "Warning", message: "近期有风险事件命中，正在持续跟踪。" };
  }

  return { status: "healthy", label: "Healthy", message: "当前没有高优先级风险告警。" };
}

function normalizeOverviewPayload(payload: unknown): DashboardOverview {
  const source = asRecord(payload) ?? {};
  const accountSource = readRecord(source, ["account", "overview", "account_overview", "accountOverview", "summary"]) ?? source;
  const account = normalizeAccount(accountSource);
  const positions = normalizePositions(source);
  const alerts = normalizeAlerts(source);
  const positionStats = calculatePositionStats(positions);

  return {
    account,
    positions,
    positionStats,
    pnl: normalizePnl(readRecord(source, ["pnl", "performance", "profit_loss", "profitLoss"]) ?? source, positions, account),
    recentAlerts: alerts,
    health: normalizeHealth(readRecord(source, ["health", "status", "summary"]) ?? source, alerts),
    updatedAt: readOptionalString(source, ["updated_at", "updatedAt", "timestamp", "as_of", "asOf"]),
  };
}

function normalizeCurvePoint(input: unknown, index: number): DashboardEquityCurvePoint {
  const source = asRecord(input) ?? {};
  const timestamp = readString(source, ["timestamp", "time", "date", "occurred_at", "occurredAt", "point_at", "pointAt"], `point-${index + 1}`);

  return {
    timestamp,
    label: readString(source, ["label", "display_time", "displayTime", "time_label", "timeLabel"], timestamp),
    value: readNumber(source, ["value", "equity", "nav", "balance", "account_value", "accountValue"], 0),
    drawdown: readOptionalNumber(source, ["drawdown", "drawdown_percent", "drawdownPercent", "dd"]),
    source: readOptionalString(source, ["source", "channel", "origin"]),
  };
}

function normalizeCurvePayload(payload: unknown): DashboardEquityCurvePoint[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "points", "series", "curve", "equity_curve", "equityCurve", "data"])
        : [];

  return items.map((item, index) => normalizeCurvePoint(item, index));
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
  const response = await httpClient.get<ApiEnvelope<unknown>>("/dashboard/overview");
  return normalizeOverviewPayload(unwrapEnvelope(response.data));
}

export async function getDashboardEquityCurve(): Promise<DashboardEquityCurvePoint[]> {
  const response = await httpClient.get<ApiEnvelope<unknown>>("/dashboard/equity-curve");
  return normalizeCurvePayload(unwrapEnvelope(response.data));
}
