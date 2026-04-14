import { Navigate, createBrowserRouter } from "react-router-dom";

import { LoginPage } from "@/features/auth/pages/LoginPage";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { RiskPage } from "@/features/risk/pages/RiskPage";
import { StrategyPage } from "@/features/strategy/pages/StrategyPage";
import { TradePage } from "@/features/trading/pages/TradePage";
import { AppShell } from "@/widgets/app-shell/AppShell";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "trade", element: <TradePage /> },
      { path: "strategy", element: <StrategyPage /> },
      { path: "risk", element: <RiskPage /> },
    ],
  },
]);
