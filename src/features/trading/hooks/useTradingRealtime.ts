import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { env } from "@/shared/config/env";
import { applyTradingStreamMessage } from "@/features/trading/hooks/useTradingQueries";

export function useTradingRealtime(symbol: string, brokerAccountId: string | null) {
  const queryClient = useQueryClient();

  useEffect(() => {
    const normalizedSymbol = symbol.trim().toUpperCase();

    if (!normalizedSymbol || typeof WebSocket === "undefined") {
      return undefined;
    }

    const streamBase = env.wsBaseUrl.replace(/\/$/, "");
    const streamUrl = streamBase;
    let disposed = false;
    let socket: WebSocket | null = null;

    try {
      socket = new WebSocket(streamUrl);
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
            channels: [
              `market.quote.${normalizedSymbol}`,
              ...(brokerAccountId ? [`orders.status.${brokerAccountId}`] : []),
            ],
          }),
        );
      } catch {
        // Ignore subscription errors. Query polling still works.
      }
    });

    socket.addEventListener("message", (event) => {
      applyTradingStreamMessage(queryClient, event.data);
    });

    socket.addEventListener("error", () => {
      // Fall back to query-driven updates.
    });

    return () => {
      disposed = true;
      socket?.close();
    };
  }, [brokerAccountId, queryClient, symbol]);
}
