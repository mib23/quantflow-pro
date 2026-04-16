from __future__ import annotations

from functools import lru_cache

from app.modules.strategies.repository import StrategyRepository, get_strategy_session_factory


@lru_cache
def get_backtest_repository() -> StrategyRepository:
    return StrategyRepository(get_strategy_session_factory())


def get_backtest_service() -> "BacktestService":
    return BacktestService(get_backtest_repository())


class BacktestService:
    def __init__(self, repository: StrategyRepository):
        self._repository = repository

    def list_jobs(self, *, user_id: str, page: int = 1, page_size: int = 20):
        return self._repository.list_jobs(user_id=user_id, page=page, page_size=page_size)

    def create_job(self, payload, *, submitted_by: str):
        return self._repository.create_job(payload, submitted_by=submitted_by)

    def get_job(self, job_id: str, *, user_id: str):
        return self._repository.get_job(job_id, user_id=user_id)

    def cancel_job(self, job_id: str, *, user_id: str):
        return self._repository.cancel_job(job_id, user_id=user_id)

    def get_result(self, job_id: str, *, user_id: str):
        return self._repository.get_result(job_id, user_id=user_id)

    def get_report(self, job_id: str, *, user_id: str):
        return self._repository.get_report(job_id, user_id=user_id)

