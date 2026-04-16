import { useEffect, useState } from "react";
import { Navigate, createBrowserRouter } from "react-router-dom";

import { bootstrapSession } from "@/shared/api/auth";
import { useSessionStore } from "@/entities/user/store";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { RiskPage } from "@/features/risk/pages/RiskPage";
import { StrategyPage } from "@/features/strategy/pages/StrategyPage";
import { TradePage } from "@/features/trading/pages/TradePage";
import { AppShell } from "@/widgets/app-shell/AppShell";

function useSessionBootstrap() {
  const hasHydrated = useSessionStore((state) => state.hasHydrated);
  const accessToken = useSessionStore((state) => state.accessToken);
  const refreshToken = useSessionStore((state) => state.refreshToken);
  const user = useSessionStore((state) => state.user);
  const [isBootstrapped, setIsBootstrapped] = useState(false);

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    let isActive = true;

    void bootstrapSession().finally(() => {
      if (isActive) {
        setIsBootstrapped(true);
      }
    });

    return () => {
      isActive = false;
    };
  }, [hasHydrated]);

  return {
    isBootstrapped: hasHydrated && isBootstrapped,
    isAuthenticated: Boolean(accessToken && refreshToken && user),
  };
}

function SessionLoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950 px-6 text-slate-300">
      <div className="rounded-3xl border border-slate-800 bg-slate-950/90 px-6 py-5 text-sm shadow-2xl shadow-black/30">
        正在恢复会话...
      </div>
    </div>
  );
}

function ProtectedRoute() {
  const { isBootstrapped, isAuthenticated } = useSessionBootstrap();

  if (!isBootstrapped) {
    return <SessionLoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <AppShell />;
}

function GuestRoute() {
  const { isBootstrapped, isAuthenticated } = useSessionBootstrap();

  if (!isBootstrapped) {
    return <SessionLoadingScreen />;
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <LoginPage />;
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <GuestRoute />,
  },
  {
    path: "/",
    element: <ProtectedRoute />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "trade", element: <TradePage /> },
      { path: "strategy", element: <StrategyPage /> },
      { path: "risk", element: <RiskPage /> },
    ],
  },
]);
