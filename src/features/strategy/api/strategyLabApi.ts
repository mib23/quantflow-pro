import { httpClient } from "@/shared/api/http";
import { ApiEnvelope, BacktestJob, BacktestResult, StrategyDetail, StrategySummary, StrategyVersion } from "@/shared/types/domain";

type StrategySummaryDto = {
  id: string;
  name: string;
  description: string | null;
  status: "ACTIVE" | "ARCHIVED" | "DRAFT";
  default_parameters: Record<string, unknown>;
  latest_version_id: string | null;
  latest_version_tag: string | null;
  updated_at: string;
};

type StrategyVersionDto = {
  id: string;
  strategy_id: string;
  version_number: number;
  version_tag: string;
  code: string;
  parameters: Record<string, unknown>;
  version_note: string | null;
  created_by: string;
  created_at: string;
};

type StrategyDetailDto = StrategySummaryDto & {
  owner_user_id: string;
  created_at: string;
  versions: StrategyVersionDto[];
};

type BacktestLogDto = {
  id: string;
  level: string;
  code: string;
  message: string;
  details: Record<string, unknown>;
  created_at: string;
};

type BacktestJobDto = {
  id: string;
  strategy_id: string;
  strategy_version_id: string;
  strategy_name: string;
  strategy_version_tag: string;
  status: BacktestJob["status"];
  queue_name: string;
  queue_job_id: string | null;
  symbols: string[];
  benchmark: string | null;
  parameters: Record<string, unknown>;
  time_range: {
    start: string;
    end: string;
  };
  failure_code: string | null;
  failure_reason: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  result_available: boolean;
  logs: BacktestLogDto[];
};

type BacktestResultDto = {
  job_id: string;
  metrics: Record<string, unknown>;
  equity_curve: Array<{ time: string; equity: number }>;
  trades: Array<Record<string, unknown>>;
  report: Record<string, unknown>;
  report_format: string;
  generated_at: string;
};

function mapStrategySummary(input: StrategySummaryDto): StrategySummary {
  return {
    id: input.id,
    name: input.name,
    description: input.description,
    status: input.status,
    defaultParameters: input.default_parameters,
    latestVersionId: input.latest_version_id,
    latestVersionTag: input.latest_version_tag,
    updatedAt: input.updated_at,
  };
}

function mapStrategyVersion(input: StrategyVersionDto): StrategyVersion {
  return {
    id: input.id,
    strategyId: input.strategy_id,
    versionNumber: input.version_number,
    versionTag: input.version_tag,
    code: input.code,
    parameters: input.parameters,
    versionNote: input.version_note,
    createdBy: input.created_by,
    createdAt: input.created_at,
  };
}

function mapStrategyDetail(input: StrategyDetailDto): StrategyDetail {
  return {
    ...mapStrategySummary(input),
    ownerUserId: input.owner_user_id,
    createdAt: input.created_at,
    versions: input.versions.map(mapStrategyVersion),
  };
}

function mapBacktestJob(input: BacktestJobDto): BacktestJob {
  return {
    id: input.id,
    strategyId: input.strategy_id,
    strategyVersionId: input.strategy_version_id,
    strategyName: input.strategy_name,
    strategyVersionTag: input.strategy_version_tag,
    status: input.status,
    queueName: input.queue_name,
    queueJobId: input.queue_job_id,
    symbols: input.symbols,
    benchmark: input.benchmark,
    parameters: input.parameters,
    timeRange: input.time_range,
    failureCode: input.failure_code,
    failureReason: input.failure_reason,
    createdAt: input.created_at,
    startedAt: input.started_at,
    finishedAt: input.finished_at,
    resultAvailable: input.result_available,
    logs: input.logs.map((log) => ({
      id: log.id,
      level: log.level,
      code: log.code,
      message: log.message,
      details: log.details,
      createdAt: log.created_at,
    })),
  };
}

function mapBacktestResult(input: BacktestResultDto): BacktestResult {
  return {
    jobId: input.job_id,
    metrics: input.metrics,
    equityCurve: input.equity_curve,
    trades: input.trades,
    report: input.report,
    reportFormat: input.report_format,
    generatedAt: input.generated_at,
  };
}

export async function getStrategies(): Promise<StrategySummary[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: StrategySummaryDto[]; total: number }>>("/strategies");
  return response.data.data.items.map(mapStrategySummary);
}

export async function createStrategy(input: {
  name: string;
  description?: string;
  defaultParameters?: Record<string, unknown>;
}): Promise<StrategyDetail> {
  const response = await httpClient.post<ApiEnvelope<StrategyDetailDto>>("/strategies", {
    name: input.name,
    description: input.description,
    default_parameters: input.defaultParameters ?? {},
  });
  return mapStrategyDetail(response.data.data);
}

export async function getStrategy(strategyId: string): Promise<StrategyDetail> {
  const response = await httpClient.get<ApiEnvelope<StrategyDetailDto>>(`/strategies/${encodeURIComponent(strategyId)}`);
  return mapStrategyDetail(response.data.data);
}

export async function createStrategyVersion(input: {
  strategyId: string;
  code: string;
  parameters?: Record<string, unknown>;
  versionNote?: string;
}): Promise<StrategyVersion> {
  const response = await httpClient.post<ApiEnvelope<StrategyVersionDto>>(
    `/strategies/${encodeURIComponent(input.strategyId)}/versions`,
    {
      code: input.code,
      parameters: input.parameters ?? {},
      version_note: input.versionNote,
    },
  );
  return mapStrategyVersion(response.data.data);
}

export async function cloneStrategyVersion(input: { strategyId: string; versionId: string }): Promise<StrategyVersion> {
  const response = await httpClient.post<ApiEnvelope<StrategyVersionDto>>(
    `/strategies/${encodeURIComponent(input.strategyId)}/versions/${encodeURIComponent(input.versionId)}/clone`,
  );
  return mapStrategyVersion(response.data.data);
}

export async function getBacktests(): Promise<BacktestJob[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: BacktestJobDto[]; total: number }>>("/backtests");
  return response.data.data.items.map(mapBacktestJob);
}

export async function createBacktest(input: {
  strategyVersionId: string;
  symbols: string[];
  benchmark?: string;
  parameters?: Record<string, unknown>;
  timeRange: {
    start: string;
    end: string;
  };
  datasetKey?: string;
}): Promise<BacktestJob> {
  const response = await httpClient.post<ApiEnvelope<BacktestJobDto>>("/backtests", {
    strategy_version_id: input.strategyVersionId,
    symbols: input.symbols,
    benchmark: input.benchmark,
    parameters: input.parameters ?? {},
    dataset_key: input.datasetKey ?? "demo-momentum",
    time_range: input.timeRange,
  });
  return mapBacktestJob(response.data.data);
}

export async function getBacktest(jobId: string): Promise<BacktestJob> {
  const response = await httpClient.get<ApiEnvelope<BacktestJobDto>>(`/backtests/${encodeURIComponent(jobId)}`);
  return mapBacktestJob(response.data.data);
}

export async function cancelBacktest(jobId: string): Promise<BacktestJob> {
  const response = await httpClient.post<ApiEnvelope<BacktestJobDto>>(`/backtests/${encodeURIComponent(jobId)}/cancel`);
  return mapBacktestJob(response.data.data);
}

export async function retryBacktest(jobId: string): Promise<BacktestJob> {
  const response = await httpClient.post<ApiEnvelope<BacktestJobDto>>(`/backtests/${encodeURIComponent(jobId)}/retry`);
  return mapBacktestJob(response.data.data);
}

export async function getBacktestResult(jobId: string): Promise<BacktestResult> {
  const response = await httpClient.get<ApiEnvelope<BacktestResultDto>>(`/backtests/${encodeURIComponent(jobId)}/result`);
  return mapBacktestResult(response.data.data);
}

export async function downloadBacktestReport(jobId: string): Promise<Blob> {
  const response = await httpClient.get(`/backtests/${encodeURIComponent(jobId)}/report`, {
    responseType: "blob",
  });
  return response.data as Blob;
}
