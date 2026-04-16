from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.models import Base, UserModel
from app.main import app
from app.modules.backtests.service import BacktestService, get_backtest_service
from app.modules.strategies.repository import StrategyRepository
from app.modules.strategies.service import StrategyService, get_strategy_service


def _build_session_factory():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def _seed_user(session_factory) -> str:
    user_id = UUID("00000000-0000-0000-0000-000000001001")
    now = datetime(2026, 4, 16, 9, 0, tzinfo=UTC)
    with session_factory() as session:
        with session.begin():
            session.add(
                UserModel(
                    id=user_id,
                    email="researcher@quantflow.local",
                    full_name="Research User",
                    password_hash="hash",
                    role="RESEARCHER",
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
            )
    return str(user_id)


def _override_strategy_services(session_factory) -> None:
    repository = StrategyRepository(session_factory)
    strategy_service = StrategyService(repository)
    backtest_service = BacktestService(repository)
    os.environ["QF_DATABASE_URL"] = "sqlite+pysqlite://"
    app.dependency_overrides[get_strategy_service] = lambda: strategy_service
    app.dependency_overrides[get_backtest_service] = lambda: backtest_service


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_strategy_version_lifecycle_exposes_frontend_friendly_payloads() -> None:
    session_factory = _build_session_factory()
    user_id = _seed_user(session_factory)
    _override_strategy_services(session_factory)

    try:
        client = TestClient(app)

        strategy_response = client.post(
            "/api/v1/strategies",
            headers={"X-User-Id": user_id},
            json={
                "name": "Mean Reversion",
                "description": "Starter research strategy",
                "status": "DRAFT",
                "default_parameters": {
                    "lookback_days": 20,
                    "entry_threshold": 1.5,
                },
            },
        )
        assert strategy_response.status_code == 200
        strategy = strategy_response.json()["data"]
        assert strategy["name"] == "Mean Reversion"
        assert strategy["status"] == "DRAFT"
        assert strategy["default_version_id"] is None

        strategy_id = strategy["id"]

        version_response = client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            headers={"X-User-Id": user_id},
            json={
                "code_snapshot": {"source": "print('hello')"},
                "parameter_template": {"lookback_days": 20, "entry_threshold": 1.5},
                "change_reason": "Initial research draft",
            },
        )
        assert version_response.status_code == 200
        version = version_response.json()["data"]
        assert version["strategy_id"] == strategy_id
        assert version["version_number"] == 1

        clone_response = client.post(
            f"/api/v1/strategies/{strategy_id}/versions/{version['id']}/clone",
            headers={"X-User-Id": user_id},
            json={"change_reason": "Experiment with longer lookback"},
        )
        assert clone_response.status_code == 200
        cloned_version = clone_response.json()["data"]
        assert cloned_version["strategy_id"] == strategy_id
        assert cloned_version["version_number"] == 2
        assert cloned_version["parameter_template"] == version["parameter_template"]

        list_response = client.get("/api/v1/strategies", headers={"X-User-Id": user_id})
        assert list_response.status_code == 200
        items = list_response.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["latest_version_id"] == cloned_version["id"]

        detail_response = client.get(f"/api/v1/strategies/{strategy_id}", headers={"X-User-Id": user_id})
        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]
        assert detail["versions"][0]["id"] == version["id"]
    finally:
        _clear_overrides()


def test_backtest_job_lifecycle_supports_queue_cancel_and_lookup() -> None:
    session_factory = _build_session_factory()
    user_id = _seed_user(session_factory)
    _override_strategy_services(session_factory)

    try:
        client = TestClient(app)

        strategy_response = client.post(
            "/api/v1/strategies",
            headers={"X-User-Id": user_id},
            json={
                "name": "Momentum",
                "description": "Starter backtest strategy",
                "status": "DRAFT",
                "default_parameters": {"window": 10},
            },
        )
        strategy_id = strategy_response.json()["data"]["id"]
        version_response = client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            headers={"X-User-Id": user_id},
            json={
                "code_snapshot": {"source": "print('momentum')"},
                "parameter_template": {"window": 10},
                "change_reason": "Initial version",
            },
        )
        version_id = version_response.json()["data"]["id"]

        job_response = client.post(
            "/api/v1/backtests",
            headers={"X-User-Id": user_id},
            json={
                "strategy_version_id": version_id,
                "name": "Momentum 2024 sample",
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "symbols": ["AAPL", "MSFT"],
                "benchmark_symbol": "SPY",
                "parameters_snapshot": {"window": 10},
            },
        )
        assert job_response.status_code == 200
        job = job_response.json()["data"]
        assert job["status"] == "QUEUED"
        assert job["strategy_version_id"] == version_id

        list_response = client.get("/api/v1/backtests", headers={"X-User-Id": user_id})
        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] == 1

        detail_response = client.get(f"/api/v1/backtests/{job['id']}", headers={"X-User-Id": user_id})
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["name"] == "Momentum 2024 sample"

        with session_factory() as session:
            with session.begin():
                session.execute(
                    text(
                        """
                        INSERT INTO backtest_results (
                            id,
                            backtest_job_id,
                            summary_metrics,
                            equity_curve,
                            trade_summary,
                            report_format,
                            report_body,
                            created_at,
                            updated_at
                        ) VALUES (
                            :id,
                            :backtest_job_id,
                            :summary_metrics,
                            :equity_curve,
                            :trade_summary,
                            :report_format,
                            :report_body,
                            :created_at,
                            :updated_at
                        )
                        """
                    ),
                    {
                        "id": "00000000-0000-0000-0000-000000009101",
                        "backtest_job_id": job["id"],
                        "summary_metrics": json.dumps(
                            {
                                "total_return": 0.184,
                                "sharpe_ratio": 1.72,
                                "max_drawdown": 0.093,
                                "win_rate": 0.58,
                                "trade_count": 24,
                            }
                        ),
                        "equity_curve": json.dumps(
                            [
                                {"date": "2024-01-02", "equity": 100000},
                                {"date": "2024-03-29", "equity": 118400},
                            ]
                        ),
                        "trade_summary": json.dumps(
                            [
                                {"symbol": "AAPL", "side": "BUY", "quantity": 10},
                                {"symbol": "MSFT", "side": "SELL", "quantity": 5},
                            ]
                        ),
                        "report_format": "json",
                        "report_body": json.dumps({"headline": "Backtest summary"}),
                        "created_at": datetime(2026, 4, 16, 9, 0, tzinfo=UTC),
                        "updated_at": datetime(2026, 4, 16, 9, 0, tzinfo=UTC),
                    },
                )
                session.execute(
                    text(
                        """
                        INSERT INTO backtest_logs (
                            id,
                            backtest_job_id,
                            level,
                            message,
                            created_at
                        ) VALUES (
                            :id,
                            :backtest_job_id,
                            :level,
                            :message,
                            :created_at
                        )
                        """
                    ),
                    {
                        "id": "00000000-0000-0000-0000-000000009201",
                        "backtest_job_id": job["id"],
                        "level": "INFO",
                        "message": "Backtest completed successfully.",
                        "created_at": datetime(2026, 4, 16, 9, 1, tzinfo=UTC),
                    },
                )

        result_response = client.get(f"/api/v1/backtests/{job['id']}/result", headers={"X-User-Id": user_id})
        assert result_response.status_code == 200
        result = result_response.json()["data"]
        assert result["summary_metrics"]["trade_count"] == 24
        assert len(result["equity_curve"]) == 2

        report_response = client.get(f"/api/v1/backtests/{job['id']}/report", headers={"X-User-Id": user_id})
        assert report_response.status_code == 200
        report = report_response.json()["data"]
        assert report["report_format"] == "json"
        assert report["report_body"]["headline"] == "Backtest summary"

        cancel_response = client.post(f"/api/v1/backtests/{job['id']}/cancel", headers={"X-User-Id": user_id})
        assert cancel_response.status_code == 200
        assert cancel_response.json()["data"]["status"] == "CANCELED"
    finally:
        _clear_overrides()
