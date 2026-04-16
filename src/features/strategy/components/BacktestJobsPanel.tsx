import { useState } from "react";

import { BacktestJob, StrategyVersion } from "@/shared/types/domain";
import { SectionCard } from "@/shared/ui/SectionCard";

type BacktestJobsPanelProps = {
  selectedVersion: StrategyVersion | null;
  jobs: BacktestJob[];
  selectedJobId: string | null;
  isSubmitting: boolean;
  isCanceling: boolean;
  isRetrying: boolean;
  onSelectJob: (jobId: string) => void;
  onSubmitBacktest: (input: {
    strategyVersionId: string;
    symbols: string[];
    benchmark: string;
    parameters: Record<string, unknown>;
    datasetKey: string;
    timeRange: {
      start: string;
      end: string;
    };
  }) => Promise<void>;
  onCancelJob: (jobId: string) => Promise<void>;
  onRetryJob: (jobId: string) => Promise<void>;
};

export function BacktestJobsPanel({
  selectedVersion,
  jobs,
  selectedJobId,
  isSubmitting,
  isCanceling,
  isRetrying,
  onSelectJob,
  onSubmitBacktest,
  onCancelJob,
  onRetryJob,
}: BacktestJobsPanelProps) {
  const [symbolsText, setSymbolsText] = useState("AAPL,MSFT");
  const [benchmark, setBenchmark] = useState("SPY");
  const [datasetKey, setDatasetKey] = useState("demo-momentum");
  const [start, setStart] = useState("2024-01-01T00:00:00Z");
  const [end, setEnd] = useState("2024-03-31T00:00:00Z");
  const [parametersText, setParametersText] = useState('{"lookback": 20}');
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedVersion) {
      return;
    }

    setError(null);

    try {
      await onSubmitBacktest({
        strategyVersionId: selectedVersion.id,
        symbols: symbolsText.split(",").map((value) => value.trim()).filter(Boolean),
        benchmark,
        datasetKey,
        parameters: JSON.parse(parametersText) as Record<string, unknown>,
        timeRange: { start, end },
      });
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "回测提交失败");
    }
  }

  return (
    <SectionCard title="回测任务" subtitle={selectedVersion ? `为 ${selectedVersion.versionTag} 提交异步回测。` : "先选择一个版本，再提交回测任务。"}>
      <form className="space-y-3" onSubmit={handleSubmit}>
        <input
          value={symbolsText}
          onChange={(event) => setSymbolsText(event.target.value)}
          placeholder="AAPL,MSFT"
          className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500/50"
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={benchmark}
            onChange={(event) => setBenchmark(event.target.value)}
            placeholder="SPY"
            className="rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500/50"
          />
          <input
            value={datasetKey}
            onChange={(event) => setDatasetKey(event.target.value)}
            placeholder="demo-momentum"
            className="rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500/50"
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={start}
            onChange={(event) => setStart(event.target.value)}
            className="rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500/50"
          />
          <input
            value={end}
            onChange={(event) => setEnd(event.target.value)}
            className="rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500/50"
          />
        </div>
        <textarea
          value={parametersText}
          onChange={(event) => setParametersText(event.target.value)}
          rows={4}
          className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 font-mono text-xs text-slate-200 outline-none transition focus:border-cyan-500/50"
        />
        {error ? <p className="text-sm text-rose-300">{error}</p> : null}
        <button
          type="submit"
          disabled={!selectedVersion || isSubmitting}
          className="w-full rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-200 transition disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "提交中..." : "提交回测"}
        </button>
      </form>

      <div className="mt-6 space-y-3">
        {jobs.map((job) => (
          <div
            key={job.id}
            className={[
              "rounded-2xl border px-4 py-4 transition",
              selectedJobId === job.id ? "border-cyan-500/40 bg-cyan-500/10" : "border-slate-800 bg-slate-950/60",
            ].join(" ")}
          >
            <button type="button" onClick={() => onSelectJob(job.id)} className="w-full text-left">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-white">
                    {job.strategyName} · {job.strategyVersionTag}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{job.createdAt}</p>
                </div>
                <span className={`rounded-full border px-2.5 py-1 text-[11px] uppercase tracking-[0.18em] ${statusTone(job.status)}`}>
                  {job.status}
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-300">
                {job.symbols.join(", ")} · {job.timeRange.start.slice(0, 10)} to {job.timeRange.end.slice(0, 10)}
              </p>
              {job.failureReason ? <p className="mt-2 text-sm text-rose-300">{job.failureReason}</p> : null}
            </button>
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                disabled={isCanceling || ["SUCCEEDED", "FAILED", "CANCELED"].includes(job.status)}
                onClick={() => onCancelJob(job.id)}
                className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs text-rose-200 transition disabled:cursor-not-allowed disabled:opacity-50"
              >
                取消
              </button>
              <button
                type="button"
                disabled={isRetrying || !["FAILED", "CANCELED"].includes(job.status)}
                onClick={() => onRetryJob(job.id)}
                className="rounded-full border border-slate-800 bg-slate-950/80 px-3 py-1 text-xs text-slate-300 transition disabled:cursor-not-allowed disabled:opacity-50"
              >
                重试
              </button>
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

function statusTone(status: BacktestJob["status"]) {
  switch (status) {
    case "SUCCEEDED":
      return "border-emerald-900/50 bg-emerald-950/30 text-emerald-300";
    case "FAILED":
      return "border-rose-900/50 bg-rose-950/30 text-rose-300";
    case "CANCELED":
      return "border-slate-800 bg-slate-900/40 text-slate-300";
    case "RUNNING":
      return "border-cyan-900/50 bg-cyan-950/30 text-cyan-300";
    default:
      return "border-amber-900/50 bg-amber-950/30 text-amber-300";
  }
}
