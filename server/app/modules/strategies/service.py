from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.database import create_sync_engine
from app.core.settings import get_settings
from app.modules.strategies.repository import StrategyRepository, get_strategy_session_factory
from app.modules.strategies.schemas import (
    BacktestJobCreateRequest,
    BacktestJobDetail,
    BacktestJobItem,
    BacktestJobListResponse,
    BacktestReportItem,
    BacktestResultItem,
    StrategyCreateRequest,
    StrategyDetail,
    StrategyItem,
    StrategyListResponse,
    StrategyVersionCloneRequest,
    StrategyVersionCreateRequest,
    StrategyVersionItem,
)


@lru_cache
def get_strategy_repository() -> StrategyRepository:
    return StrategyRepository(get_strategy_session_factory())


def get_strategy_service() -> "StrategyService":
    return StrategyService(get_strategy_repository())


class StrategyService:
    def __init__(self, repository: StrategyRepository):
        self._repository = repository

    def list_strategies(self, *, user_id: str, page: int = 1, page_size: int = 20) -> StrategyListResponse:
        return self._repository.list_strategies(user_id=user_id, page=page, page_size=page_size)

    def create_strategy(self, payload: StrategyCreateRequest, *, created_by: str) -> StrategyItem:
        return self._repository.create_strategy(payload, created_by=created_by)

    def get_strategy(self, strategy_id: str, *, user_id: str) -> StrategyDetail:
        return self._repository.get_strategy(strategy_id, user_id=user_id)

    def create_version(self, strategy_id: str, payload: StrategyVersionCreateRequest, *, created_by: str) -> StrategyVersionItem:
        return self._repository.create_version(strategy_id, payload, created_by=created_by)

    def clone_version(
        self,
        strategy_id: str,
        version_id: str,
        payload: StrategyVersionCloneRequest,
        *,
        created_by: str,
    ) -> StrategyVersionItem:
        return self._repository.clone_version(strategy_id, version_id, payload, created_by=created_by)


