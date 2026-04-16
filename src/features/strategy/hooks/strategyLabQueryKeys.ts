export const strategyLabQueryKeys = {
  root: ["strategy-lab"] as const,
  strategies: () => [...strategyLabQueryKeys.root, "strategies"] as const,
  strategy: (strategyId: string | null) => [...strategyLabQueryKeys.root, "strategy", strategyId] as const,
  jobs: () => [...strategyLabQueryKeys.root, "jobs"] as const,
  job: (jobId: string | null) => [...strategyLabQueryKeys.root, "job", jobId] as const,
  result: (jobId: string | null) => [...strategyLabQueryKeys.root, "result", jobId] as const,
};
