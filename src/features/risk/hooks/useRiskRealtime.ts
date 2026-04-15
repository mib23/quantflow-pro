import { useEffect } from "react";
import { QueryClient, useQueryClient } from "@tanstack/react-query";

import { env } from "@/shared/config/env";
import { dashboardQueryKeys } from "@/features/dashboard/hooks/dashboardQueryKeys";
import { riskQueryKeys } from "@/features/risk/hooks/riskQueryKeys";
import { normalizeRiskEvent, normalizeRiskRule, RiskEvent, RiskRule, RiskSummary } from "@/entities/risk-rule/model";
import { DashboardOverview } from "@/features/dashboard/api/getDashboardOverview";

type StreamRecord = Record<string, unknown>;

function asRecord(value: unknown): StreamRecord | null {
  return typeof value === "object" && value !== null ? (value as StreamRecord) : null;
}

function parseMessage(rawMessage: unknown): StreamRecord | null {
  if (typeof rawMessage === "string") {
    try {
      return asRecord(JSON.parse(rawMessage));
    } catch {
      return null;
    }
  }

  return asRecord(rawMessage);
}

function pickRecord(message: StreamRecord): StreamRecord {
  return asRecord(message.data) ?? asRecord(message.payload) ?? message;
}

function extractText(message: StreamRecord, record: StreamRecord): string {
  const kind = [message.type, message.kind, message.event, message.channel, record.type, record.kind, record.event, record.channel]
    .filter((value) => typeof value === "string")
    .map((value) => String(value).toLowerCase())
    .join(" ");

  return kind;
}

function extractAccountId(message: StreamRecord, record: StreamRecord): string | null {
  const value = record.account_id ?? record.accountId ?? message.account_id ?? message.accountId;
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function looksLikeEvent(kind: string, record: StreamRecord): boolean {
  return (
    kind.includes("event") ||
    kind.includes("alert") ||
    kind.includes("hit") ||
    "severity" in record ||
    "occurred_at" in record ||
    "occurredAt" in record
  );
}

function looksLikeRule(kind: string, record: StreamRecord): boolean {
  return (
    kind.includes("rule") ||
    kind.includes("config") ||
    "threshold" in record ||
    "threshold_value" in record ||
    "thresholdValue" in record ||
    "enabled" in record ||
    "status" in record ||
    "state" in record
  );
}

function upsertItemById<T extends { id: string }>(current: T[] | undefined, item: T, limit = 20): T[] {
  const base = current ?? [];
  const filtered = base.filter((entry) => entry.id !== item.id);
  return [item, ...filtered].slice(0, limit);
}

function maybeUpdateDashboardOverview(queryClient: QueryClient, event: RiskEvent): void {
  queryClient.setQueryData<DashboardOverview | undefined>(dashboardQueryKeys.overview(), (current) => {
    if (!current) {
      return current;
    }

    return {
      ...current,
      recentAlerts: upsertItemById(current.recentAlerts, event, 10),
      health:
        event.severity === "CRITICAL"
          ? { status: "critical", label: "Critical", message: "实时风险频道推送了 CRITICAL 告警。" }
          : current.health,
    };
  });
}

function maybeUpdateRiskSummary(queryClient: QueryClient, event: RiskEvent): void {
  queryClient.setQueryData<RiskSummary | undefined>(riskQueryKeys.summary(), (current) => {
    if (!current) {
      return current;
    }

    const status = event.status.trim().toUpperCase();

    return {
      ...current,
      triggeredToday: current.triggeredToday + 1,
      blockedOrdersToday:
        status.includes("BLOCK") || status.includes("REJECT") || status.includes("DENY") ? current.blockedOrdersToday + 1 : current.blockedOrdersToday,
      unresolvedEvents: status.includes("OPEN") || status.includes("ACTIVE") ? current.unresolvedEvents + 1 : current.unresolvedEvents,
      recentEvents: upsertItemById(current.recentEvents, event, 10),
    };
  });
}

function maybeUpdateRiskRules(queryClient: QueryClient, rule: RiskRule): void {
  queryClient.setQueryData<RiskRule[] | undefined>(riskQueryKeys.rules(), (current) => {
    if (!current) {
      return current;
    }

    return current.map((item) => (item.id === rule.id ? rule : item));
  });
}

export function applyRiskStreamMessage(queryClient: QueryClient, accountId: string | null | undefined, rawMessage: unknown): void {
  const message = parseMessage(rawMessage);

  if (!message) {
    return;
  }

  const record = pickRecord(message);
  const kind = extractText(message, record);
  const messageAccountId = extractAccountId(message, record);

  if (accountId && messageAccountId && messageAccountId !== accountId) {
    return;
  }

  if (looksLikeEvent(kind, record)) {
    const event = normalizeRiskEvent(record);

    if (event.id.length === 0 || event.message.length === 0) {
      return;
    }

    queryClient.setQueryData<RiskEvent[] | undefined>(riskQueryKeys.events(), (current) => upsertItemById(current, event, 20));
    queryClient.setQueryData<RiskSummary | undefined>(riskQueryKeys.summary(), (current) =>
      current ? { ...current, recentEvents: upsertItemById(current.recentEvents, event, 10) } : current,
    );
    maybeUpdateDashboardOverview(queryClient, event);
    maybeUpdateRiskSummary(queryClient, event);
    return;
  }

  if (looksLikeRule(kind, record)) {
    const rule = normalizeRiskRule(record);

    if (rule.id.length === 0) {
      return;
    }

    maybeUpdateRiskRules(queryClient, rule);
  }
}

export function useRiskRealtime(accountId: string | null | undefined) {
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
