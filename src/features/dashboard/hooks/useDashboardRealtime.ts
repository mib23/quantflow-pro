import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { env } from "@/shared/config/env";
import { applyRiskStreamMessage } from "@/features/risk/hooks/useRiskRealtime";

export function useDashboardRealtime(accountId: string | null | undefined) {
  const queryClient = useQueryClient();

  useEffect(() => {
    const normalizedAccountId = accountId?.trim();

    if (!normalizedAccountId || typeof WebSocket === "undefined") {
      return undefined;
    }

    const streamBase = env.wsBaseUrl.replace(/\/$/, "");
    let disposed = false;
    let socket: WebSocket | null = null;

    try {
      socket = new WebSocket(streamBase);
    } catch {
      return undefined;
    }

    socket.addEventListener("open", () => {
      if (disposed) {
        return;
      }

      try {
        socket?.send(
          JSON.stringify({
            action: "subscribe",
            channels: [`risk.events.${normalizedAccountId}`],
          }),
        );
      } catch {
        // Query cache remains authoritative if subscription fails.
      }
    });

    socket.addEventListener("message", (event) => {
      applyRiskStreamMessage(queryClient, normalizedAccountId, event.data);
    });

    socket.addEventListener("error", () => {
      // Stream is opportunistic. Query-driven refetch remains available.
    });

    return () => {
      disposed = true;
      socket?.close();
    };
  }, [accountId, queryClient]);
}
