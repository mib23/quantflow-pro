from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

StrategyStatus = Literal["DRAFT", "ACTIVE", "ARCHIVED"]
BacktestStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELED"]


def _dedupe_symbols(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        cleaned = str(value).strip().upper()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


class StrategyCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    status: StrategyStatus = "DRAFT"
    default_parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class StrategyVersionCreateRequest(BaseModel):
    code_snapshot: dict[str, Any] = Field(default_factory=dict)
    parameter_template: dict[str, Any] = Field(default_factory=dict)
    change_reason: str | None = None


class StrategyVersionCloneRequest(BaseModel):
    change_reason: str | None = None


class StrategyVersionItem(BaseModel):
    id: str
    strategy_id: str
    version_number: int
    code_snapshot: dict[str, Any]
    parameter_template: dict[str, Any]
    change_reason: str | None = None
    created_by: str
    created_at: datetime


class StrategyItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: StrategyStatus
    default_parameters: dict[str, Any]
    default_version_id: str | None = None
    latest_version_id: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    version_count: int = 0


class StrategyDetail(StrategyItem):
    versions: list[StrategyVersionItem] = Field(default_factory=list)


class StrategyListResponse(BaseModel):
    items: list[StrategyItem]
    page: int
    page_size: int
    total: int


class BacktestJobCreateRequest(BaseModel):
    strategy_version_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    start_date: date
    end_date: date
    symbols: list[str] = Field(default_factory=list)
    benchmark_symbol: str | None = None
    parameters_snapshot: dict[str, Any] = Field(default_factory=dict)
    queue_name: str = "default"
    execution_environment: str = "test"

    @field_validator("name", "queue_name", "execution_environment")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("benchmark_symbol")
    @classmethod
    def normalize_benchmark(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        return cleaned or None

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, values: list[str]) -> list[str]:
        return _dedupe_symbols(values)

    @model_validator(mode="after")
    def validate_dates(self) -> "BacktestJobCreateRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class BacktestLogItem(BaseModel):
    id: str
    backtest_job_id: str
    level: str
    message: str
    trace_id: str | None = None
    created_at: datetime


class BacktestJobItem(BaseModel):
    id: str
    strategy_id: str
    strategy_version_id: str
    submitted_by: str
    name: str
    status: BacktestStatus
    start_date: date
    end_date: date
    symbols: list[str] = Field(default_factory=list)
    benchmark_symbol: str | None = None
    parameters_snapshot: dict[str, Any] = Field(default_factory=dict)
    queue_name: str
    execution_environment: str
    failure_code: str | None = None
    failure_message: str | None = None
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    canceled_at: datetime | None = None
    updated_at: datetime


class BacktestJobDetail(BacktestJobItem):
    logs: list[BacktestLogItem] = Field(default_factory=list)


class BacktestJobListResponse(BaseModel):
    items: list[BacktestJobItem]
    page: int
    page_size: int
    total: int


class BacktestResultItem(BaseModel):
    id: str
    backtest_job_id: str
    summary_metrics: dict[str, Any]
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    trade_summary: list[dict[str, Any]] = Field(default_factory=list)
    report_format: str
    report_body: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BacktestReportItem(BaseModel):
    backtest_job_id: str
    report_format: str
    report_body: dict[str, Any]
    created_at: datetime
    updated_at: datetime

