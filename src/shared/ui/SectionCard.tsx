import { PropsWithChildren, ReactNode } from "react";
import clsx from "clsx";

type SectionCardProps = PropsWithChildren<{
  title: string;
  subtitle?: string;
  action?: ReactNode;
  className?: string;
}>;

export function SectionCard({ title, subtitle, action, className, children }: SectionCardProps) {
  return (
    <section
      className={clsx(
        "rounded-3xl border border-slate-800/80 bg-slate-950/80 p-5 shadow-[0_20px_80px_-35px_rgba(8,145,178,0.25)]",
        className,
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm text-slate-400">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
