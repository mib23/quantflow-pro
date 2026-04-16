from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_sync_engine
from app.core.exceptions import ApiException
from app.core.settings import get_settings
from app.modules.strategies.repository import StrategyRepository
from app.modules.strategies.schemas import StrategyCreateRequest, StrategyDetail, StrategyListData, StrategyVersionCreateRequest, StrategyVersionItem


@lru_cache
def get_strategy_session_factory() -> Callable[[], Session]:
    engine = create_sync_engine(get_settings().database_url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@lru_cache
def get_strategy_service() -> "StrategyService":
    return StrategyService(StrategyRepository(get_strategy_session_factory()))


class StrategyService:
    def __init__(self, repository: StrategyRepository):
        self._repository = repository

    def list_strategies(self, *, user_id: str) -> StrategyListData:
        items, total = self._repository.list_strategies(user_id=user_id)
        return StrategyListData(items=items, total=total)

    def get_strategy(self, strategy_id: str, *, user_id: str) -> StrategyDetail:
        strategy = self._repository.get_strategy(strategy_id, user_id=user_id)
        if strategy is None:
            raise ApiException("STRATEGY_NOT_FOUND", "Strategy not found.", 404)
        return strategy

    def create_strategy(self, payload: StrategyCreateRequest, *, user_id: str, trace_id: str | None = None) -> StrategyDetail:
        return self._repository.create_strategy(payload, user_id=user_id, trace_id=trace_id)

    def create_version(
        self,
        strategy_id: str,
        payload: StrategyVersionCreateRequest,
        *,
        user_id: str,
        trace_id: str | None = None,
    ) -> StrategyVersionItem:
        return self._repository.create_version(strategy_id, payload, user_id=user_id, trace_id=trace_id)

    def clone_version(self, strategy_id: str, version_id: str, *, user_id: str, trace_id: str | None = None) -> StrategyVersionItem:
        return self._repository.clone_version(strategy_id, version_id, user_id=user_id, trace_id=trace_id)
