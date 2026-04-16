from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BacktestTimeRange(BaseModel):
    start: datetime
    end: datetime


class BacktestJobCreateRequest(BaseModel):
    strategy_version_id: str
    symbols: list[str] = Field(default_factory=list)
    time_range: BacktestTimeRange
    benchmark: str | None = None
    parameters: dict[str, object] = Field(default_factory=dict)
    dataset_key: str = "demo-momentum"


class BacktestLogItem(BaseModel):
    id: str
    level: str
    code: str
    message: str
    details: dict[str, object]
    created_at: datetime


class BacktestJobItem(BaseModel):
    id: str
    strategy_id: str
    strategy_version_id: str
    strategy_name: str
    strategy_version_tag: str
    status: str
    queue_name: str
    queue_job_id: str | None
    symbols: list[str]
    benchmark: str | None
    parameters: dict[str, object]
    time_range: dict[str, str]
    failure_code: str | None
    failure_reason: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result_available: bool = False
    logs: list[BacktestLogItem] = Field(default_factory=list)


class BacktestJobListData(BaseModel):
    items: list[BacktestJobItem]
    total: int


class BacktestResultItem(BaseModel):
    job_id: str
    metrics: dict[str, object]
    equity_curve: list[dict[str, object]]
    trades: list[dict[str, object]]
    report: dict[str, object]
    report_format: str
    generated_at: datetime
