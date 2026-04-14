export type Side = 'BUY' | 'SELL';
export type OrderType = 'LIMIT' | 'MARKET' | 'STOP';
export type StrategyStatus = 'RUNNING' | 'STOPPED' | 'ERROR';

export interface Position {
  symbol: string;
  qty: number;
  avgPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
}

export interface Strategy {
  id: string;
  name: string;
  symbols: string[];
  status: StrategyStatus;
  dailyPnl: number;
}

export interface Order {
  id: string;
  symbol: string;
  side: Side;
  qty: number;
  price: number;
  status: 'OPEN' | 'FILLED' | 'CANCELLED';
  timestamp: string;
}

export interface LogEntry {
  id: number;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
}

export interface OrderBookLevel {
  price: number;
  size: number;
  total: number;
}