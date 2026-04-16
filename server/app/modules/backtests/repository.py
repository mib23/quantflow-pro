from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiException
from app.core.ids import coerce_uuid
from app.core.models import (
    AuditLogModel,
    BacktestJobModel,
    BacktestLogModel,
    BacktestResultModel,
    StrategyModel,
    StrategyVersionModel,
)
from app.modules.backtests.schemas import BacktestJobCreateRequest, BacktestJobItem, BacktestLogItem, BacktestResultItem
from app.modules.strategies.schemas import StrategyVersionItem


class BacktestRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def get_execution_context(self, job_id: str) -> tuple[BacktestJobModel, str, int]:
        with self._session_factory() as session:
            row = session.execute(
                select(
                    BacktestJobModel,
                    StrategyModel.name,
                    StrategyVersionModel.version_number,
                )
                .join(StrategyModel, StrategyModel.id == BacktestJobModel.strategy_id)
                .join(StrategyVersionModel, StrategyVersionModel.id == BacktestJobModel.strategy_version_id)
                .where(BacktestJobModel.id == coerce_uuid(job_id))
            ).first()
        if row is None:
            raise ApiException("BACKTEST_JOB_NOT_FOUND", "Backtest job not found.", status.HTTP_404_NOT_FOUND)
        job_row, strategy_name, version_number = row
        return job_row, str(strategy_name), int(version_number)

    def get_owned_version(self, version_id: str, *, user_id: str) -> StrategyVersionItem:
        with self._session_factory() as session:
            row = session.execute(
                select(StrategyVersionModel)
                .join(StrategyModel, StrategyModel.id == StrategyVersionModel.strategy_id)
                .where(
                    StrategyVersionModel.id == coerce_uuid(version_id),
                    StrategyModel.owner_user_id == coerce_uuid(user_id),
                )
            ).scalars().first()
        if row is None:
            raise ApiException("STRATEGY_VERSION_NOT_FOUND", "Strategy version not found.", status.HTTP_404_NOT_FOUND)
        return StrategyVersionItem(
            id=str(row.id),
            strategy_id=str(row.strategy_id),
            version_number=int(row.version_number),
            version_tag=f"v{int(row.version_number)}",
            code=row.code_snapshot,
            parameters=dict(row.parameters_snapshot or {}),
            version_note=row.version_note,
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

    def create_job(
        self,
        payload: BacktestJobCreateRequest,
        *,
        user_id: str,
        trace_id: str | None = None,
    ) -> BacktestJobItem:
        version = self.get_owned_version(payload.strategy_version_id, user_id=user_id)
        now = datetime.now(UTC)
        with self._session_factory() as session:
            with session.begin():
                strategy = session.execute(select(StrategyModel).where(StrategyModel.id == coerce_uuid(version.strategy_id))).scalars().first()
                if strategy is None:
                    raise ApiException("STRATEGY_NOT_FOUND", "Strategy not found.", status.HTTP_404_NOT_FOUND)
                row = BacktestJobModel(
                    id=uuid4(),
                    strategy_id=strategy.id,
                    strategy_version_id=coerce_uuid(version.id),
                    submitted_by=coerce_uuid(user_id),
                    status="QUEUED",
                    queue_name="backtests",
                    queue_job_id=None,
                    dataset_key=payload.dataset_key,
                    symbols=[symbol.upper() for symbol in payload.symbols],
                    parameters_snapshot=payload.parameters or version.parameters,
                    benchmark=payload.benchmark.upper() if payload.benchmark else None,
                    time_range={
                        "start": payload.time_range.start.isoformat(),
                        "end": payload.time_range.end.isoformat(),
                    },
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                session.flush()
                session.add(
                    BacktestLogModel(
                        id=uuid4(),
                        job_id=row.id,
                        level="INFO",
                        code="JOB_QUEUED",
                        message="Backtest job queued.",
                        details={"dataset_key": payload.dataset_key},
                        created_at=now,
                    )
                )
                self._append_audit_log(
                    session,
                    user_id=user_id,
                    resource_type="BACKTEST_JOB",
                    resource_id=str(row.id),
                    action="BACKTEST_SUBMITTED",
                    after_state={"strategy_version_id": version.id, "status": "QUEUED"},
                    trace_id=trace_id,
                )
        return self.get_job(str(row.id), user_id=user_id)

    def update_queue_job_id(self, job_id: str, *, queue_job_id: str | None) -> None:
        with self._session_factory() as session:
            with session.begin():
                row = session.execute(select(BacktestJobModel).where(BacktestJobModel.id == coerce_uuid(job_id))).scalars().first()
                if row is None:
                    raise ApiException("BACKTEST_JOB_NOT_FOUND", "Backtest job not found.", status.HTTP_404_NOT_FOUND)
                row.queue_job_id = queue_job_id
                row.updated_at = datetime.now(UTC)

    def list_jobs(self, *, user_id: str) -> tuple[list[BacktestJobItem], int]:
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    BacktestJobModel,
                    StrategyModel.name,
                    StrategyVersionModel.version_number,
                )
                .join(StrategyModel, StrategyModel.id == BacktestJobModel.strategy_id)
                .join(StrategyVersionModel, StrategyVersionModel.id == BacktestJobModel.strategy_version_id)
                .where(StrategyModel.owner_user_id == coerce_uuid(user_id))
                .order_by(BacktestJobModel.created_at.desc(), BacktestJobModel.id.desc())
            ).all()
        items = [
            self._serialize_job(job_row, strategy_name, version_number, self.list_logs(str(job_row.id)), self.has_result(str(job_row.id)))
            for job_row, strategy_name, version_number in rows
        ]
        return items, len(items)

    def get_job(self, job_id: str, *, user_id: str) -> BacktestJobItem:
        with self._session_factory() as session:
            row = session.execute(
                select(
                    BacktestJobModel,
                    StrategyModel.name,
                    StrategyVersionModel.version_number,
                )
                .join(StrategyModel, StrategyModel.id == BacktestJobModel.strategy_id)
                .join(StrategyVersionModel, StrategyVersionModel.id == BacktestJobModel.strategy_version_id)
                .where(
                    BacktestJobModel.id == coerce_uuid(job_id),
                    StrategyModel.owner_user_id == coerce_uuid(user_id),
                )
            ).first()
        if row is None:
            raise ApiException("BACKTEST_JOB_NOT_FOUND", "Backtest job not found.", status.HTTP_404_NOT_FOUND)
        job_row, strategy_name, version_number = row
        return self._serialize_job(job_row, strategy_name, version_number, self.list_logs(job_id), self.has_result(job_id))

    def cancel_job(self, job_id: str, *, user_id: str, trace_id: str | None = None) -> BacktestJobItem:
        with self._session_factory() as session:
            with session.begin():
                row = session.execute(
                    select(BacktestJobModel, StrategyModel.owner_user_id)
                    .join(StrategyModel, StrategyModel.id == BacktestJobModel.strategy_id)
                    .where(BacktestJobModel.id == coerce_uuid(job_id))
                ).first()
                if row is None or str(row[1]) != user_id:
                    raise ApiException("BACKTEST_JOB_NOT_FOUND", "Backtest job not found.", status.HTTP_404_NOT_FOUND)
                job_row, _owner_id = row
                if job_row.status in {"SUCCEEDED", "FAILED", "CANCELED"}:
                    return self.get_job(job_id, user_id=user_id)
                job_row.status = "CANCELED"
                job_row.cancellation_requested = True
                job_row.finished_at = datetime.now(UTC)
                job_row.updated_at = datetime.now(UTC)
                session.add(
                    BacktestLogModel(
                        id=uuid4(),
                        job_id=job_row.id,
                        level="WARN",
                        code="JOB_CANCELED",
                        message="Backtest job canceled.",
                        details={},
                        created_at=datetime.now(UTC),
                    )
                )
                self._append_audit_log(
                    session,
                    user_id=user_id,
                    resource_type="BACKTEST_JOB",
                    resource_id=str(job_row.id),
                    action="BACKTEST_CANCELED",
                    after_state={"status": "CANCELED"},
                    trace_id=trace_id,
                )
        return self.get_job(job_id, user_id=user_id)

    def retry_job(self, job_id: str, *, user_id: str, trace_id: str | None = None) -> BacktestJobItem:
        with self._session_factory() as session:
            row = session.execute(
                select(BacktestJobModel, StrategyModel.owner_user_id)
                .join(StrategyModel, StrategyModel.id == BacktestJobModel.strategy_id)
                .where(BacktestJobModel.id == coerce_uuid(job_id))
            ).first()
        if row is None or str(row[1]) != user_id:
            raise ApiException("BACKTEST_JOB_NOT_FOUND", "Backtest job not found.", status.HTTP_404_NOT_FOUND)
        existing, _owner_id = row
        payload = BacktestJobCreateRequest.model_validate(
            {
                "strategy_version_id": str(existing.strategy_version_id),
                "symbols": list(existing.symbols or []),
                "time_range": dict(existing.time_range or {}),
                "benchmark": existing.benchmark,
                "parameters": dict(existing.parameters_snapshot or {}),
                "dataset_key": existing.dataset_key,
            }
        )
        retry_job = self.create_job(payload, user_id=user_id, trace_id=trace_id)
        with self._session_factory() as session:
            with session.begin():
                retry_row = session.execute(select(BacktestJobModel).where(BacktestJobModel.id == coerce_uuid(retry_job.id))).scalars().first()
                if retry_row is not None:
                    retry_row.retry_of_job_id = existing.id
                    retry_row.updated_at = datetime.now(UTC)
        return self.get_job(retry_job.id, user_id=user_id)

    def list_logs(self, job_id: str) -> list[BacktestLogItem]:
        with self._session_factory() as session:
            rows = session.execute(
                select(BacktestLogModel)
                .where(BacktestLogModel.job_id == coerce_uuid(job_id))
                .order_by(BacktestLogModel.created_at.asc(), BacktestLogModel.id.asc())
            ).scalars().all()
        return [
            BacktestLogItem(
                id=str(row.id),
                level=row.level,
                code=row.code,
                message=row.message,
                details=dict(row.details or {}),
                created_at=row.created_at,
            )
            for row in rows
        ]

    def get_result(self, job_id: str, *, user_id: str) -> BacktestResultItem:
        self.get_job(job_id, user_id=user_id)
        with self._session_factory() as session:
            row = session.execute(select(BacktestResultModel).where(BacktestResultModel.job_id == coerce_uuid(job_id))).scalars().first()
        if row is None:
            raise ApiException("BACKTEST_RESULT_NOT_FOUND", "Backtest result not found.", status.HTTP_404_NOT_FOUND)
        return BacktestResultItem(
            job_id=str(row.job_id),
            metrics=dict(row.metrics_summary or {}),
            equity_curve=list(row.equity_curve or []),
            trades=list(row.trades or []),
            report=dict(row.report or {}),
            report_format=row.report_format,
            generated_at=row.generated_at,
        )

    def has_result(self, job_id: str) -> bool:
        with self._session_factory() as session:
            return bool(session.execute(select(exists().where(BacktestResultModel.job_id == coerce_uuid(job_id)))).scalar())

    def save_result(
        self,
        job_id: str,
        *,
        metrics: dict[str, object],
        equity_curve: list[dict[str, object]],
        trades: list[dict[str, object]],
        report: dict[str, object],
    ) -> None:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            with session.begin():
                result = session.execute(select(BacktestResultModel).where(BacktestResultModel.job_id == coerce_uuid(job_id))).scalars().first()
                if result is None:
                    result = BacktestResultModel(
                        id=uuid4(),
                        job_id=coerce_uuid(job_id),
                        metrics_summary=metrics,
                        equity_curve=equity_curve,
                        trades=trades,
                        report=report,
                        report_format="json",
                        generated_at=now,
                    )
                    session.add(result)
                else:
                    result.metrics_summary = metrics
                    result.equity_curve = equity_curve
                    result.trades = trades
                    result.report = report
                    result.generated_at = now

    def save_result_if_absent(
        self,
        job_id: str,
        *,
        metrics: dict[str, object],
        equity_curve: list[dict[str, object]],
        trades: list[dict[str, object]],
        report: dict[str, object],
    ) -> bool:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            with session.begin():
                result = session.execute(select(BacktestResultModel).where(BacktestResultModel.job_id == coerce_uuid(job_id))).scalars().first()
                if result is not None:
                    return False
                session.add(
                    BacktestResultModel(
                        id=uuid4(),
                        job_id=coerce_uuid(job_id),
                        metrics_summary=metrics,
                        equity_curve=equity_curve,
                        trades=trades,
                        report=report,
                        report_format="json",
                        generated_at=now,
                    )
                )
                return True

    def append_log(self, job_id: str, *, level: str, code: str, message: str, details: dict[str, object] | None = None) -> None:
        with self._session_factory() as session:
            with session.begin():
                session.add(
                    BacktestLogModel(
                        id=uuid4(),
                        job_id=coerce_uuid(job_id),
                        level=level,
                        code=code,
                        message=message,
                        details=details or {},
                        created_at=datetime.now(UTC),
                    )
                )

    def mark_job_running(self, job_id: str) -> None:
        self._set_job_state(job_id, status_value="RUNNING", started_at=datetime.now(UTC), finished_at=None)

    def mark_job_succeeded(self, job_id: str) -> None:
        self._set_job_state(job_id, status_value="SUCCEEDED", finished_at=datetime.now(UTC), failure_code=None, failure_reason=None)

    def mark_job_failed(self, job_id: str, *, failure_code: str, failure_reason: str) -> None:
        self._set_job_state(
            job_id,
            status_value="FAILED",
            finished_at=datetime.now(UTC),
            failure_code=failure_code,
            failure_reason=failure_reason,
        )

    def _set_job_state(
        self,
        job_id: str,
        *,
        status_value: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        failure_code: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        with self._session_factory() as session:
            with session.begin():
                row = session.execute(select(BacktestJobModel).where(BacktestJobModel.id == coerce_uuid(job_id))).scalars().first()
                if row is None:
                    raise ApiException("BACKTEST_JOB_NOT_FOUND", "Backtest job not found.", status.HTTP_404_NOT_FOUND)
                row.status = status_value
                row.started_at = started_at if started_at is not None else row.started_at
                row.finished_at = finished_at
                row.failure_code = failure_code
                row.failure_reason = failure_reason
                row.updated_at = datetime.now(UTC)

    @staticmethod
    def _serialize_job(
        row: BacktestJobModel,
        strategy_name: str,
        version_number: int,
        logs: list[BacktestLogItem],
        result_available: bool,
    ) -> BacktestJobItem:
        return BacktestJobItem(
            id=str(row.id),
            strategy_id=str(row.strategy_id),
            strategy_version_id=str(row.strategy_version_id),
            strategy_name=strategy_name,
            strategy_version_tag=f"v{int(version_number)}",
            status=row.status,
            queue_name=row.queue_name,
            queue_job_id=row.queue_job_id,
            symbols=[str(symbol).upper() for symbol in (row.symbols or [])],
            benchmark=row.benchmark,
            parameters=dict(row.parameters_snapshot or {}),
            time_range={key: str(value) for key, value in dict(row.time_range or {}).items()},
            failure_code=row.failure_code,
            failure_reason=row.failure_reason,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            result_available=result_available,
            logs=logs,
        )

    @staticmethod
    def _append_audit_log(
        session: Session,
        *,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        before_state: dict[str, object] | None = None,
        after_state: dict[str, object] | None = None,
        trace_id: str | None = None,
    ) -> None:
        session.add(
            AuditLogModel(
                id=uuid4(),
                user_id=coerce_uuid(user_id),
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                before_state=before_state,
                after_state=after_state,
                trace_id=trace_id,
                created_at=datetime.now(UTC),
            )
        )
