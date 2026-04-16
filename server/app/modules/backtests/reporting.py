from __future__ import annotations

from datetime import UTC, datetime

from app.core.models import BacktestJobModel


def build_backtest_report(*, job: BacktestJobModel, strategy_name: str, version_tag: str, sample: dict[str, object]) -> dict[str, object]:
    generated_at = job.finished_at or job.started_at or datetime.now(UTC)
    return {
        "title": str(sample["title"]),
        "description": str(sample["description"]),
        "job_id": str(job.id),
        "strategy_id": str(job.strategy_id),
        "strategy_name": strategy_name,
        "strategy_version_tag": version_tag,
        "dataset_key": job.dataset_key,
        "status": job.status,
        "generated_at": generated_at.isoformat(),
        "metrics": dict(sample["metrics"]),
        "equity_curve": list(sample["equity_curve"]),
        "trades": list(sample["trades"]),
    }
