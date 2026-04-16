import { httpClient } from "@/shared/api/http";
import { ApiEnvelope } from "@/shared/types/domain";

import { normalizeRiskEvent, normalizeRiskRule, normalizeRiskSummary, RiskEvent, RiskRule, RiskSummary } from "@/entities/risk-rule/model";

type JsonRecord = Record<string, unknown>;

function asRecord(value: unknown): JsonRecord | null {
  return typeof value === "object" && value !== null ? (value as JsonRecord) : null;
}

function firstValue(source: JsonRecord, keys: string[]): unknown {
  for (const key of keys) {
    if (key in source) {
      const value = source[key];
      if (value !== undefined && value !== null) {
        return value;
      }
    }
  }

  return undefined;
}

function readArray(source: JsonRecord, keys: string[]): unknown[] {
  const value = firstValue(source, keys);
  return Array.isArray(value) ? value : [];
}

function readString(source: JsonRecord, keys: string[], fallback = ""): string {
  const value = firstValue(source, keys);

  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return fallback;
}

function unwrapEnvelope<T>(payload: ApiEnvelope<T> | T): T {
  const record = asRecord(payload);

  if (record && "data" in record && "error" in record) {
    return (record.data as T) ?? ({} as T);
  }

  return payload as T;
}

function normalizeRuleCollection(payload: unknown): RiskRule[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "rules", "data", "records", "results"])
        : [];

  return items.map((item) => normalizeRiskRule(item));
}

function normalizeEventCollection(payload: unknown): RiskEvent[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "events", "data", "records", "results", "recent_events", "recentEvents"])
        : [];

  return items.map((item) => normalizeRiskEvent(item));
}

function normalizeRuleResponse(payload: unknown): RiskRule | null {
  const source = asRecord(payload);

  if (source) {
    const candidate = firstValue(source, ["rule", "data", "item", "record", "result"]);
    if (candidate !== undefined && candidate !== null) {
      return normalizeRiskRule(candidate);
    }
    if ("id" in source || "rule_id" in source || "ruleId" in source) {
      return normalizeRiskRule(source);
    }
  }

  return null;
}

export async function getRiskOverview(): Promise<RiskSummary> {
  const response = await httpClient.get<ApiEnvelope<unknown>>("/risk/summary");
  return normalizeRiskSummary(unwrapEnvelope(response.data));
}

export async function getRiskRules(): Promise<RiskRule[]> {
  const response = await httpClient.get<ApiEnvelope<unknown>>("/risk/rules");
  return normalizeRuleCollection(unwrapEnvelope(response.data));
}

export type RiskEventsQuery = {
  accountId?: string | null;
  ruleId?: string | null;
  severity?: string | null;
  limit?: number;
};

export async function getRiskEvents(query: RiskEventsQuery = {}): Promise<RiskEvent[]> {
  const params = new URLSearchParams();

  if (query.accountId) {
    params.set("account_id", query.accountId);
  }

  if (query.ruleId) {
    params.set("rule_id", query.ruleId);
  }

  if (query.severity) {
    params.set("severity", query.severity);
  }

  if (typeof query.limit === "number" && Number.isFinite(query.limit)) {
    params.set("limit", String(query.limit));
  }

  const suffix = params.toString().length > 0 ? `?${params.toString()}` : "";
  const response = await httpClient.get<ApiEnvelope<unknown>>(`/risk/events${suffix}`);
  return normalizeEventCollection(unwrapEnvelope(response.data));
}

export async function activateRiskRule(ruleId: string): Promise<RiskRule | null> {
  const response = await httpClient.post<ApiEnvelope<unknown>>(`/risk/rules/${encodeURIComponent(ruleId)}/activate`);
  return normalizeRuleResponse(unwrapEnvelope(response.data));
}

export async function deactivateRiskRule(ruleId: string): Promise<RiskRule | null> {
  const response = await httpClient.post<ApiEnvelope<unknown>>(`/risk/rules/${encodeURIComponent(ruleId)}/deactivate`);
  return normalizeRuleResponse(unwrapEnvelope(response.data));
}
