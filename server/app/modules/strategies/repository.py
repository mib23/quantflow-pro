from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.core.database import create_sync_engine
from app.core.exceptions import ApiException
from app.core.models import (
    BacktestJobModel,
    BacktestLogModel,
    BacktestResultModel,
    StrategyModel,
    StrategyVersionModel,
)
from app.core.settings import get_settings
from app.modules.strategies.schemas import (
    BacktestJobCreateRequest,
    BacktestJobDetail,
    BacktestJobItem,
    BacktestJobListResponse,
    BacktestLogItem,
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
def get_strategy_session_factory() -> Callable[[], Session]:
    settings = get_settings()
    engine = create_sync_engine(settings.database_url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class StrategyRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None):
        self._session_factory = session_factory or get_strategy_session_factory()

    def list_strategies(self, *, user_id: str, page: int = 1, page_size: int = 20) -> StrategyListResponse:
        with self._session_factory() as session:
            query = select(StrategyModel).where(StrategyModel.created_by == user_id).order_by(StrategyModel.updated_at.desc())
            total = session.execute(select(func.count()).select_from(query.subquery())).scalar_one()
            items = session.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
            return StrategyListResponse(
                items=[self._strategy_to_item(session, strategy) for strategy in items],
                page=page,
                page_size=page_size,
                total=total,
            )

    def create_strategy(self, payload: StrategyCreateRequest, *, created_by: str) -> StrategyItem:
        with self._session_factory() as session:
            strategy = StrategyModel(
                id=str(uuid4()),
                created_by=created_by,
                name=payload.name,
                description=payload.description,
                status=payload.status,
                default_parameters=payload.default_parameters,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(strategy)
            session.commit()
            session.refresh(strategy)
            return self._strategy_to_item(session, strategy)

    def get_strategy(self, strategy_id: str, *, user_id: str) -> StrategyDetail:
        with self._session_factory() as session:
            strategy = self._get_owned_strategy(session, strategy_id, user_id)
            versions = self._list_versions(session, strategy_id)
            return StrategyDetail(**self._strategy_to_item(session, strategy).model_dump(), versions=versions)

    def create_version(
        self,
        strategy_id: str,
        payload: StrategyVersionCreateRequest,
        *,
        created_by: str,
    ) -> StrategyVersionItem:
        with self._session_factory() as session:
            strategy = self._get_owned_strategy(session, strategy_id, created_by)
            next_version = self._next_version_number(session, strategy_id)
            version = StrategyVersionModel(
                id=str(uuid4()),
                strategy_id=strategy_id,
                version_number=next_version,
                code_snapshot=payload.code_snapshot,
                parameter_template=payload.parameter_template,
                change_reason=payload.change_reason,
                created_by=created_by,
                created_at=datetime.now(timezone.utc),
            )
            strategy.latest_version_id = version.id
            if strategy.default_version_id is None:
                strategy.default_version_id = version.id
            strategy.updated_at = datetime.now(timezone.utc)
            session.add(version)
            session.commit()
            session.refresh(version)
            return self._version_to_item(version)

    def clone_version(
        self,
        strategy_id: str,
        version_id: str,
        payload: StrategyVersionCloneRequest,
        *,
        created_by: str,
    ) -> StrategyVersionItem:
        with self._session_factory() as session:
            strategy = self._get_owned_strategy(session, strategy_id, created_by)
            source = self._get_version(session, version_id, strategy_id)
            next_version = self._next_version_number(session, strategy_id)
            cloned = StrategyVersionModel(
                id=str(uuid4()),
                strategy_id=strategy_id,
                version_number=next_version,
                code_snapshot=source.code_snapshot,
                parameter_template=source.parameter_template,
                change_reason=payload.change_reason or source.change_reason,
                created_by=created_by,
                created_at=datetime.now(timezone.utc),
            )
            strategy.latest_version_id = cloned.id
            strategy.updated_at = datetime.now(timezone.utc)
            session.add(cloned)
            session.commit()
            session.refresh(cloned)
            return self._version_to_item(cloned)

    def list_jobs(self, *, user_id: str, page: int = 1, page_size: int = 20) -> BacktestJobListResponse:
        with self._session_factory() as session:
            query = select(BacktestJobModel).where(BacktestJobModel.submitted_by == user_id).order_by(BacktestJobModel.submitted_at.desc())
            total = session.execute(select(func.count()).select_from(query.subquery())).scalar_one()
            items = session.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
            return BacktestJobListResponse(
                items=[self._job_to_item(job) for job in items],
                page=page,
                page_size=page_size,
                total=total,
            )

    def create_job(self, payload: BacktestJobCreateRequest, *, submitted_by: str) -> BacktestJobItem:
        with self._session_factory() as session:
            strategy_version = self._get_owned_version_by_id(session, payload.strategy_version_id, submitted_by)
            strategy = session.get(StrategyModel, strategy_version.strategy_id)
            if strategy is None:
                raise ApiException("STRATEGY_NOT_FOUND", "Strategy not found.", status.HTTP_404_NOT_FOUND)
            now = datetime.now(timezone.utc)
            job = BacktestJobModel(
                id=str(uuid4()),
                strategy_id=strategy.id,
                strategy_version_id=strategy_version.id,
                submitted_by=submitted_by,
                name=payload.name,
                status="QUEUED",
                start_date=payload.start_date,
                end_date=payload.end_date,
                symbols=payload.symbols,
                benchmark_symbol=payload.benchmark_symbol,
                parameters_snapshot=payload.parameters_snapshot,
                queue_name=payload.queue_name,
                execution_environment=payload.execution_environment,
                submitted_at=now,
                updated_at=now,
            )
            session.add(job)
            session.add(
                BacktestLogModel(
                    id=str(uuid4()),
                    backtest_job_id=job.id,
                    level="INFO",
                    message="Backtest queued.",
                    trace_id=None,
                    created_at=now,
                )
            )
            session.commit()
            session.refresh(job)
            return self._job_to_item(job)

    def get_job(self, job_id: str, *, user_id: str) -> BacktestJobDetail:
        with self._session_factory() as session:
            job = self._get_owned_job(session, job_id, user_id)
            return BacktestJobDetail(**self._job_to_item(job).model_dump(), logs=self._list_logs(session, job.id))

    def cancel_job(self, job_id: str, *, user_id: str) -> BacktestJobItem:
        with self._session_factory() as session:
            job = self._get_owned_job(session, job_id, user_id)
            if job.status in {"SUCCEEDED", "FAILED", "CANCELED"}:
                return self._job_to_item(job)
            now = datetime.now(timezone.utc)
            job.status = "CANCELED"
            job.canceled_at = now
            job.finished_at = now
            job.updated_at = now
            session.add(
                BacktestLogModel(
                    id=str(uuid4()),
                    backtest_job_id=job.id,
                    level="INFO",
                    message="Backtest canceled.",
                    trace_id=None,
                    created_at=now,
                )
            )
            session.commit()
            session.refresh(job)
            return self._job_to_item(job)

    def get_result(self, job_id: str, *, user_id: str) -> BacktestResultItem:
        with self._session_factory() as session:
            self._get_owned_job(session, job_id, user_id)
            result = session.execute(select(BacktestResultModel).where(BacktestResultModel.backtest_job_id == job_id)).scalar_one_or_none()
            if result is None:
                raise ApiException("BACKTEST_RESULT_NOT_FOUND", "Backtest result not found.", status.HTTP_404_NOT_FOUND)
            return self._result_to_item(result)

    def get_report(self, job_id: str, *, user_id: str) -> BacktestReportItem:
        with self._session_factory() as session:
            self._get_owned_job(session, job_id, user_id)
            result = session.execute(select(BacktestResultModel).where(BacktestResultModel.backtest_job_id == job_id)).scalar_one_or_none()
            if result is None:
                raise ApiException("BACKTEST_REPORT_NOT_FOUND", "Backtest report not found.", status.HTTP_404_NOT_FOUND)
            return BacktestReportItem(
                backtest_job_id=result.backtest_job_id,
                report_format=result.report_format,
                report_body=result.report_body,
                created_at=result.created_at,
                updated_at=result.updated_at,
            )

    def _strategy_to_item(self, session: Session, strategy: StrategyModel) -> StrategyItem:
        version_count = session.execute(
            select(func.count()).select_from(StrategyVersionModel).where(StrategyVersionModel.strategy_id == strategy.id)
        ).scalar_one()
        return StrategyItem(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            status=strategy.status,
            default_parameters=strategy.default_parameters or {},
            default_version_id=strategy.default_version_id,
            latest_version_id=strategy.latest_version_id,
            created_by=strategy.created_by,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
            archived_at=strategy.archived_at,
            version_count=version_count,
        )

    def _version_to_item(self, version: StrategyVersionModel) -> StrategyVersionItem:
        return StrategyVersionItem(
            id=version.id,
            strategy_id=version.strategy_id,
            version_number=version.version_number,
            code_snapshot=version.code_snapshot or {},
            parameter_template=version.parameter_template or {},
            change_reason=version.change_reason,
            created_by=version.created_by,
            created_at=version.created_at,
        )

    def _list_versions(self, session: Session, strategy_id: str) -> list[StrategyVersionItem]:
        versions = session.execute(
            select(StrategyVersionModel)
            .where(StrategyVersionModel.strategy_id == strategy_id)
            .order_by(StrategyVersionModel.version_number.asc())
        ).scalars().all()
        return [self._version_to_item(version) for version in versions]

    def _job_to_item(self, job: BacktestJobModel) -> BacktestJobItem:
        return BacktestJobItem(
            id=job.id,
            strategy_id=job.strategy_id,
            strategy_version_id=job.strategy_version_id,
            submitted_by=job.submitted_by,
            name=job.name,
            status=job.status,
            start_date=job.start_date,
            end_date=job.end_date,
            symbols=job.symbols or [],
            benchmark_symbol=job.benchmark_symbol,
            parameters_snapshot=job.parameters_snapshot or {},
            queue_name=job.queue_name,
            execution_environment=job.execution_environment,
            failure_code=job.failure_code,
            failure_message=job.failure_message,
            submitted_at=job.submitted_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            canceled_at=job.canceled_at,
            updated_at=job.updated_at,
        )

    def _result_to_item(self, result: BacktestResultModel) -> BacktestResultItem:
        return BacktestResultItem(
            id=result.id,
            backtest_job_id=result.backtest_job_id,
            summary_metrics=result.summary_metrics or {},
            equity_curve=result.equity_curve or [],
            trade_summary=result.trade_summary or [],
            report_format=result.report_format,
            report_body=result.report_body or {},
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    def _list_logs(self, session: Session, job_id: str) -> list[BacktestLogItem]:
        logs = session.execute(
            select(BacktestLogModel).where(BacktestLogModel.backtest_job_id == job_id).order_by(BacktestLogModel.created_at.asc())
        ).scalars().all()
        return [
            BacktestLogItem(
                id=log.id,
                backtest_job_id=log.backtest_job_id,
                level=log.level,
                message=log.message,
                trace_id=log.trace_id,
                created_at=log.created_at,
            )
            for log in logs
        ]

    def _get_owned_strategy(self, session: Session, strategy_id: str, user_id: str) -> StrategyModel:
        strategy = session.get(StrategyModel, strategy_id)
        if strategy is None or strategy.created_by != user_id:
            raise ApiException("STRATEGY_NOT_FOUND", "Strategy not found.", status.HTTP_404_NOT_FOUND)
        return strategy

    def _get_version(self, session: Session, version_id: str, strategy_id: str) -> StrategyVersionModel:
        version = session.get(StrategyVersionModel, version_id)
        if version is None or version.strategy_id != strategy_id:
            raise ApiException("STRATEGY_VERSION_NOT_FOUND", "Strategy version not found.", status.HTTP_404_NOT_FOUND)
        return version

    def _get_owned_version_by_id(self, session: Session, version_id: str, user_id: str) -> StrategyVersionModel:
        version = session.get(StrategyVersionModel, version_id)
        if version is None:
            raise ApiException("STRATEGY_VERSION_NOT_FOUND", "Strategy version not found.", status.HTTP_404_NOT_FOUND)
        strategy = session.get(StrategyModel, version.strategy_id)
        if strategy is None or strategy.created_by != user_id:
            raise ApiException("STRATEGY_VERSION_NOT_FOUND", "Strategy version not found.", status.HTTP_404_NOT_FOUND)
        return version

    def _get_owned_job(self, session: Session, job_id: str, user_id: str) -> BacktestJobModel:
        job = session.get(BacktestJobModel, job_id)
        if job is None or job.submitted_by != user_id:
            raise ApiException("BACKTEST_JOB_NOT_FOUND", "Backtest job not found.", status.HTTP_404_NOT_FOUND)
        return job

    def _next_version_number(self, session: Session, strategy_id: str) -> int:
        max_version = session.execute(
            select(func.max(StrategyVersionModel.version_number)).where(StrategyVersionModel.strategy_id == strategy_id)
        ).scalar_one()
        return int(max_version or 0) + 1

