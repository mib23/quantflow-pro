export const tradingQueryKeys = {
  root: ["trading"] as const,
  account: () => [...tradingQueryKeys.root, "account"] as const,
  orders: () => [...tradingQueryKeys.root, "orders"] as const,
  executions: () => [...tradingQueryKeys.root, "executions"] as const,
  quote: (symbol: string) => [...tradingQueryKeys.root, "quote", symbol] as const,
};
