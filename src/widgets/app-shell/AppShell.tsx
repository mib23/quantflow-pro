import { Activity, Bell, CandlestickChart, FlaskConical, LayoutDashboard, LogOut, ShieldAlert } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useSessionStore } from "@/entities/user/store";
import { ROLE_LABELS } from "@/shared/lib/enums";
import { formatCurrency, formatPercent } from "@/shared/lib/format";
import { mockDashboardOverview } from "@/shared/mocks/data";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/trade", label: "Trade & Orders", icon: CandlestickChart },
  { to: "/strategy", label: "Strategy Lab", icon: FlaskConical },
  { to: "/risk", label: "Risk Mgmt", icon: ShieldAlert },
];

export function AppShell() {
  const user = useSessionStore((state) => state.user);
  const clearSession = useSessionStore((state) => state.clearSession);
  const account = mockDashboardOverview.account;

  return (
    <div className="flex min-h-screen bg-transparent text-slate-200">
      <aside className="sticky top-0 hidden h-screen w-72 shrink-0 border-r border-slate-900/80 bg-slate-950/90 px-5 py-6 lg:flex lg:flex-col lg:justify-between">
        <div>
          <div className="flex items-center gap-3 px-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500/10 text-cyan-300">
              <Activity className="h-6 w-6" />
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.25em] text-cyan-300/70">QuantFlow</p>
              <p className="text-lg font-semibold text-white">Trading Console</p>
            </div>
          </div>

          <nav className="mt-10 space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    "group flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition-all",
                    isActive
                      ? "border-cyan-500/40 bg-cyan-500/10 text-white"
                      : "border-transparent bg-transparent text-slate-400 hover:border-slate-800 hover:bg-slate-900/80 hover:text-white",
                  ].join(" ")
                }
              >
                <item.icon className="h-5 w-5" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-cyan-400/15 text-sm font-semibold text-cyan-200">
              {user?.fullName.slice(0, 2).toUpperCase() ?? "QF"}
            </div>
            <div>
              <p className="text-sm font-medium text-white">{user?.fullName ?? "Visitor"}</p>
              <p className="text-xs text-slate-400">{user ? ROLE_LABELS[user.role] : "未登录"}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={clearSession}
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-800 px-4 py-2.5 text-sm text-slate-300 transition hover:border-slate-700 hover:bg-slate-800/80 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            <span>清空会话</span>
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-20 border-b border-slate-900/70 bg-ink-950/85 px-6 py-4 backdrop-blur-xl lg:px-10">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="grid gap-3 sm:grid-cols-3">
              <Metric label="Net Liquidity" value={formatCurrency(account.equity)} tone="text-emerald-400" />
              <Metric label="Day P&L" value={`${formatCurrency(account.dayPnl)} (${formatPercent(account.dayPnlPercent)})`} tone="text-cyan-300" />
              <Metric label="Broker" value={`${account.broker} · ${account.environment.toUpperCase()}`} tone="text-slate-200" />
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden rounded-2xl border border-slate-800 bg-slate-950/80 px-4 py-2 text-right md:block">
                <p className="font-mono text-sm text-white">{new Date().toLocaleTimeString("zh-CN")}</p>
                <p className="text-[11px] text-slate-500">{new Date().toLocaleDateString("zh-CN")}</p>
              </div>
              <button className="rounded-2xl border border-slate-800 bg-slate-950/80 p-3 text-slate-400 transition hover:border-slate-700 hover:text-white">
                <Bell className="h-5 w-5" />
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 px-6 py-8 lg:px-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3">
      <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className={`mt-2 text-sm font-semibold ${tone}`}>{value}</p>
    </div>
  );
}
