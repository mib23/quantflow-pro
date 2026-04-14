import { LogEntry, Order, OrderBookLevel, Position, Strategy } from "./types";

export const MOCK_POSITIONS: Position[] = [
  { symbol: 'TSLA', qty: 100, avgPrice: 240.50, currentPrice: 245.50, pnl: 500, pnlPercent: 2.08 },
  { symbol: 'NVDA', qty: 50, avgPrice: 480.00, currentPrice: 476.20, pnl: -190, pnlPercent: -0.79 },
  { symbol: 'AAPL', qty: 200, avgPrice: 175.20, currentPrice: 176.50, pnl: 260, pnlPercent: 0.74 },
];

export const MOCK_STRATEGIES: Strategy[] = [
  { id: 'S1', name: 'Trend_Follow_V1', symbols: ['AAPL', 'TSLA'], status: 'RUNNING', dailyPnl: 450 },
  { id: 'S2', name: 'Mean_Rev_SPY', symbols: ['SPY'], status: 'STOPPED', dailyPnl: -50 },
  { id: 'S3', name: 'Gap_Fade_Alpha', symbols: ['NVDA', 'AMD'], status: 'RUNNING', dailyPnl: 120 },
];

export const MOCK_ORDERS: Order[] = [
  { id: '#101', symbol: 'AMD', side: 'BUY', qty: 200, price: 98.50, status: 'OPEN', timestamp: '10:00:01' },
  { id: '#102', symbol: 'SPY', side: 'SELL', qty: 50, price: 401.00, status: 'OPEN', timestamp: '10:02:45' },
];

export const MOCK_LOGS: LogEntry[] = [
  { id: 1, timestamp: '14:32:01', level: 'INFO', message: 'Strategy Trend_Follow_V1 triggered BUY AAPL @ 150.20' },
  { id: 2, timestamp: '14:32:02', level: 'WARN', message: 'Order filled partially: 50/100 shares' },
  { id: 3, timestamp: '14:35:10', level: 'INFO', message: 'Market data connected via IBKR Gateway (15ms)' },
  { id: 4, timestamp: '14:40:00', level: 'ERROR', message: 'Connection timeout: Data feed retrying...' },
];

export const MOCK_EQUITY_DATA = Array.from({ length: 50 }, (_, i) => ({
  time: `10:${i < 10 ? '0' + i : i}`,
  value: 100000 + Math.random() * 5000 - 2500,
}));

export const MOCK_ASK: OrderBookLevel[] = [
  { price: 245.65, size: 100, total: 100 },
  { price: 245.60, size: 300, total: 400 },
  { price: 245.55, size: 150, total: 550 },
  { price: 245.50, size: 500, total: 1050 },
];

export const MOCK_BID: OrderBookLevel[] = [
  { price: 245.45, size: 200, total: 200 },
  { price: 245.40, size: 100, total: 300 },
  { price: 245.35, size: 450, total: 750 },
  { price: 245.30, size: 800, total: 1550 },
];

export const STRATEGY_CODE = `class MyStrategy(StrategyBase):
    def init(self):
        self.ma_fast = MA(self.data.close, 20)
        self.ma_slow = MA(self.data.close, 50)

    def on_bar(self, bar):
        # Entry Logic
        if self.ma_fast[-1] > self.ma_slow[-1]:
            if self.position.size == 0:
                self.buy(size=100)
                self.log(f"BUY at {bar.close}")
        
        # Exit Logic
        elif self.ma_fast[-1] < self.ma_slow[-1]:
             if self.position.size > 0:
                 self.sell(size=100)
                 self.log(f"SELL at {bar.close}")`;