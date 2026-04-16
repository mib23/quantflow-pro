import { useQuery } from "@tanstack/react-query";

import { getTradingWorkspace } from "@/features/trading/api/getTradingWorkspace";
import { tradingQueryKeys } from "@/features/trading/hooks/tradingQueryKeys";

export function useTradingWorkspace() {
  return useQuery({
    queryKey: [...tradingQueryKeys.root, "workspace"],
    queryFn: getTradingWorkspace,
  });
}
