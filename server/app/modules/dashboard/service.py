from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import status

from app.core.exceptions import ApiException
from app.modules.dashboard.repository import DashboardRepository, get_dashboard_session_factory
from app.modules.dashboard.schemas import (
    DashboardAccount,
    DashboardHealthSummary,
    DashboardLogEntry,
    DashboardMetricSummary,
    DashboardOverviewResponse,
    DashboardPnlSummary,
    DashboardPosition,
    EquityCurvePoint,
    EquityCurveResponse,
)
from app.modules.risk.service import RiskService, get_risk_service


@dataclass(slots=True)
class DashboardService:
    repository: DashboardRepository | None = None
    risk_service: RiskService | None = None

    @property
    def resolved_repository(self) -> DashboardRepository:
        return self.repository or DashboardRepository(get_dashboard_session_factory())

    @property
    def resolved_risk_service(self) -> RiskService:
        return self.risk_service or get_risk_service()

    def get_overview(self, user_id: str, broker_account_id: str | None = None) -> DashboardOverviewResponse:
        context = self.resolved_repository.resolve_account(user_id, broker_account_id)
        if context is None:
            raise ApiException("BROKER_ACCOUNT_NOT_FOUND", "Broker account not found.", status.HTTP_404_NOT_FOUND)

        account = context["account"]
        balance = context["balance"]
        resolved_account = DashboardAccount(
            id=str(account.id),
            broker=account.broker_name,
            environment=account.environment,
            status=account.status,
            equity=float(balance.equity) if balance is not None else 0.0,
            cash=float(balance.cash) if balance is not None else 0.0,
            buying_power=float(balance.buying_power) if balance is not None else 0.0,
            day_pnl=float(balance.day_pnl) if balance is not None else 0.0,
            day_pnl_percent=self._day_pnl_percent(balance),
            snapshot_at=balance.snapshot_at if balance is not None else None,
        )

        positions = [
            DashboardPosition(
                broker_account_id=str(position["broker_account_id"]),
                symbol=str(position["symbol"]),
                quantity=float(position["quantity"]),
                avg_price=float(position["avg_price"]),
                market_price=float(position["market_price"]),
                market_value=float(position["market_value"]),
                unrealized_pnl=float(position["unrealized_pnl"]),
                snapshot_at=position["snapshot_at"],
            )
            for position in self.resolved_repository.list_positions(str(account.id))
        ]
        unrealized_total = sum(position.unrealized_pnl for position in positions)

        risk_summary = self.resolved_risk_service.get_summary(user_id=user_id, broker_account_id=str(account.id))
        recent_alerts = risk_summary.recent_events
        equity_curve = self._curve_points(self.resolved_repository.get_equity_curve(str(account.id), days=7, limit=200))
        logs = self._build_logs(str(account.id))

        return DashboardOverviewResponse(
            account=resolved_account,
            positions=positions,
            metrics=DashboardMetricSummary(
                total_positions=len(positions),
                open_orders=self.resolved_repository.count_open_orders(str(account.id)),
                active_risk_rules=risk_summary.active_rules,
                risk_events_24h=risk_summary.total_events_24h,
            ),
            pnl=DashboardPnlSummary(
                day=resolved_account.day_pnl,
                day_percent=resolved_account.day_pnl_percent,
                unrealized=unrealized_total,
                realized=0.0,
                total=resolved_account.day_pnl + unrealized_total,
            ),
            health=self._build_health_summary(risk_summary),
            recent_alerts=recent_alerts,
            equity_curve=equity_curve,
            logs=logs,
            risk_summary=risk_summary,
            updated_at=resolved_account.snapshot_at or datetime.now(UTC),
        )

    def get_equity_curve(self, user_id: str, broker_account_id: str | None = None, *, days: int = 7, limit: int = 200) -> EquityCurveResponse:
        context = self.resolved_repository.resolve_account(user_id, broker_account_id)
        if context is None:
            raise ApiException("BROKER_ACCOUNT_NOT_FOUND", "Broker account not found.", status.HTTP_404_NOT_FOUND)
        account = context["account"]
        balances = self.resolved_repository.get_equity_curve(str(account.id), days=days, limit=limit)
        points = self._curve_points(balances)
        return EquityCurveResponse(
            account_id=str(account.id),
            points=points,
            start_at=points[0].timestamp if points else None,
            end_at=points[-1].timestamp if points else None,
        )

    def _build_logs(self, broker_account_id: str, limit: int = 10) -> list[DashboardLogEntry]:
        order_logs = [
            DashboardLogEntry(
                id=f"order::{order.client_order_id}",
                timestamp=order.updated_at,
                level="INFO" if str(order.status).upper() not in {"FAILED", "REJECTED"} else "WARN",
                message=f"Order {order.client_order_id} {order.symbol} {order.status}",
                source="order",
            )
            for order in self.resolved_repository.list_recent_orders(broker_account_id, limit=limit)
        ]
        risk_logs = [
            DashboardLogEntry(
                id=f"risk::{event.id}",
                timestamp=event.occurred_at,
                level=event.severity,
                message=event.reason,
                source="risk",
            )
            for event, _, _ in self.resolved_repository.list_recent_risk_events(broker_account_id, limit=limit)
        ]
        combined = sorted(order_logs + risk_logs, key=lambda entry: entry.timestamp, reverse=True)
        return combined[:limit]

    @staticmethod
    def _curve_points(balances) -> list[EquityCurvePoint]:
        return [
            EquityCurvePoint(
                timestamp=balance.snapshot_at,
                equity=float(balance.equity),
                cash=float(balance.cash),
                buying_power=float(balance.buying_power),
                day_pnl=float(balance.day_pnl),
            )
            for balance in balances
        ]

    @staticmethod
    def _day_pnl_percent(balance) -> float:
        if balance is None:
            return 0.0
        equity = float(balance.equity)
        pnl = float(balance.day_pnl)
        base = equity - pnl
        if base <= 0:
            return 0.0
        return round(pnl / base * 100, 2)

    @staticmethod
    def _build_health_summary(risk_summary) -> DashboardHealthSummary:
        if any(event.severity.upper() == "CRITICAL" for event in risk_summary.recent_events):
            return DashboardHealthSummary(
                status="critical",
                label="Critical",
                message="存在 CRITICAL 级风险事件，需立即处理。",
            )
        if risk_summary.unresolved_events > 0 or risk_summary.blocked_orders_today > 0:
            return DashboardHealthSummary(
                status="warning",
                label="Warning",
                message="近期有风险事件命中，Dashboard 与 Risk 页面会同步追踪。",
            )
        return DashboardHealthSummary(
            status="healthy",
            label="Healthy",
            message="当前没有未处理的高优先级风险事件。",
        )


@lru_cache
def get_dashboard_service() -> DashboardService:
    return DashboardService()
