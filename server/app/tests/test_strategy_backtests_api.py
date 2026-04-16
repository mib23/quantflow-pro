from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.models import Base, UserModel
from app.modules.backtests.repository import BacktestRepository
from app.modules.backtests.service import BacktestService, get_backtest_service
from app.modules.strategies.service import StrategyService, get_strategy_service
from app.modules.strategies.repository import StrategyRepository

USER_ID = "00000000-0000-0000-0000-000000000011"


def _build_session_factory():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def _seed_user(session_factory) -> None:
    now = datetime(2026, 4, 16, 8, 0, tzinfo=UTC)
    with session_factory() as session:
        with session.begin():
            session.add(
                UserModel(
                    id=UUID(USER_ID),
                    email="researcher@quantflow.local",
                    full_name="Research User",
                    password_hash="hash",
                    role="RESEARCHER",
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
            )


def test_strategy_version_lifecycle_exposes_frontend_friendly_payloads() -> None:
    session_factory = _build_session_factory()
    _seed_user(session_factory)
    strategy_service = StrategyService(StrategyRepository(session_factory))
    backtest_service = BacktestService(BacktestRepository(session_factory))
    app.dependency_overrides[get_strategy_service] = lambda: strategy_service
    app.dependency_overrides[get_backtest_service] = lambda: backtest_service
    client = TestClient(app)

    try:
        create_response = client.post(
            "/api/v1/strategies",
            json={"name": "Momentum Pulse", "description": "Test strategy", "default_parameters": {"lookback": 20}},
            headers={"X-User-Id": USER_ID},
        )
        assert create_response.status_code == 200
        strategy = create_response.json()["data"]
        assert strategy["name"] == "Momentum Pulse"
        assert strategy["versions"] == []

        version_response = client.post(
            f"/api/v1/strategies/{strategy['id']}/versions",
            json={"code": "def run(context):\n    return context", "parameters": {"lookback": 20}, "version_note": "Initial draft"},
            headers={"X-User-Id": USER_ID},
        )
        assert version_response.status_code == 200
        version = version_response.json()["data"]
        assert version["version_tag"] == "v1"

        clone_response = client.post(
            f"/api/v1/strategies/{strategy['id']}/versions/{version['id']}/clone",
            headers={"X-User-Id": USER_ID},
        )
        assert clone_response.status_code == 200
        cloned = clone_response.json()["data"]
        assert cloned["version_tag"] == "v2"

        detail_response = client.get(f"/api/v1/strategies/{strategy['id']}", headers={"X-User-Id": USER_ID})
        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]
        assert detail["latest_version_tag"] == "v2"
        assert [item["version_tag"] for item in detail["versions"]] == ["v2", "v1"]

        list_response = client.get("/api/v1/strategies", headers={"X-User-Id": USER_ID})
        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] == 1
    finally:
        app.dependency_overrides.clear()


def test_backtest_job_result_and_report_endpoints() -> None:
    session_factory = _build_session_factory()
    _seed_user(session_factory)
    strategy_service = StrategyService(StrategyRepository(session_factory))
    backtest_repository = BacktestRepository(session_factory)
    backtest_service = BacktestService(backtest_repository, enqueue_fn=lambda job_id: f"rq-{job_id[-6:]}")
    app.dependency_overrides[get_strategy_service] = lambda: strategy_service
    app.dependency_overrides[get_backtest_service] = lambda: backtest_service
    client = TestClient(app)

    try:
        strategy = client.post(
            "/api/v1/strategies",
            json={"name": "Mean Reversion", "default_parameters": {"window": 14}},
            headers={"X-User-Id": USER_ID},
        ).json()["data"]
        version = client.post(
            f"/api/v1/strategies/{strategy['id']}/versions",
            json={"code": "def run():\n    return 1", "parameters": {"window": 14}},
            headers={"X-User-Id": USER_ID},
        ).json()["data"]

        job_response = client.post(
            "/api/v1/backtests",
            json={
                "strategy_version_id": version["id"],
                "symbols": ["aapl", "msft"],
                "time_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-03-31T00:00:00Z"},
                "benchmark": "spy",
                "dataset_key": "demo-momentum",
            },
            headers={"X-User-Id": USER_ID},
        )
        assert job_response.status_code == 200
        job = job_response.json()["data"]
        assert job["status"] == "QUEUED"
        assert job["queue_job_id"].startswith("rq-")
        assert job["symbols"] == ["AAPL", "MSFT"]

        backtest_repository.save_result(
            job["id"],
            metrics={"total_return": 0.126, "sharpe": 1.42, "max_drawdown": -0.08, "win_rate": 0.58, "trade_count": 12},
            equity_curve=[{"time": "2024-01-02", "equity": 100000}, {"time": "2024-03-29", "equity": 112600}],
            trades=[{"symbol": "AAPL", "side": "BUY", "pnl": 820.0}],
            report={"title": "Backtest Report", "job_id": job["id"]},
        )

        list_response = client.get("/api/v1/backtests", headers={"X-User-Id": USER_ID})
        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] == 1
        assert list_response.json()["data"]["items"][0]["result_available"] is True

        detail_response = client.get(f"/api/v1/backtests/{job['id']}", headers={"X-User-Id": USER_ID})
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["strategy_version_tag"] == "v1"

        result_response = client.get(f"/api/v1/backtests/{job['id']}/result", headers={"X-User-Id": USER_ID})
        assert result_response.status_code == 200
        assert result_response.json()["data"]["metrics"]["total_return"] == 0.126

        report_response = client.get(f"/api/v1/backtests/{job['id']}/report", headers={"X-User-Id": USER_ID})
        assert report_response.status_code == 200
        assert report_response.headers["content-disposition"].startswith("attachment; filename=")

        cancel_response = client.post(f"/api/v1/backtests/{job['id']}/cancel", headers={"X-User-Id": USER_ID})
        assert cancel_response.status_code == 200
        assert cancel_response.json()["data"]["status"] == "CANCELED"

        retry_response = client.post(f"/api/v1/backtests/{job['id']}/retry", headers={"X-User-Id": USER_ID})
        assert retry_response.status_code == 200
        assert retry_response.json()["data"]["status"] == "QUEUED"
    finally:
        app.dependency_overrides.clear()
