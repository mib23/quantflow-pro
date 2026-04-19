import { isAxiosError } from "axios";

import { httpClient } from "@/shared/api/http";
import { ApiEnvelope } from "@/shared/types/domain";

type JsonRecord = Record<string, unknown>;

export type RuntimeEnvironment = "PAPER" | "LIVE" | string;
export type RuntimeStatus =
  | "CREATED"
  | "STARTING"
  | "RUNNING"
  | "STOPPING"
  | "STOPPED"
  | "FAILED"
  | "DEGRADED"
  | string;
export type RuntimeApprovalStatus = "NOT_REQUIRED" | "PENDING" | "APPROVED" | "REJECTED" | string;

export interface RuntimeStrategyVersionOption {
  id: string;
  strategyId: string;
  versionNumber: number | null;
  label: string;
  parameterTemplate: Record<string, unknown>;
  createdAt: string | null;
}

export interface RuntimeStrategyOption {
  id: string;
  name: string;
  status: string;
  latestVersionId: string | null;
  defaultVersionId: string | null;
  defaultParameters: Record<string, unknown>;
}

export interface RuntimeStrategyDetail extends RuntimeStrategyOption {
  versions: RuntimeStrategyVersionOption[];
}

export interface RuntimeBrokerAccountOption {
  id: string;
  broker: string;
  brokerAccountNo: string | null;
  externalAccountId: string | null;
  environment: string;
  status: string;
  equity: number;
  cash: number;
  buyingPower: number;
  dayPnl: number;
  dayPnlPercent: number;
}

export interface RuntimeApproval {
  decision: RuntimeApprovalStatus;
  requestedBy: string | null;
  reviewedBy: string | null;
  note: string | null;
  requestedAt: string | null;
  decidedAt: string | null;
}

export interface RuntimeLogEntry {
  id: string;
  level: string;
  source: string;
  message: string;
  createdAt: string | null;
  context: Record<string, unknown>;
}

export interface RuntimeAlert {
  id: string;
  severity: string;
  type: string;
  status: string;
  message: string;
  recommendation: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface RuntimeRelatedOrder {
  id: string;
  clientOrderId: string;
  symbol: string;
  side: string;
  quantity: number;
  status: string;
  submittedAt: string | null;
  brokerAccountId: string | null;
  runtimeInstanceId: string | null;
}

export interface RuntimeRelatedRiskEvent {
  id: string;
  severity: string;
  status: string;
  message: string;
  reasonCode: string | null;
  ruleId: string | null;
  clientOrderId: string | null;
  brokerAccountId: string | null;
  runtimeInstanceId: string | null;
  occurredAt: string | null;
}

export interface RuntimeInstance {
  id: string;
  strategyId: string;
  strategyName: string;
  strategyVersionId: string;
  strategyVersionLabel: string;
  brokerAccountId: string;
  brokerAccountLabel: string;
  environment: RuntimeEnvironment;
  status: RuntimeStatus;
  approvalStatus: RuntimeApprovalStatus;
  submittedBy: string | null;
  submittedAt: string | null;
  startedAt: string | null;
  stoppedAt: string | null;
  lastHeartbeatAt: string | null;
  heartbeatTimeoutSeconds: number | null;
  restartCount: number;
  brokerFailureCount: number;
  errorSummary: string | null;
  deploymentNotes: string | null;
  parametersSnapshot: Record<string, unknown>;
  approval: RuntimeApproval | null;
  logs: RuntimeLogEntry[];
  alerts: RuntimeAlert[];
}

export interface RuntimeInstanceDetail {
  instance: RuntimeInstance;
  logs: RuntimeLogEntry[];
  alerts: RuntimeAlert[];
  relatedOrders: RuntimeRelatedOrder[];
  relatedRiskEvents: RuntimeRelatedRiskEvent[];
}

export interface CreateRuntimeInstanceInput {
  strategyId: string;
  strategyVersionId: string;
  environment: RuntimeEnvironment;
  brokerAccountId: string;
  parametersSnapshot: Record<string, unknown>;
  deploymentNotes?: string | null;
}

export interface RuntimeApprovalActionInput {
  note?: string | null;
}

function asRecord(value: unknown): JsonRecord | null {
  return typeof value === "object" && value !== null ? (value as JsonRecord) : null;
}

function firstValue(source: JsonRecord, keys: string[]): unknown {
  for (const key of keys) {
    if (!(key in source)) {
      continue;
    }

    const value = source[key];

    if (value !== undefined && value !== null) {
      return value;
    }
  }

  return undefined;
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

function readOptionalString(source: JsonRecord, keys: string[]): string | null {
  const value = firstValue(source, keys);

  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function readNumber(source: JsonRecord, keys: string[], fallback = 0): number {
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

function readOptionalNumber(source: JsonRecord, keys: string[]): number | null {
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

function readObject(source: JsonRecord, keys: string[]): JsonRecord | null {
  return asRecord(firstValue(source, keys));
}

function readArray(source: JsonRecord, keys: string[]): unknown[] {
  const value = firstValue(source, keys);
  return Array.isArray(value) ? value : [];
}

function readObjectMap(source: JsonRecord, keys: string[]): Record<string, unknown> {
  const value = firstValue(source, keys);
  return asRecord(value) ?? {};
}

function unwrapEnvelope<T>(payload: ApiEnvelope<T> | T): T {
  const source = asRecord(payload);

  if (source && "data" in source && "error" in source) {
    return (source.data as T) ?? ({} as T);
  }

  return payload as T;
}

function normalizeEnvironment(value: string): RuntimeEnvironment {
  const normalized = value.trim().toUpperCase();
  return normalized.length > 0 ? normalized : "PAPER";
}

function normalizeRuntimeStatus(value: string): RuntimeStatus {
  const normalized = value.trim().toUpperCase();
  return normalized.length > 0 ? normalized : "CREATED";
}

function normalizeApprovalStatus(value: string): RuntimeApprovalStatus {
  const normalized = value.trim().toUpperCase();

  if (normalized === "APPROVE") {
    return "APPROVED";
  }

  if (normalized === "DENIED") {
    return "REJECTED";
  }

  return normalized.length > 0 ? normalized : "NOT_REQUIRED";
}

function normalizeStrategyVersion(input: unknown): RuntimeStrategyVersionOption {
  const source = asRecord(input) ?? {};
  const strategyId = readString(source, ["strategy_id", "strategyId"]);
  const versionNumber = readOptionalNumber(source, ["version_number", "versionNumber", "version"]);
  const label =
    readString(source, ["version_tag", "versionTag", "label", "name"], "") || (versionNumber !== null ? `v${versionNumber}` : "N/A");

  return {
    id: readString(source, ["id", "version_id", "versionId"], `version-${Date.now()}`),
    strategyId,
    versionNumber,
    label,
    parameterTemplate: readObjectMap(source, ["parameter_template", "parameterTemplate", "parameters_snapshot", "parametersSnapshot", "parameters"]),
    createdAt: readOptionalString(source, ["created_at", "createdAt"]),
  };
}

function normalizeStrategyOption(input: unknown): RuntimeStrategyOption {
  const source = asRecord(input) ?? {};

  return {
    id: readString(source, ["id", "strategy_id", "strategyId"], `strategy-${Date.now()}`),
    name: readString(source, ["name", "strategy_name", "strategyName"], "Unnamed strategy"),
    status: readString(source, ["status"], "DRAFT"),
    latestVersionId: readOptionalString(source, ["latest_version_id", "latestVersionId"]),
    defaultVersionId: readOptionalString(source, ["default_version_id", "defaultVersionId"]),
    defaultParameters: readObjectMap(source, ["default_parameters", "defaultParameters"]),
  };
}

function normalizeStrategyCollection(payload: unknown): RuntimeStrategyOption[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "strategies", "data", "records", "results"])
        : [];

  return items
    .map((item) => normalizeStrategyOption(item))
    .filter((item) => item.id.trim().length > 0);
}

function normalizeStrategyDetail(payload: unknown): RuntimeStrategyDetail {
  const source = asRecord(payload) ?? {};
  const strategySource = readObject(source, ["strategy", "item", "record", "data"]) ?? source;
  const base = normalizeStrategyOption(strategySource);
  const versions =
    readArray(source, ["versions", "strategy_versions", "strategyVersions"])
      .map((item) => normalizeStrategyVersion(item))
      .filter((item) => item.id.trim().length > 0) ?? [];

  return {
    ...base,
    versions,
  };
}

function normalizeBrokerAccount(input: unknown): RuntimeBrokerAccountOption {
  const source = asRecord(input) ?? {};

  return {
    id: readString(source, ["id", "broker_account_id", "brokerAccountId"], `account-${Date.now()}`),
    broker: readString(source, ["broker", "broker_name", "brokerName"], "UNKNOWN"),
    brokerAccountNo: readOptionalString(source, ["broker_account_no", "brokerAccountNo"]),
    externalAccountId: readOptionalString(source, ["external_account_id", "externalAccountId"]),
    environment: readString(source, ["environment", "env"], "paper"),
    status: readString(source, ["status"], "UNKNOWN"),
    equity: readNumber(source, ["equity"], 0),
    cash: readNumber(source, ["cash"], 0),
    buyingPower: readNumber(source, ["buying_power", "buyingPower"], 0),
    dayPnl: readNumber(source, ["day_pnl", "dayPnl"], 0),
    dayPnlPercent: readNumber(source, ["day_pnl_percent", "dayPnlPercent"], 0),
  };
}

function normalizeBrokerAccountCollection(payload: unknown): RuntimeBrokerAccountOption[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "accounts", "broker_accounts", "brokerAccounts", "data"])
        : [];

  return items
    .map((item) => normalizeBrokerAccount(item))
    .filter((item) => item.id.trim().length > 0);
}

function normalizeRuntimeApproval(input: unknown): RuntimeApproval | null {
  const source = asRecord(input);

  if (!source) {
    return null;
  }

  return {
    decision: normalizeApprovalStatus(readString(source, ["decision", "status", "approval_status", "approvalStatus"], "NOT_REQUIRED")),
    requestedBy: readOptionalString(source, ["requested_by", "requestedBy", "applicant"]),
    reviewedBy: readOptionalString(source, ["reviewed_by", "reviewedBy", "reviewer"]),
    note: readOptionalString(source, ["note", "notes", "remark", "remarks"]),
    requestedAt: readOptionalString(source, ["requested_at", "requestedAt", "created_at", "createdAt"]),
    decidedAt: readOptionalString(source, ["decided_at", "decidedAt", "reviewed_at", "reviewedAt"]),
  };
}

function normalizeRuntimeLogEntry(input: unknown): RuntimeLogEntry {
  const source = asRecord(input) ?? {};

  return {
    id: readString(source, ["id", "log_id", "logId"], `log-${Date.now()}`),
    level: readString(source, ["level"], "INFO").toUpperCase(),
    source: readString(source, ["source", "channel"], "runtime"),
    message: readString(source, ["message", "detail"], ""),
    createdAt: readOptionalString(source, ["created_at", "createdAt", "timestamp", "occurred_at", "occurredAt"]),
    context: readObjectMap(source, ["context", "payload", "details"]),
  };
}

function normalizeRuntimeLogCollection(payload: unknown): RuntimeLogEntry[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "logs", "runtime_logs", "runtimeLogs", "data", "records", "results", "recent_logs", "recentLogs"])
        : [];

  return items
    .map((item) => normalizeRuntimeLogEntry(item))
    .filter((item) => item.id.trim().length > 0);
}

function normalizeRuntimeAlert(input: unknown): RuntimeAlert {
  const source = asRecord(input) ?? {};

  return {
    id: readString(source, ["id", "alert_id", "alertId"], `alert-${Date.now()}`),
    severity: readString(source, ["severity", "level"], "INFO").toUpperCase(),
    type: readString(source, ["alert_type", "alertType", "type"], "RUNTIME"),
    status: readString(source, ["status"], "OPEN"),
    message: readString(source, ["message", "detail"], ""),
    recommendation: readOptionalString(source, ["recommendation", "suggestion"]),
    createdAt: readOptionalString(source, ["created_at", "createdAt", "timestamp", "occurred_at", "occurredAt"]),
    updatedAt: readOptionalString(source, ["updated_at", "updatedAt"]),
  };
}

function normalizeRuntimeAlertCollection(payload: unknown): RuntimeAlert[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "alerts", "runtime_alerts", "runtimeAlerts", "recent_alerts", "recentAlerts", "data"])
        : [];

  return items
    .map((item) => normalizeRuntimeAlert(item))
    .filter((item) => item.id.trim().length > 0);
}

function normalizeRuntimeRelatedOrder(input: unknown): RuntimeRelatedOrder {
  const source = asRecord(input) ?? {};

  return {
    id: readString(source, ["id", "order_id", "orderId", "client_order_id", "clientOrderId"], `order-${Date.now()}`),
    clientOrderId: readString(source, ["client_order_id", "clientOrderId", "id"], ""),
    symbol: readString(source, ["symbol", "ticker"], "N/A").toUpperCase(),
    side: readString(source, ["side"], "BUY").toUpperCase(),
    quantity: readNumber(source, ["quantity", "filled_quantity", "filledQuantity"], 0),
    status: readString(source, ["status"], "UNKNOWN").toUpperCase(),
    submittedAt: readOptionalString(source, ["submitted_at", "submittedAt", "created_at", "createdAt", "updated_at", "updatedAt"]),
    brokerAccountId: readOptionalString(source, ["broker_account_id", "brokerAccountId"]),
    runtimeInstanceId: readOptionalString(source, ["runtime_instance_id", "runtimeInstanceId"]),
  };
}

function normalizeRuntimeRelatedOrderCollection(payload: unknown): RuntimeRelatedOrder[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "orders", "recent_orders", "recentOrders", "data", "records", "results"])
        : [];

  return items
    .map((item) => normalizeRuntimeRelatedOrder(item))
    .filter((item) => item.id.trim().length > 0);
}

function normalizeRuntimeRelatedRiskEvent(input: unknown): RuntimeRelatedRiskEvent {
  const source = asRecord(input) ?? {};

  return {
    id: readString(source, ["id", "event_id", "eventId"], `risk-${Date.now()}`),
    severity: readString(source, ["severity", "level"], "INFO").toUpperCase(),
    status: readString(source, ["status"], "UNKNOWN").toUpperCase(),
    message: readString(source, ["message", "reason", "detail"], "Risk event"),
    reasonCode: readOptionalString(source, ["reason_code", "reasonCode", "code"]),
    ruleId: readOptionalString(source, ["rule_id", "ruleId", "risk_rule_id", "riskRuleId"]),
    clientOrderId: readOptionalString(source, ["client_order_id", "clientOrderId"]),
    brokerAccountId: readOptionalString(source, ["broker_account_id", "brokerAccountId", "account_id", "accountId"]),
    runtimeInstanceId: readOptionalString(source, ["runtime_instance_id", "runtimeInstanceId"]),
    occurredAt: readOptionalString(source, ["occurred_at", "occurredAt", "created_at", "createdAt", "timestamp"]),
  };
}

function normalizeRuntimeRelatedRiskEventCollection(payload: unknown): RuntimeRelatedRiskEvent[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "events", "risk_events", "riskEvents", "recent_risk_events", "recentRiskEvents", "data"])
        : [];

  return items
    .map((item) => normalizeRuntimeRelatedRiskEvent(item))
    .filter((item) => item.id.trim().length > 0);
}

function normalizeRuntimeInstance(input: unknown): RuntimeInstance {
  const source = asRecord(input) ?? {};
  const strategySource = readObject(source, ["strategy", "strategy_info", "strategyInfo"]) ?? {};
  const versionSource = readObject(source, ["strategy_version", "strategyVersion", "version"]) ?? {};
  const accountSource = readObject(source, ["broker_account", "brokerAccount", "account"]) ?? {};
  const approvalSource =
    readObject(source, ["approval", "deployment_approval", "deploymentApproval"]) ??
    readObject(source, ["approval_info", "approvalInfo"]) ??
    null;

  const rawApprovalStatus =
    readString(source, ["approval_status", "approvalStatus"], "") ||
    readString(approvalSource ?? {}, ["decision", "status"], "NOT_REQUIRED");

  const versionNumber = readOptionalNumber(versionSource, ["version_number", "versionNumber", "version"]);
  const strategyVersionLabel =
    readString(source, ["strategy_version_label", "strategyVersionLabel"], "") ||
    (versionNumber !== null ? `v${versionNumber}` : "");

  const embeddedLogs = normalizeRuntimeLogCollection(
    firstValue(source, ["logs", "runtime_logs", "runtimeLogs", "recent_logs", "recentLogs"]) ?? [],
  );
  const embeddedAlerts = normalizeRuntimeAlertCollection(
    firstValue(source, ["alerts", "runtime_alerts", "runtimeAlerts", "recent_alerts", "recentAlerts"]) ?? [],
  );

  return {
    id: readString(source, ["id", "instance_id", "instanceId", "runtime_instance_id", "runtimeInstanceId"], `runtime-${Date.now()}`),
    strategyId: readString(source, ["strategy_id", "strategyId"], readString(strategySource, ["id", "strategy_id", "strategyId"])),
    strategyName:
      readString(source, ["strategy_name", "strategyName"], "") ||
      readString(strategySource, ["name", "strategy_name", "strategyName"], "Unknown strategy"),
    strategyVersionId: readString(
      source,
      ["strategy_version_id", "strategyVersionId"],
      readString(versionSource, ["id", "strategy_version_id", "strategyVersionId"]),
    ),
    strategyVersionLabel: strategyVersionLabel || "N/A",
    brokerAccountId: readString(
      source,
      ["broker_account_id", "brokerAccountId"],
      readString(accountSource, ["id", "broker_account_id", "brokerAccountId"]),
    ),
    brokerAccountLabel:
      readString(source, ["broker_account_label", "brokerAccountLabel"], "") ||
      readString(accountSource, ["broker_account_no", "brokerAccountNo", "id"], "N/A"),
    environment: normalizeEnvironment(readString(source, ["environment", "env"], "paper")),
    status: normalizeRuntimeStatus(readString(source, ["status", "state"], "CREATED")),
    approvalStatus: normalizeApprovalStatus(rawApprovalStatus),
    submittedBy: readOptionalString(source, ["submitted_by", "submittedBy", "created_by", "createdBy"]),
    submittedAt: readOptionalString(source, ["submitted_at", "submittedAt", "created_at", "createdAt"]),
    startedAt: readOptionalString(source, ["started_at", "startedAt"]),
    stoppedAt: readOptionalString(source, ["stopped_at", "stoppedAt"]),
    lastHeartbeatAt: readOptionalString(source, ["last_heartbeat_at", "lastHeartbeatAt", "heartbeat_at", "heartbeatAt"]),
    heartbeatTimeoutSeconds: readOptionalNumber(source, ["heartbeat_timeout_seconds", "heartbeatTimeoutSeconds"]),
    restartCount: readNumber(source, ["restart_count", "restartCount"], 0),
    brokerFailureCount: readNumber(source, ["broker_failure_count", "brokerFailureCount"], 0),
    errorSummary: readOptionalString(source, ["error_summary", "errorSummary", "failure_message", "failureMessage"]),
    deploymentNotes: readOptionalString(source, ["deployment_notes", "deploymentNotes", "notes", "note"]),
    parametersSnapshot: readObjectMap(source, ["parameters_snapshot", "parametersSnapshot"]),
    approval: normalizeRuntimeApproval(approvalSource),
    logs: embeddedLogs,
    alerts: embeddedAlerts,
  };
}

function normalizeRuntimeInstanceCollection(payload: unknown): RuntimeInstance[] {
  const source = asRecord(payload);
  const items =
    Array.isArray(payload)
      ? payload
      : source
        ? readArray(source, ["items", "instances", "runtime_instances", "runtimeInstances", "data", "records", "results"])
        : [];

  return items
    .map((item) => normalizeRuntimeInstance(item))
    .filter((item) => item.id.trim().length > 0);
}

function normalizeRuntimeInstanceDetail(payload: unknown): RuntimeInstanceDetail {
  const source = asRecord(payload) ?? {};
  const instanceSource = readObject(source, ["instance", "runtime_instance", "runtimeInstance", "item", "record"]) ?? source;

  const instance = normalizeRuntimeInstance(instanceSource);
  const logs = normalizeRuntimeLogCollection(
    firstValue(source, ["logs", "runtime_logs", "runtimeLogs", "recent_logs", "recentLogs"]) ??
      firstValue(instanceSource, ["logs", "runtime_logs", "runtimeLogs", "recent_logs", "recentLogs"]) ??
      [],
  );
  const alerts = normalizeRuntimeAlertCollection(
    firstValue(source, ["alerts", "runtime_alerts", "runtimeAlerts", "recent_alerts", "recentAlerts"]) ??
      firstValue(instanceSource, ["alerts", "runtime_alerts", "runtimeAlerts", "recent_alerts", "recentAlerts"]) ??
      [],
  );
  const relatedOrders = normalizeRuntimeRelatedOrderCollection(
    firstValue(source, ["related_orders", "relatedOrders", "recent_orders", "recentOrders", "orders"]) ??
      firstValue(instanceSource, ["related_orders", "relatedOrders", "recent_orders", "recentOrders", "orders"]) ??
      [],
  );
  const relatedRiskEvents = normalizeRuntimeRelatedRiskEventCollection(
    firstValue(source, ["related_risk_events", "relatedRiskEvents", "recent_risk_events", "recentRiskEvents", "risk_events", "riskEvents"]) ??
      firstValue(instanceSource, ["related_risk_events", "relatedRiskEvents", "recent_risk_events", "recentRiskEvents", "risk_events", "riskEvents"]) ??
      [],
  );

  return {
    instance: {
      ...instance,
      logs: logs.length > 0 ? logs : instance.logs,
      alerts: alerts.length > 0 ? alerts : instance.alerts,
    },
    logs: logs.length > 0 ? logs : instance.logs,
    alerts: alerts.length > 0 ? alerts : instance.alerts,
    relatedOrders,
    relatedRiskEvents,
  };
}

function sortByTimestampDesc<T>(items: T[], extractor: (item: T) => string | null): T[] {
  return [...items].sort((left, right) => {
    const leftTime = extractor(left) ? Date.parse(extractor(left) as string) : 0;
    const rightTime = extractor(right) ? Date.parse(extractor(right) as string) : 0;
    return rightTime - leftTime;
  });
}

function matchesRuntimeOrder(order: RuntimeRelatedOrder, instance: RuntimeInstance): boolean {
  if (order.runtimeInstanceId && order.runtimeInstanceId === instance.id) {
    return true;
  }

  if (order.brokerAccountId && instance.brokerAccountId && order.brokerAccountId === instance.brokerAccountId) {
    return true;
  }

  return false;
}

function matchesRuntimeRiskEvent(event: RuntimeRelatedRiskEvent, instance: RuntimeInstance): boolean {
  if (event.runtimeInstanceId && event.runtimeInstanceId === instance.id) {
    return true;
  }

  if (event.brokerAccountId && instance.brokerAccountId && event.brokerAccountId === instance.brokerAccountId) {
    return true;
  }

  return false;
}

function isNotFoundError(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 404;
}

export async function getRuntimeStrategyOptions(): Promise<RuntimeStrategyOption[]> {
  const response = await httpClient.get<ApiEnvelope<unknown>>("/strategies", {
    params: { page: 1, page_size: 200 },
  });

  return normalizeStrategyCollection(unwrapEnvelope(response.data));
}

export async function getRuntimeStrategyDetail(strategyId: string): Promise<RuntimeStrategyDetail> {
  const response = await httpClient.get<ApiEnvelope<unknown>>(`/strategies/${encodeURIComponent(strategyId)}`);
  return normalizeStrategyDetail(unwrapEnvelope(response.data));
}

export async function getRuntimeBrokerAccountOptions(): Promise<RuntimeBrokerAccountOption[]> {
  const response = await httpClient.get<ApiEnvelope<unknown>>("/accounts/broker-accounts");
  return normalizeBrokerAccountCollection(unwrapEnvelope(response.data));
}

export async function getRuntimeInstances(): Promise<RuntimeInstance[]> {
  const response = await httpClient.get<ApiEnvelope<unknown>>("/runtime/instances", {
    params: { page: 1, page_size: 200 },
  });

  return normalizeRuntimeInstanceCollection(unwrapEnvelope(response.data));
}

export async function getRuntimeInstanceDetail(instanceId: string): Promise<RuntimeInstanceDetail> {
  const response = await httpClient.get<ApiEnvelope<unknown>>(`/runtime/instances/${encodeURIComponent(instanceId)}`);
  return normalizeRuntimeInstanceDetail(unwrapEnvelope(response.data));
}

export async function getRuntimeInstanceLogs(instanceId: string): Promise<RuntimeLogEntry[]> {
  try {
    const response = await httpClient.get<ApiEnvelope<unknown>>(`/runtime/instances/${encodeURIComponent(instanceId)}/logs`, {
      params: { page: 1, page_size: 100 },
    });

    return normalizeRuntimeLogCollection(unwrapEnvelope(response.data));
  } catch (error) {
    if (isNotFoundError(error)) {
      return [];
    }

    throw error;
  }
}

export async function createRuntimeInstance(input: CreateRuntimeInstanceInput): Promise<RuntimeInstance> {
  const response = await httpClient.post<ApiEnvelope<unknown>>("/runtime/instances", {
    strategy_id: input.strategyId,
    strategy_version_id: input.strategyVersionId,
    broker_account_id: input.brokerAccountId,
    environment: normalizeEnvironment(input.environment),
    parameters_snapshot: input.parametersSnapshot,
    deployment_notes: input.deploymentNotes ?? null,
  });

  const detail = normalizeRuntimeInstanceDetail(unwrapEnvelope(response.data));
  return detail.instance;
}

export async function startRuntimeInstance(instanceId: string): Promise<RuntimeInstance | null> {
  const response = await httpClient.post<ApiEnvelope<unknown>>(`/runtime/instances/${encodeURIComponent(instanceId)}/start`);
  const payload = unwrapEnvelope(response.data);
  const source = asRecord(payload);

  if (!source) {
    return null;
  }

  const candidate = readObject(source, ["instance", "runtime_instance", "runtimeInstance", "data"]) ?? source;
  return normalizeRuntimeInstance(candidate);
}

export async function stopRuntimeInstance(instanceId: string): Promise<RuntimeInstance | null> {
  const response = await httpClient.post<ApiEnvelope<unknown>>(`/runtime/instances/${encodeURIComponent(instanceId)}/stop`);
  const payload = unwrapEnvelope(response.data);
  const source = asRecord(payload);

  if (!source) {
    return null;
  }

  const candidate = readObject(source, ["instance", "runtime_instance", "runtimeInstance", "data"]) ?? source;
  return normalizeRuntimeInstance(candidate);
}

export async function restartRuntimeInstance(instanceId: string): Promise<RuntimeInstance | null> {
  const response = await httpClient.post<ApiEnvelope<unknown>>(`/runtime/instances/${encodeURIComponent(instanceId)}/restart`);
  const payload = unwrapEnvelope(response.data);
  const source = asRecord(payload);

  if (!source) {
    return null;
  }

  const candidate = readObject(source, ["instance", "runtime_instance", "runtimeInstance", "data"]) ?? source;
  return normalizeRuntimeInstance(candidate);
}

async function applyRuntimeApprovalAction(
  instanceId: string,
  path: "approve" | "reject",
  input: RuntimeApprovalActionInput = {},
): Promise<RuntimeInstance | null> {
  const response = await httpClient.post<ApiEnvelope<unknown>>(
    `/runtime/deployments/${encodeURIComponent(instanceId)}/${path}`,
    {
      note: input.note?.trim() ? input.note.trim() : null,
    },
  );
  const payload = unwrapEnvelope(response.data);
  const source = asRecord(payload);

  if (!source) {
    return null;
  }

  const candidate = readObject(source, ["instance", "runtime_instance", "runtimeInstance", "data"]) ?? source;
  return normalizeRuntimeInstance(candidate);
}

export async function approveRuntimeDeployment(
  instanceId: string,
  input: RuntimeApprovalActionInput = {},
): Promise<RuntimeInstance | null> {
  return applyRuntimeApprovalAction(instanceId, "approve", input);
}

export async function rejectRuntimeDeployment(
  instanceId: string,
  input: RuntimeApprovalActionInput = {},
): Promise<RuntimeInstance | null> {
  return applyRuntimeApprovalAction(instanceId, "reject", input);
}

export async function getRuntimeRelatedOrders(instance: RuntimeInstance): Promise<RuntimeRelatedOrder[]> {
  try {
    const response = await httpClient.get<ApiEnvelope<unknown>>("/orders", {
      params: { page: 1, page_size: 200 },
    });
    const orders = normalizeRuntimeRelatedOrderCollection(unwrapEnvelope(response.data));
    const exactMatches = orders.filter((order) => order.runtimeInstanceId === instance.id);
    const fallbackMatches = exactMatches.length > 0 ? exactMatches : orders.filter((order) => matchesRuntimeOrder(order, instance));
    return sortByTimestampDesc(fallbackMatches, (order) => order.submittedAt).slice(0, 20);
  } catch (error) {
    if (isNotFoundError(error)) {
      return [];
    }

    throw error;
  }
}

export async function getRuntimeRelatedRiskEvents(instance: RuntimeInstance): Promise<RuntimeRelatedRiskEvent[]> {
  const params: Record<string, unknown> = { page: 1, page_size: 200 };

  if (instance.brokerAccountId) {
    params.broker_account_id = instance.brokerAccountId;
  }

  try {
    const response = await httpClient.get<ApiEnvelope<unknown>>("/risk/events", { params });
    const events = normalizeRuntimeRelatedRiskEventCollection(unwrapEnvelope(response.data));
    const exactMatches = events.filter((event) => event.runtimeInstanceId === instance.id);
    const fallbackMatches = exactMatches.length > 0 ? exactMatches : events.filter((event) => matchesRuntimeRiskEvent(event, instance));
    return sortByTimestampDesc(fallbackMatches, (event) => event.occurredAt).slice(0, 20);
  } catch (error) {
    if (isNotFoundError(error)) {
      return [];
    }

    throw error;
  }
}
