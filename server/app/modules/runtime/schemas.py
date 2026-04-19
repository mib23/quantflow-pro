from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator

RuntimeEnvironment = Literal["PAPER", "LIVE"]
RuntimeStatus = Literal["CREATED", "STARTING", "RUNNING", "STOPPING", "STOPPED", "FAILED", "DEGRADED"]
ApprovalStatus = Literal["NOT_REQUIRED", "PENDING", "APPROVED", "REJECTED"]


class RuntimeInstanceCreateRequest(BaseModel):
    strategy_version_id: str = Field(min_length=1)
    broker_account_id: str = Field(min_length=1)
    environment: RuntimeEnvironment
    parameters_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("parameters_snapshot", "config_snapshot"),
    )
    deployment_notes: str | None = None

    @field_validator("strategy_version_id", "broker_account_id")
    @classmethod
    def normalize_ids(cls, value: str) -> str:
        return value.strip()

    @field_validator("deployment_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class RuntimeApprovalActionRequest(BaseModel):
    note: str | None = None

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class RuntimeHeartbeatRequest(BaseModel):
    summary: str | None = None

    @field_validator("summary")
    @classmethod
    def normalize_summary(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class DeploymentApprovalItem(BaseModel):
    id: str
    runtime_instance_id: str
    requested_by: str
    reviewed_by: str | None = None
    decision: ApprovalStatus | Literal["PENDING"]
    note: str | None = None
    requested_at: datetime
    decided_at: datetime | None = None
    updated_at: datetime


class RuntimeLogEntryItem(BaseModel):
    id: str
    runtime_instance_id: str
    level: Literal["INFO", "WARN", "ERROR"]
    source: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RuntimeAlertItem(BaseModel):
    id: str
    runtime_instance_id: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    alert_type: str
    status: Literal["OPEN", "ACKED", "RESOLVED"]
    message: str
    recommendation: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RuntimeOrderItem(BaseModel):
    id: str
    runtime_instance_id: str | None = None
    broker_account_id: str
    client_order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP"]
    quantity: float
    limit_price: float | None = None
    status: str
    submitted_at: datetime
    updated_at: datetime


class RuntimeRiskEventItem(BaseModel):
    id: str
    runtime_instance_id: str | None = None
    rule_id: str
    rule_name: str
    rule_type: str
    account_id: str
    client_order_id: str | None = None
    severity: str
    status: str
    reason: str
    occurred_at: datetime


class RuntimeInstanceItem(BaseModel):
    id: str
    strategy_id: str
    strategy_name: str
    strategy_version_id: str
    strategy_version_number: int
    broker_account_id: str
    broker_account_no: str
    environment: RuntimeEnvironment
    status: RuntimeStatus
    approval_status: ApprovalStatus
    parameters_snapshot: dict[str, Any] = Field(default_factory=dict)
    deployment_notes: str | None = None
    submitted_by: str
    submitted_at: datetime
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    heartbeat_timeout_seconds: int
    restart_count: int = 0
    broker_failure_count: int = 0
    error_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class RuntimeInstanceDetail(RuntimeInstanceItem):
    approval: DeploymentApprovalItem | None = None
    recent_logs: list[RuntimeLogEntryItem] = Field(default_factory=list)
    recent_alerts: list[RuntimeAlertItem] = Field(default_factory=list)
    recent_orders: list[RuntimeOrderItem] = Field(default_factory=list)
    recent_risk_events: list[RuntimeRiskEventItem] = Field(default_factory=list)


class RuntimeInstanceListResponse(BaseModel):
    items: list[RuntimeInstanceItem]
    page: int
    page_size: int
    total: int


class RuntimeLogListResponse(BaseModel):
    items: list[RuntimeLogEntryItem]
    total: int
