import { FormEvent, useEffect, useMemo, useState } from "react";

import { useSessionStore } from "@/entities/user/store";
import {
  useApproveRuntimeDeploymentMutation,
  useCreateRuntimeInstanceMutation,
  useRejectRuntimeDeploymentMutation,
  useRestartRuntimeInstanceMutation,
  useRuntimeBrokerAccountsQuery,
  useRuntimeInstanceDetailQuery,
  useRuntimeInstanceLogsQuery,
  useRuntimeInstancesQuery,
  useRuntimeRelatedOrdersQuery,
  useRuntimeRelatedRiskEventsQuery,
  useRuntimeStrategyDetailQuery,
  useRuntimeStrategyOptionsQuery,
  useStartRuntimeInstanceMutation,
  useStopRuntimeInstanceMutation,
} from "@/features/strategy/hooks/useStrategyRuntimeWorkspace";
import { formatNumber } from "@/shared/lib/format";
import { DataState } from "@/shared/ui/DataState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionCard } from "@/shared/ui/SectionCard";

type RuntimeAction = "start" | "stop" | "restart";

const runtimeEnvironmentOptions = [
  { value: "PAPER", label: "Paper" },
  { value: "LIVE", label: "Live" },
] as const;

export function StrategyPage() {
  const strategiesQuery = useRuntimeStrategyOptionsQuery();
  const brokerAccountsQuery = useRuntimeBrokerAccountsQuery();
  const runtimeInstancesQuery = useRuntimeInstancesQuery();

  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [selectedEnvironment, setSelectedEnvironment] = useState<(typeof runtimeEnvironmentOptions)[number]["value"]>("PAPER");
  const [selectedBrokerAccountId, setSelectedBrokerAccountId] = useState<string | null>(null);
  const [parameterSnapshotText, setParameterSnapshotText] = useState("{}");
  const [deploymentNotes, setDeploymentNotes] = useState("");
  const [deploymentError, setDeploymentError] = useState<string | null>(null);
  const [selectedInstanceId, setSelectedInstanceId] = useState<string | null>(null);
  const [approvalNote, setApprovalNote] = useState("");

  const strategyDetailQuery = useRuntimeStrategyDetailQuery(selectedStrategyId);
  const strategyVersions = strategyDetailQuery.data?.versions ?? [];
  const sessionUser = useSessionStore((state) => state.user);

  useEffect(() => {
    const strategies = strategiesQuery.data ?? [];

    if (!strategies.length) {
      setSelectedStrategyId(null);
      return;
    }

    if (!selectedStrategyId || !strategies.some((item) => item.id === selectedStrategyId)) {
      setSelectedStrategyId(strategies[0].id);
    }
  }, [selectedStrategyId, strategiesQuery.data]);

  useEffect(() => {
    if (!strategyDetailQuery.data) {
      return;
    }

    if (!strategyVersions.length) {
      setSelectedVersionId(null);
      setParameterSnapshotText("{}");
      return;
    }

    const preferredVersionId =
      strategyDetailQuery.data.defaultVersionId ?? strategyDetailQuery.data.latestVersionId ?? strategyVersions[0].id;
    const hasCurrentVersion = selectedVersionId ? strategyVersions.some((version) => version.id === selectedVersionId) : false;
    const nextVersionId = hasCurrentVersion ? selectedVersionId : preferredVersionId;
    const nextVersion = strategyVersions.find((version) => version.id === nextVersionId) ?? strategyVersions[0];

    setSelectedVersionId(nextVersion.id);
    setParameterSnapshotText(stringifyJson(nextVersion.parameterTemplate, strategyDetailQuery.data.defaultParameters));
  }, [selectedVersionId, strategyDetailQuery.data, strategyVersions]);

  useEffect(() => {
    const accounts = brokerAccountsQuery.data ?? [];

    if (!accounts.length) {
      setSelectedBrokerAccountId(null);
      return;
    }

    const hasCurrentSelection = selectedBrokerAccountId ? accounts.some((item) => item.id === selectedBrokerAccountId) : false;

    if (hasCurrentSelection) {
      return;
    }

    const matchedByEnvironment =
      accounts.find((item) => item.environment.trim().toUpperCase() === selectedEnvironment) ?? accounts[0];
    setSelectedBrokerAccountId(matchedByEnvironment.id);
  }, [brokerAccountsQuery.data, selectedBrokerAccountId, selectedEnvironment]);

  useEffect(() => {
    const instances = runtimeInstancesQuery.data ?? [];

    if (!instances.length) {
      setSelectedInstanceId(null);
      return;
    }

    if (!selectedInstanceId || !instances.some((item) => item.id === selectedInstanceId)) {
      setSelectedInstanceId(instances[0].id);
    }
  }, [runtimeInstancesQuery.data, selectedInstanceId]);

  const selectedInstanceFromList = useMemo(
    () => runtimeInstancesQuery.data?.find((instance) => instance.id === selectedInstanceId) ?? null,
    [runtimeInstancesQuery.data, selectedInstanceId],
  );

  const runtimeInstanceDetailQuery = useRuntimeInstanceDetailQuery(selectedInstanceId);
  const activeInstance = runtimeInstanceDetailQuery.data?.instance ?? selectedInstanceFromList ?? null;
  const runtimeLogsQuery = useRuntimeInstanceLogsQuery(selectedInstanceId);
  const relatedOrdersQuery = useRuntimeRelatedOrdersQuery(activeInstance);
  const relatedRiskEventsQuery = useRuntimeRelatedRiskEventsQuery(activeInstance);

  const createRuntimeInstanceMutation = useCreateRuntimeInstanceMutation();
  const startRuntimeMutation = useStartRuntimeInstanceMutation();
  const stopRuntimeMutation = useStopRuntimeInstanceMutation();
  const restartRuntimeMutation = useRestartRuntimeInstanceMutation();
  const approveRuntimeMutation = useApproveRuntimeDeploymentMutation();
  const rejectRuntimeMutation = useRejectRuntimeDeploymentMutation();

  const actionInFlight =
    startRuntimeMutation.isPending ||
    stopRuntimeMutation.isPending ||
    restartRuntimeMutation.isPending ||
    approveRuntimeMutation.isPending ||
    rejectRuntimeMutation.isPending;

  const runtimeStatus = (activeInstance?.status ?? "").toUpperCase();
  const runtimeApprovalStatus = (activeInstance?.approvalStatus ?? activeInstance?.approval?.decision ?? "NOT_REQUIRED").toUpperCase();
  const isLiveRuntime = (activeInstance?.environment ?? "").toUpperCase() === "LIVE";
  const liveApprovalPassed = runtimeApprovalStatus === "APPROVED" || runtimeApprovalStatus === "NOT_REQUIRED";
  const isAdminUser = sessionUser?.role === "ADMIN";

  const canStart =
    Boolean(activeInstance) &&
    ["CREATED", "STOPPED", "FAILED", "DEGRADED"].includes(runtimeStatus) &&
    (!isLiveRuntime || liveApprovalPassed);
  const canStop = Boolean(activeInstance) && ["RUNNING", "STARTING", "DEGRADED"].includes(runtimeStatus);
  const canRestart = Boolean(activeInstance) && ["RUNNING", "FAILED", "DEGRADED", "STOPPED"].includes(runtimeStatus);
  const canReviewLiveApproval = Boolean(activeInstance) && isLiveRuntime && runtimeApprovalStatus === "PENDING" && isAdminUser;

  const actionError = resolveErrorMessage(
    startRuntimeMutation.error ??
      stopRuntimeMutation.error ??
      restartRuntimeMutation.error ??
      approveRuntimeMutation.error ??
      rejectRuntimeMutation.error,
  );

  const runtimeLogs = useMemo(() => {
    if (runtimeLogsQuery.data?.length) {
      return runtimeLogsQuery.data;
    }

    if (runtimeInstanceDetailQuery.data?.logs.length) {
      return runtimeInstanceDetailQuery.data.logs;
    }

    return activeInstance?.logs ?? [];
  }, [activeInstance, runtimeInstanceDetailQuery.data?.logs, runtimeLogsQuery.data]);

  const runtimeAlerts = useMemo(() => {
    if (runtimeInstanceDetailQuery.data?.alerts.length) {
      return runtimeInstanceDetailQuery.data.alerts;
    }

    return activeInstance?.alerts ?? [];
  }, [activeInstance?.alerts, runtimeInstanceDetailQuery.data?.alerts]);

  const relatedOrders = useMemo(() => {
    if (runtimeInstanceDetailQuery.data?.relatedOrders.length) {
      return runtimeInstanceDetailQuery.data.relatedOrders;
    }

    return relatedOrdersQuery.data ?? [];
  }, [relatedOrdersQuery.data, runtimeInstanceDetailQuery.data?.relatedOrders]);

  const relatedRiskEvents = useMemo(() => {
    if (runtimeInstanceDetailQuery.data?.relatedRiskEvents.length) {
      return runtimeInstanceDetailQuery.data.relatedRiskEvents;
    }

    return relatedRiskEventsQuery.data ?? [];
  }, [relatedRiskEventsQuery.data, runtimeInstanceDetailQuery.data?.relatedRiskEvents]);

  const isDeployDisabled =
    createRuntimeInstanceMutation.isPending || !selectedStrategyId || !selectedVersionId || !selectedBrokerAccountId;

  const handleVersionChange = (versionId: string) => {
    setSelectedVersionId(versionId);
    const version = strategyVersions.find((item) => item.id === versionId);
    setParameterSnapshotText(stringifyJson(version?.parameterTemplate ?? {}, strategyDetailQuery.data?.defaultParameters ?? {}));
  };

  const handleCreateRuntime = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setDeploymentError(null);

    if (!selectedStrategyId || !selectedVersionId || !selectedBrokerAccountId) {
      setDeploymentError("Please choose strategy, version, and broker account first.");
      return;
    }

    let parsedSnapshot: Record<string, unknown> = {};
    const trimmedSnapshot = parameterSnapshotText.trim();

    if (trimmedSnapshot.length > 0) {
      try {
        const parsed = JSON.parse(trimmedSnapshot) as unknown;

        if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
          setDeploymentError("Parameter snapshot must be a JSON object.");
          return;
        }

        parsedSnapshot = parsed as Record<string, unknown>;
      } catch {
        setDeploymentError("Parameter snapshot is not valid JSON.");
        return;
      }
    }

    createRuntimeInstanceMutation.mutate(
      {
        strategyId: selectedStrategyId,
        strategyVersionId: selectedVersionId,
        environment: selectedEnvironment,
        brokerAccountId: selectedBrokerAccountId,
        parametersSnapshot: parsedSnapshot,
        deploymentNotes: deploymentNotes.trim().length > 0 ? deploymentNotes.trim() : null,
      },
      {
        onSuccess: (instance) => {
          setSelectedInstanceId(instance.id);
          setDeploymentNotes("");
          setDeploymentError(null);
        },
        onError: (error) => {
          setDeploymentError(resolveErrorMessage(error) ?? "Failed to create runtime instance.");
        },
      },
    );
  };

  const runRuntimeAction = (action: RuntimeAction) => {
    if (!activeInstance || actionInFlight) {
      return;
    }

    const actionConfig =
      action === "start"
        ? {
            allowed: canStart,
            confirmText: `Start runtime ${activeInstance.id}?`,
            run: () => startRuntimeMutation.mutate({ instanceId: activeInstance.id }),
          }
        : action === "stop"
          ? {
              allowed: canStop,
              confirmText: `Stop runtime ${activeInstance.id}?`,
              run: () => stopRuntimeMutation.mutate({ instanceId: activeInstance.id }),
            }
          : {
              allowed: canRestart,
              confirmText: `Restart runtime ${activeInstance.id}?`,
              run: () => restartRuntimeMutation.mutate({ instanceId: activeInstance.id }),
            };

    if (!actionConfig.allowed) {
      return;
    }

    if (!window.confirm(actionConfig.confirmText)) {
      return;
    }

    actionConfig.run();
  };

  const reviewLiveApproval = (decision: "approve" | "reject") => {
    if (!activeInstance || !canReviewLiveApproval || actionInFlight) {
      return;
    }

    const confirmText =
      decision === "approve"
        ? `Approve live deployment ${activeInstance.id}?`
        : `Reject live deployment ${activeInstance.id}?`;

    if (!window.confirm(confirmText)) {
      return;
    }

    const mutation = decision === "approve" ? approveRuntimeMutation : rejectRuntimeMutation;
    mutation.mutate(
      {
        instanceId: activeInstance.id,
        input: { note: approvalNote },
      },
      {
        onSuccess: () => {
          setApprovalNote("");
        },
      },
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Strategy"
        title="Runtime Workspace"
        description="Deploy strategy versions to paper/live, watch runtime health and heartbeat, and manage start/stop/restart actions with approval-aware controls."
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-6">
          <SectionCard title="Deploy Runtime Instance" subtitle="Choose strategy/version/environment/account and create a runtime deployment.">
            <form onSubmit={handleCreateRuntime} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.18em] text-slate-500">Strategy</span>
                  <select
                    value={selectedStrategyId ?? ""}
                    onChange={(event) => {
                      setSelectedStrategyId(event.target.value || null);
                      setSelectedVersionId(null);
                    }}
                    className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-500/50"
                  >
                    <option value="" disabled>
                      Select strategy
                    </option>
                    {(strategiesQuery.data ?? []).map((strategy) => (
                      <option key={strategy.id} value={strategy.id}>
                        {strategy.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.18em] text-slate-500">Version</span>
                  <select
                    value={selectedVersionId ?? ""}
                    onChange={(event) => handleVersionChange(event.target.value)}
                    disabled={!strategyVersions.length}
                    className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-500/50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="" disabled>
                      Select version
                    </option>
                    {strategyVersions.map((version) => (
                      <option key={version.id} value={version.id}>
                        {version.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.18em] text-slate-500">Environment</span>
                  <select
                    value={selectedEnvironment}
                    onChange={(event) => setSelectedEnvironment(event.target.value as (typeof runtimeEnvironmentOptions)[number]["value"])}
                    className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-500/50"
                  >
                    {runtimeEnvironmentOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.18em] text-slate-500">Broker Account</span>
                  <select
                    value={selectedBrokerAccountId ?? ""}
                    onChange={(event) => setSelectedBrokerAccountId(event.target.value || null)}
                    className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-500/50"
                  >
                    <option value="" disabled>
                      Select broker account
                    </option>
                    {(brokerAccountsQuery.data ?? []).map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.broker} · {account.brokerAccountNo ?? account.id} · {account.environment.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="space-y-2 text-sm text-slate-300">
                <span className="text-xs uppercase tracking-[0.18em] text-slate-500">Parameter Snapshot (JSON)</span>
                <textarea
                  rows={6}
                  value={parameterSnapshotText}
                  onChange={(event) => setParameterSnapshotText(event.target.value)}
                  className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-3 py-2 font-mono text-xs text-slate-200 outline-none transition focus:border-cyan-500/50"
                />
              </label>

              <label className="space-y-2 text-sm text-slate-300">
                <span className="text-xs uppercase tracking-[0.18em] text-slate-500">Deployment Notes</span>
                <textarea
                  rows={3}
                  value={deploymentNotes}
                  onChange={(event) => setDeploymentNotes(event.target.value)}
                  className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-3 py-2 text-sm text-slate-200 outline-none transition focus:border-cyan-500/50"
                  placeholder="Optional notes for this deployment..."
                />
              </label>

              {selectedEnvironment === "LIVE" ? (
                <div className="rounded-2xl border border-amber-900/40 bg-amber-950/25 px-4 py-3 text-sm text-amber-200">
                  Live runtime start is blocked until approval status is <span className="font-semibold">APPROVED</span>.
                </div>
              ) : null}

              {deploymentError ? <p className="rounded-2xl border border-rose-900/40 bg-rose-950/25 px-4 py-3 text-sm text-rose-300">{deploymentError}</p> : null}

              <button
                type="submit"
                disabled={isDeployDisabled}
                className="inline-flex items-center rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-2.5 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {createRuntimeInstanceMutation.isPending ? "Creating..." : "Create Runtime Instance"}
              </button>
            </form>
          </SectionCard>

          <SectionCard title="Runtime Instances" subtitle="Select an instance to inspect details, logs, and related events.">
            <DataState
              isLoading={runtimeInstancesQuery.isPending}
              error={resolveErrorMessage(runtimeInstancesQuery.error)}
              isEmpty={!runtimeInstancesQuery.data?.length}
              emptyTitle="No runtime instances yet."
            >
              <div className="space-y-3">
                {runtimeInstancesQuery.data?.map((instance) => (
                  <button
                    key={instance.id}
                    type="button"
                    onClick={() => setSelectedInstanceId(instance.id)}
                    className={[
                      "w-full rounded-2xl border px-4 py-4 text-left transition",
                      selectedInstanceId === instance.id
                        ? "border-cyan-500/40 bg-cyan-500/10"
                        : "border-slate-800 bg-ink-950 hover:border-slate-700 hover:bg-slate-900/70",
                    ].join(" ")}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-white">{instance.strategyName}</p>
                        <p className="mt-1 text-xs text-slate-500">{instance.id}</p>
                      </div>
                      <span className={`rounded-full border px-2.5 py-0.5 text-[11px] uppercase tracking-[0.18em] ${runtimeStatusTone(instance.status)}`}>
                        {instance.status}
                      </span>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span className="rounded-full border border-slate-800 bg-slate-950/60 px-2.5 py-1">{instance.environment}</span>
                      <span className={`rounded-full border px-2.5 py-1 ${approvalStatusTone(instance.approvalStatus)}`}>Approval: {instance.approvalStatus}</span>
                      <span>{instance.strategyVersionLabel}</span>
                    </div>

                    <p className="mt-3 text-xs text-slate-500">Heartbeat: {formatTimestamp(instance.lastHeartbeatAt)}</p>
                  </button>
                ))}
              </div>
            </DataState>
          </SectionCard>
        </div>

        <div className="space-y-6">
          <SectionCard
            title="Runtime Detail"
            subtitle="State, heartbeat, approval, and operational controls for the selected runtime instance."
            action={
              activeInstance ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={!canStart || actionInFlight}
                    onClick={() => runRuntimeAction("start")}
                    className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-200 transition disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {startRuntimeMutation.isPending ? "Starting..." : "Start"}
                  </button>
                  <button
                    type="button"
                    disabled={!canStop || actionInFlight}
                    onClick={() => runRuntimeAction("stop")}
                    className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-200 transition disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {stopRuntimeMutation.isPending ? "Stopping..." : "Stop"}
                  </button>
                  <button
                    type="button"
                    disabled={!canRestart || actionInFlight}
                    onClick={() => runRuntimeAction("restart")}
                    className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs text-cyan-200 transition disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {restartRuntimeMutation.isPending ? "Restarting..." : "Restart"}
                  </button>
                </div>
              ) : null
            }
          >
            <DataState
              isLoading={runtimeInstanceDetailQuery.isPending && !activeInstance}
              error={resolveErrorMessage(runtimeInstanceDetailQuery.error)}
              isEmpty={!activeInstance}
              emptyTitle="Select a runtime instance to view detail."
            >
              {activeInstance ? (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <InfoBlock label="Runtime ID" value={activeInstance.id} mono />
                    <InfoBlock label="Strategy" value={`${activeInstance.strategyName} · ${activeInstance.strategyVersionLabel}`} />
                    <InfoBlock label="Environment" value={activeInstance.environment} />
                    <InfoBlock label="Status" value={activeInstance.status} tone={runtimeStatusTone(activeInstance.status)} />
                    <InfoBlock label="Approval" value={activeInstance.approvalStatus} tone={approvalStatusTone(activeInstance.approvalStatus)} />
                    <InfoBlock label="Heartbeat" value={formatTimestamp(activeInstance.lastHeartbeatAt)} />
                    <InfoBlock label="Started At" value={formatTimestamp(activeInstance.startedAt)} />
                    <InfoBlock label="Stopped At" value={formatTimestamp(activeInstance.stoppedAt)} />
                    <InfoBlock label="Restart Count" value={formatNumber(activeInstance.restartCount)} />
                    <InfoBlock label="Broker Failures" value={formatNumber(activeInstance.brokerFailureCount)} />
                  </div>

                  {isLiveRuntime && !liveApprovalPassed ? (
                    <div className="rounded-2xl border border-rose-900/40 bg-rose-950/25 px-4 py-3 text-sm text-rose-300">
                      Live runtime cannot start until approval is <span className="font-semibold">APPROVED</span>.
                    </div>
                  ) : null}

                  {activeInstance.deploymentNotes ? (
                    <div className="rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-slate-300">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Deployment Notes</p>
                      <p className="mt-2">{activeInstance.deploymentNotes}</p>
                    </div>
                  ) : null}

                  {activeInstance.errorSummary ? (
                    <div className="rounded-2xl border border-rose-900/40 bg-rose-950/25 px-4 py-3 text-sm text-rose-300">
                      {activeInstance.errorSummary}
                    </div>
                  ) : null}

                  {isLiveRuntime ? (
                    <div className="rounded-2xl border border-slate-800 bg-ink-950 px-4 py-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Approval Workflow</p>
                          <p className="mt-2 text-sm text-slate-300">
                            {runtimeApprovalStatus === "PENDING"
                              ? "This live deployment is waiting for admin review."
                              : `Current decision: ${runtimeApprovalStatus}.`}
                          </p>
                        </div>
                        {canReviewLiveApproval ? (
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              disabled={actionInFlight}
                              onClick={() => reviewLiveApproval("approve")}
                              className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-200 transition disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {approveRuntimeMutation.isPending ? "Approving..." : "Approve"}
                            </button>
                            <button
                              type="button"
                              disabled={actionInFlight}
                              onClick={() => reviewLiveApproval("reject")}
                              className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-200 transition disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {rejectRuntimeMutation.isPending ? "Rejecting..." : "Reject"}
                            </button>
                          </div>
                        ) : null}
                      </div>

                      <label className="mt-4 block space-y-2 text-sm text-slate-300">
                        <span className="text-xs uppercase tracking-[0.18em] text-slate-500">Approval Note</span>
                        <textarea
                          rows={3}
                          value={approvalNote}
                          onChange={(event) => setApprovalNote(event.target.value)}
                          disabled={!canReviewLiveApproval}
                          className="w-full rounded-2xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-sm text-slate-200 outline-none transition focus:border-cyan-500/50 disabled:cursor-not-allowed disabled:opacity-60"
                          placeholder={canReviewLiveApproval ? "Optional approval note..." : "Admin approval controls are only available while review is pending."}
                        />
                      </label>
                    </div>
                  ) : null}

                  {actionError ? <div className="rounded-2xl border border-rose-900/40 bg-rose-950/25 px-4 py-3 text-sm text-rose-300">{actionError}</div> : null}
                </div>
              ) : null}
            </DataState>
          </SectionCard>

          <div className="grid gap-6 xl:grid-cols-2">
            <SectionCard title="Runtime Logs" subtitle="Recent instance logs from /runtime/instances/{id}/logs.">
              <DataState
                isLoading={runtimeLogsQuery.isPending && !runtimeLogs.length}
                error={resolveErrorMessage(runtimeLogsQuery.error)}
                isEmpty={!runtimeLogs.length}
                emptyTitle="No logs yet."
              >
                <div className="space-y-3">
                  {runtimeLogs.slice(0, 10).map((log) => (
                    <div key={log.id} className="rounded-2xl border border-slate-800 bg-ink-950 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] uppercase tracking-[0.18em] ${logLevelTone(log.level)}`}>
                          {log.level}
                        </span>
                        <span className="text-xs text-slate-500">{formatTimestamp(log.createdAt)}</span>
                      </div>
                      <p className="mt-2 text-sm text-slate-200">{log.message}</p>
                      <p className="mt-2 text-xs text-slate-500">{log.source}</p>
                    </div>
                  ))}
                </div>
              </DataState>
            </SectionCard>

            <SectionCard title="Alerts" subtitle="Recent runtime alerts and operational recommendations.">
              <DataState isLoading={false} error={null} isEmpty={!runtimeAlerts.length} emptyTitle="No alerts.">
                <div className="space-y-3">
                  {runtimeAlerts.slice(0, 10).map((alert) => (
                    <div key={alert.id} className="rounded-2xl border border-slate-800 bg-ink-950 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] uppercase tracking-[0.18em] ${alertSeverityTone(alert.severity)}`}>
                          {alert.severity}
                        </span>
                        <span className="text-xs text-slate-500">{formatTimestamp(alert.createdAt)}</span>
                      </div>
                      <p className="mt-2 text-sm text-slate-200">{alert.message}</p>
                      <p className="mt-2 text-xs text-slate-500">
                        {alert.type} · {alert.status}
                      </p>
                      {alert.recommendation ? <p className="mt-2 text-xs text-slate-400">Recommendation: {alert.recommendation}</p> : null}
                    </div>
                  ))}
                </div>
              </DataState>
            </SectionCard>
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <SectionCard title="Recent Related Orders" subtitle="Orders linked to this runtime instance or account.">
              <DataState
                isLoading={relatedOrdersQuery.isPending && !relatedOrders.length}
                error={resolveErrorMessage(relatedOrdersQuery.error)}
                isEmpty={!relatedOrders.length}
                emptyTitle="No related orders."
              >
                <div className="space-y-3">
                  {relatedOrders.slice(0, 10).map((order) => (
                    <div key={order.id} className="rounded-2xl border border-slate-800 bg-ink-950 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-white">{order.symbol}</p>
                        <span className={`text-xs uppercase tracking-[0.18em] ${runtimeStatusTone(order.status)}`}>{order.status}</span>
                      </div>
                      <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-400">
                        <span>{order.side}</span>
                        <span>Qty {formatNumber(order.quantity)}</span>
                        <span>{formatTimestamp(order.submittedAt)}</span>
                      </div>
                      <p className="mt-2 text-xs text-slate-500">{order.clientOrderId}</p>
                    </div>
                  ))}
                </div>
              </DataState>
            </SectionCard>

            <SectionCard title="Recent Related Risk Events" subtitle="Risk events associated with this runtime instance or account.">
              <DataState
                isLoading={relatedRiskEventsQuery.isPending && !relatedRiskEvents.length}
                error={resolveErrorMessage(relatedRiskEventsQuery.error)}
                isEmpty={!relatedRiskEvents.length}
                emptyTitle="No related risk events."
              >
                <div className="space-y-3">
                  {relatedRiskEvents.slice(0, 10).map((event) => (
                    <div key={event.id} className="rounded-2xl border border-slate-800 bg-ink-950 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] uppercase tracking-[0.18em] ${alertSeverityTone(event.severity)}`}>
                          {event.severity}
                        </span>
                        <span className="text-xs text-slate-500">{formatTimestamp(event.occurredAt)}</span>
                      </div>
                      <p className="mt-2 text-sm text-slate-200">{event.message}</p>
                      <p className="mt-2 text-xs text-slate-500">
                        {event.status}
                        {event.reasonCode ? ` · ${event.reasonCode}` : ""}
                        {event.ruleId ? ` · Rule ${event.ruleId}` : ""}
                      </p>
                    </div>
                  ))}
                </div>
              </DataState>
            </SectionCard>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoBlock({ label, value, mono = false, tone }: { label: string; value: string; mono?: boolean; tone?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3">
      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={["mt-2 text-sm", mono ? "font-mono text-slate-200" : "text-white", tone ?? ""].join(" ")}>{value}</p>
    </div>
  );
}

function stringifyJson(value: Record<string, unknown>, fallback: Record<string, unknown>) {
  const target = Object.keys(value).length > 0 ? value : fallback;

  try {
    return JSON.stringify(target, null, 2);
  } catch {
    return "{}";
  }
}

function formatTimestamp(value: string | null) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN");
}

function resolveErrorMessage(error: unknown): string | null {
  if (!error) {
    return null;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Request failed.";
}

function runtimeStatusTone(status: string) {
  const normalized = status.trim().toUpperCase();

  if (normalized === "RUNNING") {
    return "border-emerald-900/50 bg-emerald-950/30 text-emerald-300";
  }

  if (normalized === "FAILED" || normalized === "REJECTED") {
    return "border-rose-900/50 bg-rose-950/30 text-rose-300";
  }

  if (normalized === "DEGRADED" || normalized === "STOPPING" || normalized === "STARTING") {
    return "border-amber-900/50 bg-amber-950/30 text-amber-300";
  }

  if (normalized === "STOPPED" || normalized === "CREATED") {
    return "border-slate-800 bg-slate-900/40 text-slate-300";
  }

  return "border-cyan-900/50 bg-cyan-950/30 text-cyan-300";
}

function approvalStatusTone(status: string) {
  const normalized = status.trim().toUpperCase();

  if (normalized === "APPROVED" || normalized === "NOT_REQUIRED") {
    return "border-emerald-900/50 bg-emerald-950/30 text-emerald-300";
  }

  if (normalized === "REJECTED") {
    return "border-rose-900/50 bg-rose-950/30 text-rose-300";
  }

  return "border-amber-900/50 bg-amber-950/30 text-amber-300";
}

function alertSeverityTone(severity: string) {
  const normalized = severity.trim().toUpperCase();

  if (normalized === "CRITICAL" || normalized === "HIGH") {
    return "border-rose-900/50 bg-rose-950/30 text-rose-300";
  }

  if (normalized === "MEDIUM" || normalized === "WARN" || normalized === "WARNING") {
    return "border-amber-900/50 bg-amber-950/30 text-amber-300";
  }

  return "border-cyan-900/50 bg-cyan-950/30 text-cyan-300";
}

function logLevelTone(level: string) {
  const normalized = level.trim().toUpperCase();

  if (normalized === "ERROR") {
    return "border-rose-900/50 bg-rose-950/30 text-rose-300";
  }

  if (normalized === "WARN" || normalized === "WARNING") {
    return "border-amber-900/50 bg-amber-950/30 text-amber-300";
  }

  return "border-cyan-900/50 bg-cyan-950/30 text-cyan-300";
}
