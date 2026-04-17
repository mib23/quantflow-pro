export type UserRole = "ADMIN" | "TRADER" | "RESEARCHER";
export type OrderSide = "BUY" | "SELL";
export type OrderType = "MARKET" | "LIMIT" | "STOP";
export type OrderStatus =
  | "PENDING_SUBMIT"
  | "SUBMITTED"
  | "OPEN"
  | "PARTIALLY_FILLED"
  | "FILLED"
  | "CANCEL_REQUESTED"
  | "CANCELED"
  | "REJECTED"
  | "FAILED";

export interface SessionUser {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
}

export interface SessionState {
  accessToken: string | null;
  refreshToken: string | null;
  user: SessionUser | null;
}

export interface AccountOverview {
  id: string;
  broker: string;
  environment: string;
  equity: number;
  cash: number;
  buyingPower: number;
  dayPnl: number;
  dayPnlPercent: number;
}

export interface BrokerAccount extends AccountOverview {
  brokerAccountNo?: string;
  externalAccountId?: string;
  status?: string;
}

export interface Position {
  brokerAccountId?: string;
  symbol: string;
  quantity: number;
  avgPrice: number;
  marketPrice: number;
  marketValue?: number;
  unrealizedPnl: number;
}

export interface Order {
  clientOrderId: string;
  brokerOrderId?: string | null;
  symbol: string;
  side: OrderSide;
  orderType?: OrderType;
  quantity: number;
  limitPrice: number | null;
  status: OrderStatus;
  timeInForce?: string;
  idempotencyKey?: string;
  submittedAt: string;
  updatedAt?: string;
}

export interface Execution {
  id: string;
  orderId: string;
  clientOrderId: string;
  brokerExecutionId: string;
  symbol: string;
  side: OrderSide;
  filledQuantity: number;
  filledPrice: number;
  feeAmount: number;
  executedAt: string;
}

export interface OrderBookLevel {
  price: number;
  size: number;
  total: number;
}

export interface BrokerQuote {
  symbol: string;
  bid: number | null;
  ask: number | null;
  last: number | null;
  timestamp: string;
}

export interface StrategySummary {
  id: string;
  name: string;
  description: string | null;
  status: "ACTIVE" | "ARCHIVED" | "DRAFT";
  defaultParameters: Record<string, unknown>;
  latestVersionId: string | null;
  latestVersionTag: string | null;
  updatedAt: string;
}

export interface StrategyVersion {
  id: string;
  strategyId: string;
  versionNumber: number;
  versionTag: string;
  code: string;
  parameters: Record<string, unknown>;
  versionNote: string | null;
  createdBy: string;
  createdAt: string;
}

export interface StrategyDetail extends StrategySummary {
  ownerUserId: string;
  createdAt: string;
  versions: StrategyVersion[];
}

export interface BacktestLog {
  id: string;
  level: string;
  code: string;
  message: string;
  details: Record<string, unknown>;
  createdAt: string;
}

export interface BacktestJob {
  id: string;
  strategyId: string;
  strategyVersionId: string;
  strategyName: string;
  strategyVersionTag: string;
  status: "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELED";
  queueName: string;
  queueJobId: string | null;
  symbols: string[];
  benchmark: string | null;
  parameters: Record<string, unknown>;
  timeRange: {
    start: string;
    end: string;
  };
  failureCode: string | null;
  failureReason: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  resultAvailable: boolean;
  logs: BacktestLog[];
}

export interface BacktestMetricMap {
  totalReturn?: number;
  sharpe?: number;
  maxDrawdown?: number;
  winRate?: number;
  tradeCount?: number;
  [key: string]: unknown;
}

export interface BacktestResult {
  jobId: string;
  metrics: BacktestMetricMap;
  equityCurve: Array<{ time: string; equity: number }>;
  trades: Array<Record<string, unknown>>;
  report: Record<string, unknown>;
  reportFormat: string;
  generatedAt: string;
}

export interface LogEntry {
  id: number;
  timestamp: string;
  level: "INFO" | "WARN" | "ERROR";
  message: string;
}

export interface DashboardOverview {
  account: AccountOverview;
  positions: Position[];
  strategies: StrategySummary[];
  logs: LogEntry[];
  equityCurve: Array<{ time: string; value: number }>;
}

export interface TradingWorkspace {
  account: AccountOverview;
  activeSymbol: string;
  bidLevels: OrderBookLevel[];
  askLevels: OrderBookLevel[];
  orders: Order[];
}

export interface RiskSummary {
  hardLimits: {
    maxDailyLoss: number;
    maxSingleOrderValue: number;
    maxPositionSizePercent: number;
  };
  restrictions: {
    restrictedSymbols: string[];
    marketHoursOnly: boolean;
  };
  recentEvents: Array<{
    id: string;
    severity: string;
    message: string;
    occurredAt: string;
  }>;
}

export interface ApiEnvelope<T> {
  data: T;
  meta: {
    request_id?: string | null;
  };
  error: {
    code: string;
    message: string;
  } | null;
}
