from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.risk.schemas import RiskCheckResult

OrderStatus = Literal[
    "PENDING_SUBMIT",
    "SUBMITTED",
    "OPEN",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCEL_REQUESTED",
    "CANCELED",
    "REJECTED",
    "FAILED",
]


class PlaceOrderRequest(BaseModel):
    broker_account_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP"]
    quantity: Decimal = Field(gt=0)
    limit_price: Decimal | None = Field(default=None, gt=0)
    time_in_force: str = Field(default="day", min_length=1)
    idempotency_key: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("time_in_force")
    @classmethod
    def normalize_time_in_force(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("idempotency_key")
    @classmethod
    def normalize_idempotency_key(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_limit_price(self) -> "PlaceOrderRequest":
        if self.order_type == "LIMIT" and self.limit_price is None:
            raise ValueError("limit_price is required for LIMIT orders.")
        return self


class OrderItem(BaseModel):
    id: str
    broker_account_id: str
    client_order_id: str
    broker_order_id: str | None = None
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP"]
    quantity: float
    limit_price: float | None = None
    status: OrderStatus
    time_in_force: str
    idempotency_key: str
    submitted_at: datetime
    updated_at: datetime


class PlaceOrderResponse(OrderItem):
    risk_check: RiskCheckResult = Field(default_factory=RiskCheckResult)


class OrderListData(BaseModel):
    items: list[OrderItem]
    page: int
    page_size: int
    total: int


class ExecutionItem(BaseModel):
    id: str
    order_id: str
    client_order_id: str
    broker_order_id: str | None = None
    symbol: str
    side: Literal["BUY", "SELL"]
    broker_execution_id: str
    filled_quantity: float
    filled_price: float
    fee_amount: float
    executed_at: datetime


class ExecutionListData(BaseModel):
    items: list[ExecutionItem]
    page: int
    page_size: int
    total: int
