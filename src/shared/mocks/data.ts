import {
  DashboardOverview,
  RiskSummary,
  SessionState,
  TradingWorkspace,
} from "@/shared/types/domain";

export const mockSession: SessionState = {
  accessToken: "mock-access-token",
  refreshToken: "mock-refresh-token",
  user: {
    id: "usr_admin_001",
    email: "alex@quantflow.local",
    fullName: "Alex Johnson",
    role: "ADMIN",
  },
};

export const mockDashboardOverview: DashboardOverview = {
  account: {
    id: "acc_paper_001",
    broker: "ALPACA",
    environment: "paper",
    equity: 124592.4,
    cash: 41240,
    buyingPower: 201840,
    dayPnl: 1240.5,
    dayPnlPercent: 1.01,
  },
  positions: [
    { symbol: "TSLA", quantity: 100, avgPrice: 240.5, marketPrice: 245.5, unrealizedPnl: 500 },
    { symbol: "NVDA", quantity: 50, avgPrice: 480, marketPrice: 476.2, unrealizedPnl: -190 },
    { symbol: "AAPL", quantity: 200, avgPrice: 175.2, marketPrice: 176.5, unrealizedPnl: 260 },
  ],
  strategies: [
    { id: "S1", name: "Trend_Follow_V1", symbols: ["AAPL", "TSLA"], status: "RUNNING", dailyPnl: 450 },
    { id: "S2", name: "Mean_Rev_SPY", symbols: ["SPY"], status: "STOPPED", dailyPnl: -50 },
    { id: "S3", name: "Gap_Fade_Alpha", symbols: ["NVDA", "AMD"], status: "RUNNING", dailyPnl: 120 },
  ],
  logs: [
    { id: 1, timestamp: "14:32:01", level: "INFO", message: "Strategy Trend_Follow_V1 triggered BUY AAPL @ 150.20" },
    { id: 2, timestamp: "14:32:02", level: "WARN", message: "Order filled partially: 50/100 shares" },
    { id: 3, timestamp: "14:35:10", level: "INFO", message: "Market data connected via Alpaca paper feed (18ms)" },
  ],
  equityCurve: Array.from({ length: 32 }, (_, index) => ({
    time: `09:${index.toString().padStart(2, "0")}`,
    value: 100000 + index * 140 + ((index % 3) - 1) * 190,
  })),
};

export const mockTradingWorkspace: TradingWorkspace = {
  account: mockDashboardOverview.account,
  activeSymbol: "TSLA",
  askLevels: [
    { price: 245.65, size: 100, total: 100 },
    { price: 245.6, size: 300, total: 400 },
    { price: 245.55, size: 150, total: 550 },
    { price: 245.5, size: 500, total: 1050 },
  ],
  bidLevels: [
    { price: 245.45, size: 200, total: 200 },
    { price: 245.4, size: 100, total: 300 },
    { price: 245.35, size: 450, total: 750 },
    { price: 245.3, size: 800, total: 1550 },
  ],
  orders: [
    {
      clientOrderId: "ord_20260414_001",
      symbol: "AMD",
      side: "BUY",
      quantity: 200,
      limitPrice: 98.5,
      status: "OPEN",
      submittedAt: "2026-04-14T10:00:01Z",
    },
    {
      clientOrderId: "ord_20260414_002",
      symbol: "SPY",
      side: "SELL",
      quantity: 50,
      limitPrice: 401,
      status: "OPEN",
      submittedAt: "2026-04-14T10:02:45Z",
    },
  ],
};

export const mockRiskSummary: RiskSummary = {
  hardLimits: {
    maxDailyLoss: 5000,
    maxSingleOrderValue: 50000,
    maxPositionSizePercent: 20,
  },
  restrictions: {
    restrictedSymbols: ["GME", "AMC", "DOGE"],
    marketHoursOnly: true,
  },
  recentEvents: [
    {
      id: "risk_evt_001",
      severity: "MEDIUM",
      message: "Daily exposure reached 72% of configured threshold.",
      occurredAt: "2026-04-14T07:20:00Z",
    },
  ],
};
