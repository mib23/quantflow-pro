export const dashboardQueryKeys = {
  root: ["dashboard"] as const,
  overview: () => [...dashboardQueryKeys.root, "overview"] as const,
  equityCurve: () => [...dashboardQueryKeys.root, "equity-curve"] as const,
};
