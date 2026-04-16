import { useEffect, useState } from "react";

import { StrategyDetail, StrategyVersion } from "@/shared/types/domain";
import { SectionCard } from "@/shared/ui/SectionCard";

type StrategyVersionPanelProps = {
  strategy: StrategyDetail | null;
  selectedVersionId: string | null;
  isCreating: boolean;
  isCloning: boolean;
  onSelectVersion: (versionId: string) => void;
  onCreateVersion: (input: { strategyId: string; code: string; parameters: Record<string, unknown>; versionNote: string }) => Promise<void>;
  onCloneVersion: (input: { strategyId: string; versionId: string }) => Promise<void>;
};

const starterCode = `def run(context):\n    signal = context.get("signal", 0)\n    return {"signal": signal}`;

export function StrategyVersionPanel({
  strategy,
  selectedVersionId,
  isCreating,
  isCloning,
  onSelectVersion,
  onCreateVersion,
  onCloneVersion,
}: StrategyVersionPanelProps) {
  const [code, setCode] = useState(starterCode);
  const [parametersText, setParametersText] = useState('{"lookback": 20}');
  const [versionNote, setVersionNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!strategy) {
      return;
    }

    if (strategy.versions[0]) {
      setCode(strategy.versions[0].code);
      setParametersText(JSON.stringify(strategy.versions[0].parameters, null, 2));
    } else {
      setCode(starterCode);
      setParametersText(JSON.stringify(strategy.defaultParameters, null, 2));
    }
  }, [strategy]);

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!strategy) {
      return;
    }

    setError(null);

    try {
      await onCreateVersion({
        strategyId: strategy.id,
        code,
        parameters: JSON.parse(parametersText) as Record<string, unknown>,
        versionNote,
      });
      setVersionNote("");
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "版本创建失败");
    }
  }

  return (
    <SectionCard title="版本管理" subtitle={strategy ? `${strategy.name} 的代码快照、参数模板和版本说明。` : "先从左侧选择一条策略。"}>
      {strategy ? (
        <>
          <form className="space-y-3" onSubmit={handleCreate}>
            <textarea
              value={code}
              onChange={(event) => setCode(event.target.value)}
              rows={10}
              className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 font-mono text-xs leading-6 text-slate-200 outline-none transition focus:border-cyan-500/50"
            />
            <textarea
              value={parametersText}
              onChange={(event) => setParametersText(event.target.value)}
              rows={4}
              className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 font-mono text-xs text-slate-200 outline-none transition focus:border-cyan-500/50"
            />
            <input
              value={versionNote}
              onChange={(event) => setVersionNote(event.target.value)}
              placeholder="这次修改做了什么"
              className="w-full rounded-2xl border border-slate-800 bg-ink-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500/50"
            />
            {error ? <p className="text-sm text-rose-300">{error}</p> : null}
            <button
              type="submit"
              disabled={isCreating}
              className="w-full rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-200 transition disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isCreating ? "保存中..." : "保存新版本"}
            </button>
          </form>

          <div className="mt-6 space-y-3">
            {strategy.versions.map((version: StrategyVersion) => (
              <div
                key={version.id}
                className={[
                  "rounded-2xl border px-4 py-4 transition",
                  selectedVersionId === version.id ? "border-cyan-500/40 bg-cyan-500/10" : "border-slate-800 bg-slate-950/60",
                ].join(" ")}
              >
                <button type="button" onClick={() => onSelectVersion(version.id)} className="w-full text-left">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-white">{version.versionTag}</p>
                      <p className="mt-1 text-xs text-slate-500">{version.createdAt}</p>
                    </div>
                    <span className="rounded-full border border-slate-800 bg-slate-950/80 px-2.5 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-300">
                      {Object.keys(version.parameters).length} params
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-slate-300">{version.versionNote || "无版本说明。"}</p>
                </button>
                <button
                  type="button"
                  disabled={isCloning}
                  onClick={() => onCloneVersion({ strategyId: strategy.id, versionId: version.id })}
                  className="mt-4 rounded-full border border-slate-800 bg-slate-950/80 px-3 py-1 text-xs text-slate-300 transition disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isCloning ? "复制中..." : "复制版本"}
                </button>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 text-sm text-slate-400">选择策略后即可保存和复制版本。</div>
      )}
    </SectionCard>
  );
}
