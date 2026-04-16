export const riskQueryKeys = {
  root: ["risk"] as const,
  summary: () => [...riskQueryKeys.root, "summary"] as const,
  rules: () => [...riskQueryKeys.root, "rules"] as const,
  events: () => [...riskQueryKeys.root, "events"] as const,
};
