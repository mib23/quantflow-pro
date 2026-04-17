from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_sync_engine
from app.core.settings import get_settings
from app.modules.backtests.repository import BacktestRepository
from app.modules.backtests.schemas import BacktestJobCreateRequest, BacktestJobItem, BacktestJobListData, BacktestResultItem
from app.workers.queue import enqueue_backtest_job


@lru_cache
def get_backtest_session_factory() -> Callable[[], Session]:
    engine = create_sync_engine(get_settings().database_url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@lru_cache
def get_backtest_service() -> "BacktestService":
    settings = get_settings()
    return BacktestService(
        BacktestRepository(get_backtest_session_factory()),
        enqueue_fn=lambda job_id: enqueue_backtest_job(job_id, database_url=settings.database_url),
    )


class BacktestService:
    def __init__(self, repository: BacktestRepository, enqueue_fn: Callable[[str], str | None] | None = None):
        self._repository = repository
        self._enqueue_fn = enqueue_fn or (lambda _job_id: None)

    def list_jobs(self, *, user_id: str) -> BacktestJobListData:
        items, total = self._repository.list_jobs(user_id=user_id)
        return BacktestJobListData(items=items, total=total)

    def get_job(self, job_id: str, *, user_id: str) -> BacktestJobItem:
        return self._repository.get_job(job_id, user_id=user_id)

    def create_job(self, payload: BacktestJobCreateRequest, *, user_id: str, trace_id: str | None = None) -> BacktestJobItem:
        job = self._repository.create_job(payload, user_id=user_id, trace_id=trace_id)
        queue_job_id = self._enqueue_fn(job.id)
        if queue_job_id is not None:
            self._repository.update_queue_job_id(job.id, queue_job_id=queue_job_id)
            self._repository.append_log(job.id, level="INFO", code="QUEUE_ATTACHED", message="Queue job attached.", details={"queue_job_id": queue_job_id})
        return self._repository.get_job(job.id, user_id=user_id)

    def cancel_job(self, job_id: str, *, user_id: str, trace_id: str | None = None) -> BacktestJobItem:
        return self._repository.cancel_job(job_id, user_id=user_id, trace_id=trace_id)

    def retry_job(self, job_id: str, *, user_id: str, trace_id: str | None = None) -> BacktestJobItem:
        retry_job = self._repository.retry_job(job_id, user_id=user_id, trace_id=trace_id)
        queue_job_id = self._enqueue_fn(retry_job.id)
        if queue_job_id is not None:
            self._repository.update_queue_job_id(retry_job.id, queue_job_id=queue_job_id)
            self._repository.append_log(
                retry_job.id,
                level="INFO",
                code="QUEUE_ATTACHED",
                message="Queue job attached.",
                details={"queue_job_id": queue_job_id},
            )
        return self._repository.get_job(retry_job.id, user_id=user_id)

    def get_result(self, job_id: str, *, user_id: str) -> BacktestResultItem:
        return self._repository.get_result(job_id, user_id=user_id)

    def get_report(self, job_id: str, *, user_id: str) -> dict[str, object]:
        return self.get_result(job_id, user_id=user_id).report
