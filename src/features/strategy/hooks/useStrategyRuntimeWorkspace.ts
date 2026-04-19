import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveRuntimeDeployment,
  createRuntimeInstance,
  CreateRuntimeInstanceInput,
  getRuntimeBrokerAccountOptions,
  getRuntimeInstanceDetail,
  getRuntimeInstanceLogs,
  getRuntimeInstances,
  getRuntimeRelatedOrders,
  getRuntimeRelatedRiskEvents,
  getRuntimeStrategyDetail,
  getRuntimeStrategyOptions,
  rejectRuntimeDeployment,
  restartRuntimeInstance,
  RuntimeInstance,
  RuntimeApprovalActionInput,
  startRuntimeInstance,
  stopRuntimeInstance,
} from "@/features/strategy/api/runtimeApi";
import { strategyRuntimeQueryKeys } from "@/features/strategy/hooks/strategyRuntimeQueryKeys";

export function useRuntimeStrategyOptionsQuery() {
  return useQuery({
    queryKey: strategyRuntimeQueryKeys.strategies(),
    queryFn: getRuntimeStrategyOptions,
    placeholderData: (previous) => previous,
  });
}

export function useRuntimeStrategyDetailQuery(strategyId: string | null) {
  const normalizedStrategyId = strategyId?.trim() ?? "";

  return useQuery({
    queryKey: strategyRuntimeQueryKeys.strategyDetail(normalizedStrategyId || "__pending__"),
    queryFn: () => getRuntimeStrategyDetail(normalizedStrategyId),
    enabled: normalizedStrategyId.length > 0,
    placeholderData: (previous) => previous,
  });
}

export function useRuntimeBrokerAccountsQuery() {
  return useQuery({
    queryKey: strategyRuntimeQueryKeys.brokerAccounts(),
    queryFn: getRuntimeBrokerAccountOptions,
    placeholderData: (previous) => previous,
  });
}

export function useRuntimeInstancesQuery() {
  return useQuery({
    queryKey: strategyRuntimeQueryKeys.runtimeInstances(),
    queryFn: getRuntimeInstances,
    placeholderData: (previous) => previous,
    refetchInterval: 15_000,
  });
}

export function useRuntimeInstanceDetailQuery(instanceId: string | null) {
  const normalizedInstanceId = instanceId?.trim() ?? "";

  return useQuery({
    queryKey: strategyRuntimeQueryKeys.runtimeInstanceDetail(normalizedInstanceId || "__pending__"),
    queryFn: () => getRuntimeInstanceDetail(normalizedInstanceId),
    enabled: normalizedInstanceId.length > 0,
    placeholderData: (previous) => previous,
    refetchInterval: 10_000,
  });
}

export function useRuntimeInstanceLogsQuery(instanceId: string | null) {
  const normalizedInstanceId = instanceId?.trim() ?? "";

  return useQuery({
    queryKey: strategyRuntimeQueryKeys.runtimeLogs(normalizedInstanceId || "__pending__"),
    queryFn: () => getRuntimeInstanceLogs(normalizedInstanceId),
    enabled: normalizedInstanceId.length > 0,
    placeholderData: (previous) => previous,
    refetchInterval: 10_000,
  });
}

export function useRuntimeRelatedOrdersQuery(instance: RuntimeInstance | null) {
  const instanceId = instance?.id?.trim() ?? "";

  return useQuery({
    queryKey: strategyRuntimeQueryKeys.runtimeOrders(instanceId || "__pending__"),
    queryFn: () => (instance ? getRuntimeRelatedOrders(instance) : Promise.resolve([])),
    enabled: instanceId.length > 0,
    placeholderData: (previous) => previous,
    refetchInterval: 15_000,
  });
}

export function useRuntimeRelatedRiskEventsQuery(instance: RuntimeInstance | null) {
  const instanceId = instance?.id?.trim() ?? "";

  return useQuery({
    queryKey: strategyRuntimeQueryKeys.runtimeRiskEvents(instanceId || "__pending__"),
    queryFn: () => (instance ? getRuntimeRelatedRiskEvents(instance) : Promise.resolve([])),
    enabled: instanceId.length > 0,
    placeholderData: (previous) => previous,
    refetchInterval: 15_000,
  });
}

export function useCreateRuntimeInstanceMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateRuntimeInstanceInput) => createRuntimeInstance(input),
    onSuccess: (instance) => {
      queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeInstances() });
      queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeInstanceDetail(instance.id) });
      queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeLogs(instance.id) });
      queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeOrders(instance.id) });
      queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeRiskEvents(instance.id) });
    },
  });
}

type RuntimeActionInput = {
  instanceId: string;
};

function invalidateRuntimeInstanceQueries(queryClient: ReturnType<typeof useQueryClient>, instanceId: string) {
  queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeInstances() });
  queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeInstanceDetail(instanceId) });
  queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeLogs(instanceId) });
  queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeOrders(instanceId) });
  queryClient.invalidateQueries({ queryKey: strategyRuntimeQueryKeys.runtimeRiskEvents(instanceId) });
}

export function useStartRuntimeInstanceMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ instanceId }: RuntimeActionInput) => startRuntimeInstance(instanceId),
    onSuccess: (_, variables) => {
      invalidateRuntimeInstanceQueries(queryClient, variables.instanceId);
    },
  });
}

type RuntimeApprovalMutationInput = {
  instanceId: string;
  input?: RuntimeApprovalActionInput;
};

export function useApproveRuntimeDeploymentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ instanceId, input }: RuntimeApprovalMutationInput) => approveRuntimeDeployment(instanceId, input),
    onSuccess: (_, variables) => {
      invalidateRuntimeInstanceQueries(queryClient, variables.instanceId);
    },
  });
}

export function useRejectRuntimeDeploymentMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ instanceId, input }: RuntimeApprovalMutationInput) => rejectRuntimeDeployment(instanceId, input),
    onSuccess: (_, variables) => {
      invalidateRuntimeInstanceQueries(queryClient, variables.instanceId);
    },
  });
}

export function useStopRuntimeInstanceMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ instanceId }: RuntimeActionInput) => stopRuntimeInstance(instanceId),
    onSuccess: (_, variables) => {
      invalidateRuntimeInstanceQueries(queryClient, variables.instanceId);
    },
  });
}

export function useRestartRuntimeInstanceMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ instanceId }: RuntimeActionInput) => restartRuntimeInstance(instanceId),
    onSuccess: (_, variables) => {
      invalidateRuntimeInstanceQueries(queryClient, variables.instanceId);
    },
  });
}
