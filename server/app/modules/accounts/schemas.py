from datetime import datetime

from pydantic import BaseModel, Field


class BrokerAccount(BaseModel):
    id: str
    broker: str
    broker_account_no: str
    external_account_id: str
    environment: str
    status: str
    equity: float = 0.0
    cash: float = 0.0
    buying_power: float = 0.0
    day_pnl: float = 0.0
    day_pnl_percent: float = 0.0
    snapshot_at: datetime | None = None


class Position(BaseModel):
    broker_account_id: str
    symbol: str
    quantity: float = Field(default=0.0)
    avg_price: float = Field(default=0.0)
    market_price: float = Field(default=0.0)
    market_value: float = Field(default=0.0)
    unrealized_pnl: float = Field(default=0.0)
    snapshot_at: datetime | None = None


class BrokerAccountsListResponse(BaseModel):
    items: list[BrokerAccount]
    page: int = 1
    page_size: int = 0
    total: int = 0


class PositionsListResponse(BaseModel):
    items: list[Position]
    page: int = 1
    page_size: int = 0
    total: int = 0


class OverviewResponse(BaseModel):
    account: BrokerAccount
    positions: list[Position]
