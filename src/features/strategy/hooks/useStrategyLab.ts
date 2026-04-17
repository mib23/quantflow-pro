import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  cancelBacktest,
  cloneStrategyVersion,
  createBacktest,
  createStrategy,
  createStrategyVersion,
  downloadBacktestReport,
  getBacktest,
  getBacktestResult,
  getBacktests,
  getStrategies,
  getStrategy,
  retryBacktest,
} from "@/features/strategy/api/strategyLabApi";
import { strategyLabQueryKeys } from "@/features/strategy/hooks/strategyLabQueryKeys";

export function useStrategiesQuery() {
  return useQuery({
    queryKey: strategyLabQueryKeys.strategies(),
    queryFn: getStrategies,
  });
}

export function useStrategyQuery(strategyId: string | null) {
  return useQuery({
    queryKey: strategyLabQueryKeys.strategy(strategyId),
    queryFn: () => getStrategy(strategyId!),
    enabled: Boolean(strategyId),
  });
}

export function useBacktestJobsQuery() {
  return useQuery({
    queryKey: strategyLabQueryKeys.jobs(),
    queryFn: getBacktests,
    refetchInterval: 3000,
  });
}

export function useBacktestJobQuery(jobId: string | null) {
  return useQuery({
    queryKey: strategyLabQueryKeys.job(jobId),
    queryFn: () => getBacktest(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "QUEUED" || status === "RUNNING" ? 3000 : false;
    },
  });
}

export function useBacktestResultQuery(jobId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: strategyLabQueryKeys.result(jobId),
    queryFn: () => getBacktestResult(jobId!),
    enabled: Boolean(jobId) && enabled,
  });
}

export function useStrategyLabMutations() {
  const queryClient = useQueryClient();

  const refreshStrategies = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.strategies() }),
      queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.jobs() }),
    ]);
  };

  return {
    createStrategy: useMutation({
      mutationFn: createStrategy,
      onSuccess: async () => {
        await refreshStrategies();
      },
    }),
    createStrategyVersion: useMutation({
      mutationFn: createStrategyVersion,
      onSuccess: async (version) => {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.strategies() }),
          queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.strategy(version.strategyId) }),
        ]);
      },
    }),
    cloneStrategyVersion: useMutation({
      mutationFn: cloneStrategyVersion,
      onSuccess: async (_version, variables) => {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.strategies() }),
          queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.strategy(variables.strategyId) }),
        ]);
      },
    }),
    createBacktest: useMutation({
      mutationFn: createBacktest,
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.jobs() });
      },
    }),
    cancelBacktest: useMutation({
      mutationFn: cancelBacktest,
      onSuccess: async (job) => {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.jobs() }),
          queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.job(job.id) }),
        ]);
      },
    }),
    retryBacktest: useMutation({
      mutationFn: retryBacktest,
      onSuccess: async (job) => {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.jobs() }),
          queryClient.invalidateQueries({ queryKey: strategyLabQueryKeys.job(job.id) }),
        ]);
      },
    }),
    downloadBacktestReport,
  };
}
