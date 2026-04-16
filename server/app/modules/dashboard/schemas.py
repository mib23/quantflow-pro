from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.modules.risk.schemas import RiskEventItem, RiskSummaryResponse


class DashboardAccount(BaseModel):
    id: str
    broker: str
    environment: str
    status: str
    equity: float
    cash: float
    buying_power: float
    day_pnl: float
    day_pnl_percent: float
    snapshot_at: datetime | None = None


class DashboardPosition(BaseModel):
    broker_account_id: str
    symbol: str
    quantity: float
    avg_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    snapshot_at: datetime | None = None


class DashboardMetricSummary(BaseModel):
    total_positions: int
    open_orders: int
    active_risk_rules: int
    risk_events_24h: int


class DashboardPnlSummary(BaseModel):
    day: float
    day_percent: float
    unrealized: float
    realized: float
    total: float


class DashboardHealthSummary(BaseModel):
    status: str
    label: str
    message: str


class DashboardLogEntry(BaseModel):
    id: str
    timestamp: datetime
    level: str
    message: str
    source: str


class EquityCurvePoint(BaseModel):
    timestamp: datetime
    equity: float
    cash: float
    buying_power: float
    day_pnl: float


class EquityCurveResponse(BaseModel):
    account_id: str
    points: list[EquityCurvePoint]
    start_at: datetime | None = None
    end_at: datetime | None = None


class DashboardOverviewResponse(BaseModel):
    account: DashboardAccount
    positions: list[DashboardPosition]
    metrics: DashboardMetricSummary
    pnl: DashboardPnlSummary
    health: DashboardHealthSummary
    recent_alerts: list[RiskEventItem]
    equity_curve: list[EquityCurvePoint]
    logs: list[DashboardLogEntry]
    risk_summary: RiskSummaryResponse
    updated_at: datetime | None = None
