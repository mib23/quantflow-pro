from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

RiskRuleType = Literal[
    "MAX_SINGLE_ORDER_NOTIONAL",
    "RESTRICTED_SYMBOLS",
    "TRADING_WINDOW",
    "DAILY_LOSS_THRESHOLD",
]


def _normalize_str_list(values: list[str] | None, *, upper: bool = False) -> list[str]:
    result: list[str] = []
    for value in values or []:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        cleaned = cleaned.upper() if upper else cleaned
        if cleaned not in result:
            result.append(cleaned)
    return result


def _validate_rule_config(rule_type: RiskRuleType, config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config or {})
    if rule_type == "MAX_SINGLE_ORDER_NOTIONAL":
        max_notional = normalized.get("max_notional")
        if max_notional is None or Decimal(str(max_notional)) <= 0:
            raise ValueError("max_notional is required for MAX_SINGLE_ORDER_NOTIONAL rules.")
        normalized["max_notional"] = float(Decimal(str(max_notional)))
    elif rule_type == "RESTRICTED_SYMBOLS":
        symbols = _normalize_str_list(normalized.get("symbols"), upper=True)
        if not symbols:
            raise ValueError("symbols is required for RESTRICTED_SYMBOLS rules.")
        normalized["symbols"] = symbols
    elif rule_type == "TRADING_WINDOW":
        start_time = str(normalized.get("start_time", "")).strip()
        end_time = str(normalized.get("end_time", "")).strip()
        if not start_time or not end_time:
            raise ValueError("start_time and end_time are required for TRADING_WINDOW rules.")
        normalized["start_time"] = start_time
        normalized["end_time"] = end_time
        normalized["timezone"] = str(normalized.get("timezone") or "America/New_York").strip() or "America/New_York"
        normalized["weekdays"] = _normalize_str_list(normalized.get("weekdays"))
    elif rule_type == "DAILY_LOSS_THRESHOLD":
        max_daily_loss = normalized.get("max_daily_loss")
        if max_daily_loss is None or Decimal(str(max_daily_loss)) <= 0:
            raise ValueError("max_daily_loss is required for DAILY_LOSS_THRESHOLD rules.")
        normalized["max_daily_loss"] = float(Decimal(str(max_daily_loss)))
    return normalized


class RiskScope(BaseModel):
    account_ids: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)

    @field_validator("account_ids")
    @classmethod
    def normalize_account_ids(cls, values: list[str]) -> list[str]:
        return _normalize_str_list(values)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, values: list[str]) -> list[str]:
        return _normalize_str_list(values, upper=True)


class RiskRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    rule_type: RiskRuleType
    scope: RiskScope = Field(default_factory=RiskScope)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    change_reason: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_config(self) -> "RiskRuleCreateRequest":
        self.config = _validate_rule_config(self.rule_type, self.config)
        return self


class RiskRuleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    scope: RiskScope | None = None
    config: dict[str, Any] | None = None
    change_reason: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def normalize_scope(self) -> "RiskRuleUpdateRequest":
        return self


class RiskRuleVersion(BaseModel):
    id: str
    rule_id: str
    version: int
    snapshot: dict[str, Any]
    change_reason: str | None = None
    changed_by: str
    changed_at: datetime


class RiskRule(BaseModel):
    id: str
    name: str
    description: str | None = None
    rule_type: RiskRuleType
    scope: RiskScope
    config: dict[str, Any]
    enabled: bool
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    history: list[RiskRuleVersion] = Field(default_factory=list)


class RiskRuleListResponse(BaseModel):
    items: list[RiskRule]
    page: int
    page_size: int
    total: int


class RiskEventItem(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    rule_type: RiskRuleType
    account_id: str
    runtime_instance_id: str | None = None
    client_order_id: str | None = None
    order_id: str | None = None
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    event_type: str
    status: str
    reason: str
    message: str
    payload: dict[str, Any]
    occurred_at: datetime


class RiskEventListResponse(BaseModel):
    items: list[RiskEventItem]
    page: int
    page_size: int
    total: int


class RiskHardLimits(BaseModel):
    max_daily_loss: float | None = None
    max_single_order_value: float | None = None
    max_position_size_percent: float | None = None


class RiskRestrictions(BaseModel):
    restricted_symbols: list[str] = Field(default_factory=list)
    market_hours_only: bool = False


class RiskSummaryResponse(BaseModel):
    account_id: str | None = None
    hard_limits: RiskHardLimits
    restrictions: RiskRestrictions
    recent_events: list[RiskEventItem] = Field(default_factory=list)
    active_rules: int = 0
    total_events_24h: int = 0
    triggered_today: int = 0
    blocked_orders_today: int = 0
    unresolved_events: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PreTradeCheckRequest(BaseModel):
    broker_account_id: str = Field(min_length=1)
    runtime_instance_id: str | None = Field(default=None, min_length=1)
    symbol: str = Field(min_length=1)
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP"]
    quantity: Decimal = Field(gt=0)
    limit_price: Decimal | None = Field(default=None, gt=0)
    time_in_force: str = Field(default="day", min_length=1)
    idempotency_key: str | None = Field(default=None, min_length=1)
    client_order_id: str | None = Field(default=None, min_length=1)
    reference_price: Decimal | None = Field(default=None, gt=0)
    evaluated_at: datetime | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("time_in_force")
    @classmethod
    def normalize_time_in_force(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("runtime_instance_id", "idempotency_key", "client_order_id")
    @classmethod
    def normalize_optional_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_limit_price(self) -> "PreTradeCheckRequest":
        if self.order_type == "LIMIT" and self.limit_price is None:
            raise ValueError("limit_price is required for LIMIT orders.")
        return self


class RiskCheckResult(BaseModel):
    passed: bool = True
    reason: str | None = None
    events: list[RiskEventItem] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RiskRuleScopeSummary(BaseModel):
    account_ids: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)


class RiskRuleMutationResponse(RiskRule):
    pass


class RiskEventSummary(RiskEventItem):
    pass
