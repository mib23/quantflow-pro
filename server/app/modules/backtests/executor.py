from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import sessionmaker

from app.core.database import create_sync_engine
from app.core.settings import get_settings
from app.modules.backtests.reporting import build_backtest_report
from app.modules.backtests.repository import BacktestRepository
from app.modules.backtests.sample_data import load_sample_backtest


def build_backtest_session_factory(database_url: str | None = None) -> sessionmaker:
    engine = create_sync_engine(database_url or get_settings().database_url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def execute_backtest_job(*, job_id: str, database_url: str | None = None) -> dict[str, object]:
    repository = BacktestRepository(build_backtest_session_factory(database_url))
    job, strategy_name, version_number = repository.get_execution_context(job_id)
    version_tag = f"v{int(version_number)}"

    if job.status == "SUCCEEDED":
        return {"job_id": job_id, "status": "SUCCEEDED"}

    if job.status == "CANCELED" or bool(job.cancellation_requested):
        repository.append_log(
            job_id,
            level="WARN",
            code="JOB_CANCELED",
            message="Backtest job was canceled before execution.",
            details={},
        )
        return {"job_id": job_id, "status": "CANCELED"}

    repository.mark_job_running(job_id)
    repository.append_log(
        job_id,
        level="INFO",
        code="JOB_RUNNING",
        message="Backtest job started.",
        details={"dataset_key": job.dataset_key},
    )

    try:
        sample = load_sample_backtest(job.dataset_key)
        completed_at = datetime.now(UTC)
        report = build_backtest_report(job=job, strategy_name=strategy_name, version_tag=version_tag, sample=sample)
        report["status"] = "SUCCEEDED"
        report["generated_at"] = completed_at.isoformat()
        repository.save_result_if_absent(
            job_id,
            metrics=dict(sample["metrics"]),
            equity_curve=list(sample["equity_curve"]),
            trades=list(sample["trades"]),
            report=report,
        )
        repository.mark_job_succeeded(job_id)
        repository.append_log(
            job_id,
            level="INFO",
            code="JOB_SUCCEEDED",
            message="Backtest job finished successfully.",
            details={"version_tag": version_tag},
        )
        return {"job_id": job_id, "status": "SUCCEEDED"}
    except Exception as exc:  # pragma: no cover - exercised through worker tests
        repository.mark_job_failed(job_id, failure_code="EXECUTION_FAILED", failure_reason=str(exc))
        repository.append_log(
            job_id,
            level="ERROR",
            code="JOB_FAILED",
            message="Backtest job failed.",
            details={"error": str(exc)},
        )
        return {"job_id": job_id, "status": "FAILED", "failure_code": "EXECUTION_FAILED", "failure_reason": str(exc)}
