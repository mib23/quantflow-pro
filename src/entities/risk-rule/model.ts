type RiskJsonRecord = Record<string, unknown>;

export type RiskSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type RiskRuleStatus = "ACTIVE" | "INACTIVE" | "PAUSED" | "DRAFT" | "UNKNOWN";

export interface RiskRuleVersion {
  version: string;
  createdAt: string | null;
  createdBy: string | null;
  changeReason: string | null;
  snapshot?: RiskJsonRecord;
}

export interface RiskRuleScope {
  accountIds: string[];
  symbols: string[];
  strategies: string[];
  venues: string[];
  tags: string[];
  note: string | null;
}

export interface RiskRule {
  id: string;
  name: string;
  type: string;
  status: RiskRuleStatus;
  enabled: boolean;
  version: string;
  description: string;
  thresholdLabel: string;
  thresholdValue: number | null;
  thresholdUnit: string | null;
  scope: RiskRuleScope;
  createdAt: string | null;
  updatedAt: string | null;
  createdBy: string | null;
  updatedBy: string | null;
  versions: RiskRuleVersion[];
}

export interface RiskEvent {
  id: string;
  accountId: string | null;
  ruleId: string | null;
  ruleName: string | null;
  orderId: string | null;
  clientOrderId: string | null;
  severity: RiskSeverity;
  status: string;
  title: string;
  message: string;
  occurredAt: string;
  resolvedAt: string | null;
  source: string | null;
  details: RiskJsonRecord;
}

export interface RiskSummary {
  accountId: string | null;
  activeRules: number;
  triggeredToday: number;
  blockedOrdersToday: number;
  unresolvedEvents: number;
  hardLimits: {
    maxDailyLoss: number | null;
    maxSingleOrderValue: number | null;
    maxPositionSizePercent: number | null;
  };
  restrictions: {
    restrictedSymbols: string[];
    marketHoursOnly: boolean;
  };
  recentEvents: RiskEvent[];
  updatedAt: string | null;
}

function asRecord(value: unknown): RiskJsonRecord | null {
  return typeof value === "object" && value !== null ? (value as RiskJsonRecord) : null;
}

function firstValue(source: RiskJsonRecord, keys: string[]): unknown {
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

function readString(source: RiskJsonRecord, keys: string[], fallback = ""): string {
  const value = firstValue(source, keys);

  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return fallback;
}

function readOptionalString(source: RiskJsonRecord, keys: string[]): string | null {
  const value = firstValue(source, keys);

  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function readNumber(source: RiskJsonRecord, keys: string[], fallback = 0): number {
  const value = firstValue(source, keys);

  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
}

function readOptionalNumber(source: RiskJsonRecord, keys: string[]): number | null {
  const value = firstValue(source, keys);

  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return null;
}

function readBoolean(source: RiskJsonRecord, keys: string[], fallback = false): boolean {
  const value = firstValue(source, keys);

  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "true" || normalized === "1" || normalized === "enabled" || normalized === "active" || normalized === "yes") {
      return true;
    }
    if (normalized === "false" || normalized === "0" || normalized === "disabled" || normalized === "inactive" || normalized === "no") {
      return false;
    }
  }

  if (typeof value === "number") {
    return value !== 0;
  }

  return fallback;
}

function readStringArray(source: RiskJsonRecord, keys: string[]): string[] {
  const value = firstValue(source, keys);

  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (typeof item === "string") {
        return item.trim();
      }

      if (typeof item === "number" || typeof item === "boolean") {
        return String(item);
      }

      return "";
    })
    .filter((item) => item.length > 0);
}

function readRecord(source: RiskJsonRecord, keys: string[]): RiskJsonRecord | null {
  const value = firstValue(source, keys);
  return asRecord(value);
}

function normalizeStatus(value: unknown): RiskRuleStatus {
  if (typeof value !== "string") {
    return "UNKNOWN";
  }

  const normalized = value.trim().toUpperCase();

  if (normalized === "ACTIVE" || normalized === "ENABLED" || normalized === "ON" || normalized === "RUNNING") {
    return "ACTIVE";
  }

  if (normalized === "INACTIVE" || normalized === "DISABLED" || normalized === "OFF" || normalized === "STOPPED") {
    return "INACTIVE";
  }

  if (normalized === "PAUSED" || normalized === "SUSPENDED") {
    return "PAUSED";
  }

  if (normalized === "DRAFT") {
    return "DRAFT";
  }

  return "UNKNOWN";
}

export function normalizeRiskSeverity(value: unknown): RiskSeverity {
  if (typeof value !== "string") {
    return "LOW";
  }

  const normalized = value.trim().toUpperCase();

  if (normalized === "INFO" || normalized === "LOW" || normalized === "MEDIUM" || normalized === "HIGH" || normalized === "CRITICAL") {
    return normalized;
  }

  if (normalized === "WARN" || normalized === "WARNING") {
    return "MEDIUM";
  }

  if (normalized === "ERROR" || normalized === "SEVERE") {
    return "HIGH";
  }

  return "LOW";
}

export function normalizeRiskRuleStatus(value: unknown): RiskRuleStatus {
  return normalizeStatus(value);
}

export function normalizeRiskRule(input: unknown): RiskRule {
  const source = asRecord(input) ?? {};
  const versionsSource = firstValue(source, ["versions", "history", "rule_versions", "version_history", "audit_trail"]);
  const versions = Array.isArray(versionsSource)
    ? versionsSource
        .map((item, index) => normalizeRiskRuleVersion(item, index + 1))
        .filter((item) => item.version.length > 0)
    : [];
  const thresholdValue = readOptionalNumber(source, ["threshold_value", "thresholdValue", "value", "limit", "max_value", "maxValue"]);
  const version = readString(source, ["version", "current_version", "currentVersion", "revision"], versions[0]?.version ?? "v1");
  const statusSource = firstValue(source, ["status", "state"]);
  const rawStatus = normalizeRiskRuleStatus(statusSource);
  const enabled = readBoolean(source, ["enabled", "active", "is_active", "isActive"], false) || rawStatus === "ACTIVE";

  return {
    id: readString(source, ["id", "rule_id", "ruleId", "resource_id", "resourceId"], version),
    name: readString(source, ["name", "rule_name", "ruleName", "title"], "Risk Rule"),
    type: readString(source, ["type", "rule_type", "ruleType", "kind"], "rule"),
    status: rawStatus === "UNKNOWN" && enabled ? "ACTIVE" : rawStatus,
    enabled,
    version,
    description: readString(source, ["description", "summary", "memo", "note"], ""),
    thresholdLabel: readString(source, ["threshold_label", "thresholdLabel", "limit_label", "limitLabel", "value_label", "valueLabel"], "Threshold"),
    thresholdValue,
    thresholdUnit: readOptionalString(source, ["threshold_unit", "thresholdUnit", "unit", "currency"]),
    scope: {
      accountIds: readStringArray(source, ["account_ids", "accountIds", "accounts", "broker_account_ids", "brokerAccountIds"]),
      symbols: readStringArray(source, ["symbols", "symbol_ids", "symbolIds", "instrument_symbols", "instruments"]),
      strategies: readStringArray(source, ["strategies", "strategy_ids", "strategyIds"]),
      venues: readStringArray(source, ["venues", "markets", "exchanges"]),
      tags: readStringArray(source, ["tags", "labels"]),
      note: readOptionalString(source, ["scope_note", "scopeNote", "scope_description", "scopeDescription"]),
    },
    createdAt: readOptionalString(source, ["created_at", "createdAt", "inserted_at", "insertedAt"]),
    updatedAt: readOptionalString(source, ["updated_at", "updatedAt", "modified_at", "modifiedAt"]),
    createdBy: readOptionalString(source, ["created_by", "createdBy", "owner", "author"]),
    updatedBy: readOptionalString(source, ["updated_by", "updatedBy", "modified_by", "modifiedBy"]),
    versions,
  };
}

export function normalizeRiskRuleVersion(input: unknown, fallbackIndex: number): RiskRuleVersion {
  const source = asRecord(input) ?? {};
  const snapshot = readRecord(source, ["snapshot", "config", "payload", "data", "rule"]);

  return {
    version: readString(source, ["version", "revision", "name", "label"], `v${fallbackIndex}`),
    createdAt: readOptionalString(source, ["created_at", "createdAt", "updated_at", "updatedAt"]),
    createdBy: readOptionalString(source, ["created_by", "createdBy", "author", "updated_by", "updatedBy"]),
    changeReason: readOptionalString(source, ["change_reason", "changeReason", "reason", "note"]),
    snapshot: snapshot ?? undefined,
  };
}

export function normalizeRiskEvent(input: unknown): RiskEvent {
  const source = asRecord(input) ?? {};
  const details = readRecord(source, ["details", "payload", "context", "meta", "metadata", "event"]) ?? {};
  const message = readString(source, ["message", "reason", "summary", "description"], "");
  const title = readString(source, ["title", "heading"], message || "Risk Event");

  return {
    id: readString(source, ["id", "event_id", "eventId", "risk_event_id", "riskEventId"], `${readString(source, ["rule_id", "ruleId"], "event")}-${readString(source, ["occurred_at", "occurredAt", "timestamp"], new Date().toISOString())}`),
    accountId: readOptionalString(source, ["account_id", "accountId", "broker_account_id", "brokerAccountId"]),
    ruleId: readOptionalString(source, ["rule_id", "ruleId", "risk_rule_id", "riskRuleId"]),
    ruleName: readOptionalString(source, ["rule_name", "ruleName", "rule", "rule_title"]),
    orderId: readOptionalString(source, ["order_id", "orderId", "broker_order_id", "brokerOrderId"]),
    clientOrderId: readOptionalString(source, ["client_order_id", "clientOrderId"]),
    severity: normalizeRiskSeverity(firstValue(source, ["severity", "level", "priority"])),
    status: readString(source, ["status", "state", "action", "resolution"], "OPEN"),
    title,
    message: message || title,
    occurredAt: readString(source, ["occurred_at", "occurredAt", "timestamp", "created_at", "createdAt"], new Date().toISOString()),
    resolvedAt: readOptionalString(source, ["resolved_at", "resolvedAt", "closed_at", "closedAt"]),
    source: readOptionalString(source, ["source", "channel", "origin"]),
    details,
  };
}

export function normalizeRiskSummary(input: unknown): RiskSummary {
  const source = asRecord(input) ?? {};
  const hardLimitsSource = readRecord(source, ["hard_limits", "hardLimits", "limits", "thresholds"]) ?? {};
  const restrictionsSource = readRecord(source, ["restrictions", "constraints", "guards"]) ?? {};
  const recentEventsSource = firstValue(source, ["recent_events", "recentEvents", "events", "risk_events", "riskEvents"]);
  const recentEvents = Array.isArray(recentEventsSource) ? recentEventsSource.map((event) => normalizeRiskEvent(event)).filter((event) => event.id.length > 0) : [];
  const activeRules = readNumber(source, ["active_rules", "activeRules", "enabled_rules", "enabledRules"], recentEvents.length > 0 ? recentEvents.length : 0);
  const triggeredToday = readNumber(source, ["triggered_today", "triggeredToday", "hits_today", "hitsToday"], recentEvents.length);
  const blockedOrdersToday = readNumber(source, ["blocked_orders_today", "blockedOrdersToday", "rejected_orders_today", "rejectedOrdersToday"], 0);
  const unresolvedEvents = readNumber(source, ["unresolved_events", "unresolvedEvents", "open_events", "openEvents"], recentEvents.filter((event) => event.status.toUpperCase() !== "RESOLVED" && event.status.toUpperCase() !== "CLOSED").length);

  return {
    accountId: readOptionalString(source, ["account_id", "accountId", "broker_account_id", "brokerAccountId"]),
    activeRules,
    triggeredToday,
    blockedOrdersToday,
    unresolvedEvents,
    hardLimits: {
      maxDailyLoss: readOptionalNumber(hardLimitsSource, ["max_daily_loss", "maxDailyLoss", "daily_loss_limit", "dailyLossLimit"]),
      maxSingleOrderValue: readOptionalNumber(hardLimitsSource, ["max_single_order_value", "maxSingleOrderValue", "single_order_limit", "singleOrderLimit"]),
      maxPositionSizePercent: readOptionalNumber(hardLimitsSource, ["max_position_size_percent", "maxPositionSizePercent", "position_size_limit_percent", "positionSizeLimitPercent"]),
    },
    restrictions: {
      restrictedSymbols: readStringArray(restrictionsSource, ["restricted_symbols", "restrictedSymbols", "symbols", "symbol_blacklist", "blacklist"]),
      marketHoursOnly: readBoolean(restrictionsSource, ["market_hours_only", "marketHoursOnly", "market_only", "marketOnly"], false),
    },
    recentEvents,
    updatedAt: readOptionalString(source, ["updated_at", "updatedAt", "timestamp", "as_of", "asOf"]),
  };
}
