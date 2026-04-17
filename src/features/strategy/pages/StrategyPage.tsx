import { useEffect, useState } from "react";

import { BacktestJobsPanel } from "@/features/strategy/components/BacktestJobsPanel";
import { BacktestResultPanel } from "@/features/strategy/components/BacktestResultPanel";
import { StrategyListPanel } from "@/features/strategy/components/StrategyListPanel";
import { StrategyVersionPanel } from "@/features/strategy/components/StrategyVersionPanel";
import {
  useBacktestJobQuery,
  useBacktestJobsQuery,
  useBacktestResultQuery,
  useStrategiesQuery,
  useStrategyLabMutations,
  useStrategyQuery,
} from "@/features/strategy/hooks/useStrategyLab";
import { DataState } from "@/shared/ui/DataState";
import { PageHeader } from "@/shared/ui/PageHeader";

export function StrategyPage() {
  const strategiesQuery = useStrategiesQuery();
  const jobsQuery = useBacktestJobsQuery();
  const mutations = useStrategyLabMutations();

  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const strategyQuery = useStrategyQuery(selectedStrategyId);
  const selectedStrategy = strategyQuery.data ?? null;

  useEffect(() => {
    if (!strategiesQuery.data?.length) {
      setSelectedStrategyId(null);
      return;
    }

    if (!selectedStrategyId || !strategiesQuery.data.some((strategy) => strategy.id === selectedStrategyId)) {
      setSelectedStrategyId(strategiesQuery.data[0].id);
    }
  }, [selectedStrategyId, strategiesQuery.data]);

  useEffect(() => {
    if (!selectedStrategy?.versions.length) {
      setSelectedVersionId(null);
      return;
    }

    if (!selectedVersionId || !selectedStrategy.versions.some((version) => version.id === selectedVersionId)) {
      setSelectedVersionId(selectedStrategy.versions[0].id);
    }
  }, [selectedStrategy, selectedVersionId]);

  useEffect(() => {
    if (!jobsQuery.data?.length) {
      setSelectedJobId(null);
      return;
    }

    if (!selectedJobId || !jobsQuery.data.some((job) => job.id === selectedJobId)) {
      setSelectedJobId(jobsQuery.data[0].id);
    }
  }, [jobsQuery.data, selectedJobId]);

  const selectedVersion = selectedStrategy?.versions.find((version) => version.id === selectedVersionId) ?? null;
  const selectedJobFallback = jobsQuery.data?.find((job) => job.id === selectedJobId) ?? null;
  const selectedJobQuery = useBacktestJobQuery(selectedJobId);
  const selectedJob = selectedJobQuery.data ?? selectedJobFallback;
  const resultQuery = useBacktestResultQuery(selectedJobId, Boolean(selectedJob?.resultAvailable));

  async function handleDownloadReport(jobId: string) {
    const blob = await mutations.downloadBacktestReport(jobId);
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `backtest-${jobId}.json`;
    anchor.click();
    window.URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Strategy Lab"
        title="研究工作台与异步回测"
        description="在一个页面里完成策略创建、版本管理、回测提交和结果查看。页面只消费标准化策略 DTO 与回测 DTO，不直接依赖 worker 原始结构。"
      />

      <DataState
        isLoading={strategiesQuery.isPending && !strategiesQuery.data}
        error={strategiesQuery.error instanceof Error ? strategiesQuery.error.message : null}
        isEmpty={!strategiesQuery.data?.length}
        emptyTitle="还没有策略，先创建第一条研究策略。"
      >
        <div className="grid gap-6 xl:grid-cols-[320px_360px_minmax(0,1fr)]">
          <StrategyListPanel
            strategies={strategiesQuery.data ?? []}
            selectedStrategyId={selectedStrategyId}
            isCreating={mutations.createStrategy.isPending}
            onSelect={setSelectedStrategyId}
            onCreate={async (input) => {
              const created = await mutations.createStrategy.mutateAsync(input);
              setSelectedStrategyId(created.id);
            }}
          />

          <StrategyVersionPanel
            strategy={selectedStrategy}
            selectedVersionId={selectedVersionId}
            isCreating={mutations.createStrategyVersion.isPending}
            isCloning={mutations.cloneStrategyVersion.isPending}
            onSelectVersion={setSelectedVersionId}
            onCreateVersion={async (input) => {
              const created = await mutations.createStrategyVersion.mutateAsync(input);
              setSelectedVersionId(created.id);
            }}
            onCloneVersion={async (input) => {
              const cloned = await mutations.cloneStrategyVersion.mutateAsync(input);
              setSelectedVersionId(cloned.id);
            }}
          />

          <div className="space-y-6">
            <BacktestJobsPanel
              selectedVersion={selectedVersion}
              jobs={jobsQuery.data ?? []}
              selectedJobId={selectedJobId}
              isSubmitting={mutations.createBacktest.isPending}
              isCanceling={mutations.cancelBacktest.isPending}
              isRetrying={mutations.retryBacktest.isPending}
              onSelectJob={setSelectedJobId}
              onSubmitBacktest={async (input) => {
                const job = await mutations.createBacktest.mutateAsync(input);
                setSelectedJobId(job.id);
              }}
              onCancelJob={async (jobId) => {
                const job = await mutations.cancelBacktest.mutateAsync(jobId);
                setSelectedJobId(job.id);
              }}
              onRetryJob={async (jobId) => {
                const job = await mutations.retryBacktest.mutateAsync(jobId);
                setSelectedJobId(job.id);
              }}
            />

            <BacktestResultPanel
              selectedJob={selectedJob ?? null}
              result={resultQuery.data ?? null}
              isLoading={resultQuery.isPending}
              error={resultQuery.error instanceof Error ? resultQuery.error.message : null}
              onDownloadReport={handleDownloadReport}
            />
          </div>
        </div>
      </DataState>
    </div>
  );
}
