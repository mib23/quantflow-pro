export type UserRole = "ADMIN" | "TRADER" | "RESEARCHER";
export type OrderSide = "BUY" | "SELL";
export type OrderType = "MARKET" | "LIMIT" | "STOP";
export type OrderStatus =
  | "PENDING_SUBMIT"
  | "OPEN"
  | "PARTIALLY_FILLED"
  | "FILLED"
  | "CANCEL_REQUESTED"
  | "CANCELLED";

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

export interface Position {
  symbol: string;
  quantity: number;
  avgPrice: number;
  marketPrice: number;
  unrealizedPnl: number;
}

export interface Order {
  clientOrderId: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  limitPrice: number | null;
  status: OrderStatus;
  submittedAt: string;
}

export interface OrderBookLevel {
  price: number;
  size: number;
  total: number;
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
