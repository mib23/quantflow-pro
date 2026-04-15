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
  symbols: string[];
  status: "RUNNING" | "STOPPED" | "ERROR";
  dailyPnl: number;
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
