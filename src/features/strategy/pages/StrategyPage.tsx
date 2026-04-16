import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionCard } from "@/shared/ui/SectionCard";

const strategyCode = `class MyStrategy(StrategyBase):
    def init(self):
        self.ma_fast = MA(self.data.close, 20)
        self.ma_slow = MA(self.data.close, 50)

    def on_bar(self, bar):
        if self.ma_fast[-1] > self.ma_slow[-1]:
            self.buy(size=100)
        elif self.ma_fast[-1] < self.ma_slow[-1]:
            self.sell(size=100)`;

export function StrategyPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Strategy"
        title="研究与回测骨架"
        description="Phase 0 只保留领域边界和页面落点，等回测任务系统进入 Phase 3 后再接异步任务与结果归档。"
      />

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <SectionCard title="Research Scope" subtitle="当前阶段只做编辑器占位和契约预留。">
          <div className="space-y-3 text-sm text-slate-300">
            <p>已确认策略研究域不会直接依赖 Broker SDK，执行和回测通过后台作业解耦。</p>
            <p>一期不做参数优化、Walk-forward 和多进程编排，只保留文件、版本、任务和结果接口边界。</p>
          </div>
        </SectionCard>

        <SectionCard title="Editor Placeholder" subtitle="后续可替换为 Monaco。">
          <pre className="overflow-x-auto rounded-2xl border border-slate-800 bg-ink-950 p-5 text-sm leading-7 text-slate-300">
            <code>{strategyCode}</code>
          </pre>
        </SectionCard>
      </div>
    </div>
  );
}
