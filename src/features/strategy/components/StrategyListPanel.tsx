import { useState } from "react";

import { StrategySummary } from "@/shared/types/domain";
import { SectionCard } from "@/shared/ui/SectionCard";

type StrategyListPanelProps = {
  strategies: StrategySummary[];
  selectedStrategyId: string | null;
  isCreating: boolean;
  onSelect: (strategyId: string) => void;
  onCreate: (input: { name: string; description: string; defaultParameters: Record<string, unknown> }) => Promise<void>;
};

export function StrategyListPanel({ strategies, selectedStrategyId, isCreating, onSelect, onCreate }: StrategyListPanelProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [defaultParametersText, setDefaultParametersText] = useState('{"lookback": 20}');
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const defaultParameters = JSON.parse(defaultParametersText) as Record<string, unknown>;
      await onCreate({ name, description, defaultParameters });
      setName("");
      setDescription("");
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "策略创建失败");
    }
  }

  return (
    <SectionCard title="策略列表" subtitle="创建策略并选择一个工作中的研究对象。">
      <form className="space-y-3" onSubmit={handleSubmit}>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Momentum Pulse"
          className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500/50"
        />
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
          placeholder="写一句这条策略做什么。"
          className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500/50"
        />
        <textarea
          value={defaultParametersText}
          onChange={(event) => setDefaultParametersText(event.target.value)}
          rows={3}
          className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 font-mono text-xs text-slate-200 outline-none transition focus:border-cyan-500/50"
        />
        {error ? <p className="text-sm text-rose-300">{error}</p> : null}
        <button
          type="submit"
          disabled={isCreating || name.trim().length < 2}
          className="w-full rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-200 transition disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isCreating ? "创建中..." : "创建策略"}
        </button>
      </form>

      <div className="mt-6 space-y-3">
        {strategies.map((strategy) => (
          <button
            key={strategy.id}
            type="button"
            onClick={() => onSelect(strategy.id)}
            className={[
              "w-full rounded-2xl border px-4 py-4 text-left transition",
              selectedStrategyId === strategy.id
                ? "border-cyan-500/40 bg-cyan-500/10"
                : "border-slate-800 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-900/70",
            ].join(" ")}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-white">{strategy.name}</p>
                <p className="mt-1 text-xs text-slate-500">{strategy.latestVersionTag ?? "尚无版本"}</p>
              </div>
              <span className="rounded-full border border-slate-800 bg-slate-950/80 px-2.5 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-300">
                {strategy.status}
              </span>
            </div>
            <p className="mt-3 text-sm text-slate-300">{strategy.description || "暂无描述。"}</p>
          </button>
        ))}
      </div>
    </SectionCard>
  );
}
