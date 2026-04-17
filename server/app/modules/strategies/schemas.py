from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class StrategyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    default_parameters: dict[str, object] = Field(default_factory=dict)


class StrategyVersionCreateRequest(BaseModel):
    code: str = Field(min_length=1)
    parameters: dict[str, object] = Field(default_factory=dict)
    version_note: str | None = None


class StrategyVersionItem(BaseModel):
    id: str
    strategy_id: str
    version_number: int
    version_tag: str
    code: str
    parameters: dict[str, object]
    version_note: str | None
    created_by: str
    created_at: datetime


class StrategySummary(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    default_parameters: dict[str, object]
    latest_version_id: str | None
    latest_version_tag: str | None
    updated_at: datetime


class StrategyDetail(StrategySummary):
    owner_user_id: str
    created_at: datetime
    versions: list[StrategyVersionItem] = Field(default_factory=list)


class StrategyListData(BaseModel):
    items: list[StrategySummary]
    total: int
