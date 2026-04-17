from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.models import BacktestJobModel, BacktestLogModel, BacktestResultModel, Base, StrategyModel, UserModel
from app.modules.backtests.executor import execute_backtest_job
from app.modules.backtests.schemas import BacktestJobCreateRequest, BacktestTimeRange
from app.modules.backtests.repository import BacktestRepository
from app.modules.backtests.service import BacktestService
from app.modules.strategies.repository import StrategyRepository
from app.modules.strategies.service import StrategyService
from app.modules.strategies.schemas import StrategyCreateRequest, StrategyVersionCreateRequest

USER_ID = "00000000-0000-0000-0000-000000000021"


def _build_session_factory(database_url: str):
    engine_kwargs = {"future": True}
    if database_url == "sqlite+pysqlite://":
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["poolclass"] = StaticPool
    else:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **engine_kwargs)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def _seed_user(session_factory) -> None:
    now = datetime(2026, 4, 16, 8, 0, tzinfo=UTC)
    with session_factory() as session:
        with session.begin():
            session.add(
                UserModel(
                    id=UUID(USER_ID),
                    email="worker@quantflow.local",
                    full_name="Worker Test User",
                    password_hash="hash",
                    role="RESEARCHER",
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
            )


def _seed_job(session_factory) -> tuple[BacktestService, str]:
    strategy_service = StrategyService(StrategyRepository(session_factory))
    backtest_service = BacktestService(BacktestRepository(session_factory))
    strategy = strategy_service.create_strategy(StrategyCreateRequest(name="Momentum Pulse"), user_id=USER_ID)
    version = strategy_service.create_version(
        strategy.id,
        StrategyVersionCreateRequest(code="def run(context):\n    return context", parameters={"lookback": 20}),
        user_id=USER_ID,
    )
    job = backtest_service.create_job(
        BacktestJobCreateRequest(
            strategy_version_id=version.id,
            symbols=["aapl"],
            time_range=BacktestTimeRange(start="2024-01-01T00:00:00Z", end="2024-03-31T00:00:00Z"),
            benchmark="spy",
            parameters={},
            dataset_key="demo-momentum",
        ),
        user_id=USER_ID,
    )
    return backtest_service, job.id


@pytest.fixture()
def sqlite_session_factory(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'backtests.db'}"
    session_factory = _build_session_factory(database_url)
    _seed_user(session_factory)
    return database_url, session_factory


def test_execute_backtest_job_writes_result_report_and_logs(sqlite_session_factory) -> None:
    database_url, session_factory = sqlite_session_factory
    _, job_id = _seed_job(session_factory)

    result = execute_backtest_job(job_id=job_id, database_url=database_url)

    assert result["job_id"] == job_id
    assert result["status"] == "SUCCEEDED"

    with session_factory() as session:
        job = session.execute(select(BacktestJobModel).where(BacktestJobModel.id == job_id)).scalars().one()
        stored_result = session.execute(select(BacktestResultModel).where(BacktestResultModel.job_id == job_id)).scalars().one()
        logs = session.execute(select(BacktestLogModel).where(BacktestLogModel.job_id == job_id)).scalars().all()

    assert job.status == "SUCCEEDED"
    assert job.started_at is not None
    assert job.finished_at is not None
    assert stored_result.report_format == "json"
    assert stored_result.metrics_summary["total_return"] == 0.126
    assert stored_result.report["title"] == "Backtest Report"
    assert [log.code for log in logs] == ["JOB_QUEUED", "JOB_RUNNING", "JOB_SUCCEEDED"]


def test_execute_backtest_job_is_idempotent_for_existing_result(sqlite_session_factory) -> None:
    database_url, session_factory = sqlite_session_factory
    _, job_id = _seed_job(session_factory)

    first = execute_backtest_job(job_id=job_id, database_url=database_url)
    second = execute_backtest_job(job_id=job_id, database_url=database_url)

    assert first["status"] == "SUCCEEDED"
    assert second["status"] == "SUCCEEDED"

    with session_factory() as session:
        results = session.execute(select(BacktestResultModel).where(BacktestResultModel.job_id == job_id)).scalars().all()

    assert len(results) == 1
    assert results[0].report["title"] == "Backtest Report"


def test_execute_backtest_job_skips_canceled_jobs(sqlite_session_factory) -> None:
    database_url, session_factory = sqlite_session_factory
    _, job_id = _seed_job(session_factory)

    with session_factory() as session:
        with session.begin():
            job = session.execute(select(BacktestJobModel).where(BacktestJobModel.id == job_id)).scalars().one()
            job.status = "CANCELED"
            job.cancellation_requested = True

    result = execute_backtest_job(job_id=job_id, database_url=database_url)

    assert result["status"] == "CANCELED"

    with session_factory() as session:
        results = session.execute(select(BacktestResultModel).where(BacktestResultModel.job_id == job_id)).scalars().all()
        logs = session.execute(select(BacktestLogModel).where(BacktestLogModel.job_id == job_id)).scalars().all()

    assert results == []
    assert logs[-1].code == "JOB_CANCELED"
