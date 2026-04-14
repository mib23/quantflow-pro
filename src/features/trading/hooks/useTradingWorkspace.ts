import { useQuery } from "@tanstack/react-query";

import { getTradingWorkspace } from "@/features/trading/api/getTradingWorkspace";

export function useTradingWorkspace() {
  return useQuery({
    queryKey: ["trading-workspace"],
    queryFn: getTradingWorkspace,
  });
}
