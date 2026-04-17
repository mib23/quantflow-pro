export const strategyRuntimeQueryKeys = {
  root: ["strategy-runtime"] as const,
  strategies: () => [...strategyRuntimeQueryKeys.root, "strategies"] as const,
  strategyDetail: (strategyId: string) => [...strategyRuntimeQueryKeys.root, "strategy-detail", strategyId] as const,
  brokerAccounts: () => [...strategyRuntimeQueryKeys.root, "broker-accounts"] as const,
  runtimeInstances: () => [...strategyRuntimeQueryKeys.root, "instances"] as const,
  runtimeInstanceDetail: (instanceId: string) => [...strategyRuntimeQueryKeys.root, "instance-detail", instanceId] as const,
  runtimeLogs: (instanceId: string) => [...strategyRuntimeQueryKeys.root, "instance-logs", instanceId] as const,
  runtimeOrders: (instanceId: string) => [...strategyRuntimeQueryKeys.root, "instance-orders", instanceId] as const,
  runtimeRiskEvents: (instanceId: string) => [...strategyRuntimeQueryKeys.root, "instance-risk-events", instanceId] as const,
};
