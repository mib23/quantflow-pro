from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.models import (
    BacktestJobModel,
    BacktestResultModel,
    Base,
    BrokerAccountModel,
    OrderModel,
    RiskEventModel,
    RiskRuleModel,
    RuntimeInstanceModel,
    StrategyModel,
    StrategyVersionModel,
    UserModel,
)
from app.main import app
from app.modules.runtime.repository import RuntimeRepository
from app.modules.runtime.schemas import RuntimeInstanceCreateRequest
from app.modules.runtime.service import RuntimeService, get_runtime_service


def _build_session_factory():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def _seed_runtime_baseline(session_factory):
    researcher_id = UUID("00000000-0000-0000-0000-000000004001")
    admin_id = UUID("00000000-0000-0000-0000-000000004002")
    paper_account_id = UUID("00000000-0000-0000-0000-000000004101")
    live_account_id = UUID("00000000-0000-0000-0000-000000004102")
    strategy_id = UUID("00000000-0000-0000-0000-000000004201")
    version_id = UUID("00000000-0000-0000-0000-000000004202")
    live_job_id = UUID("00000000-0000-0000-0000-000000004301")
    live_result_id = UUID("00000000-0000-0000-0000-000000004302")
    risk_rule_id = UUID("00000000-0000-0000-0000-000000004401")
    now = datetime(2026, 4, 17, 11, 45, tzinfo=UTC)

    with session_factory() as session:
        with session.begin():
            session.add_all(
                [
                    UserModel(
                        id=researcher_id,
                        email="researcher@quantflow.local",
                        full_name="Researcher User",
                        password_hash="hash",
                        role="RESEARCHER",
                        status="ACTIVE",
                        created_at=now,
                        updated_at=now,
                    ),
                    UserModel(
                        id=admin_id,
                        email="admin@quantflow.local",
                        full_name="Admin User",
                        password_hash="hash",
                        role="ADMIN",
                        status="ACTIVE",
                        created_at=now,
                        updated_at=now,
                    ),
                    BrokerAccountModel(
                        id=paper_account_id,
                        user_id=researcher_id,
                        broker_name="ALPACA",
                        broker_account_no="PA-4001",
                        external_account_id="paper-runtime-4001",
                        environment="paper",
                        status="ACTIVE",
                        created_at=now,
                        updated_at=now,
                    ),
                    BrokerAccountModel(
                        id=live_account_id,
                        user_id=researcher_id,
                        broker_name="ALPACA",
                        broker_account_no="LV-4001",
                        external_account_id="live-runtime-4001",
                        environment="live",
                        status="ACTIVE",
                        created_at=now,
                        updated_at=now,
                    ),
                    StrategyModel(
                        id=strategy_id,
                        created_by=researcher_id,
                        name="Runtime Momentum",
                        description="Strategy for runtime tests",
                        status="ACTIVE",
                        default_parameters={"window": 12},
                        default_version_id=str(version_id),
                        latest_version_id=str(version_id),
                        created_at=now,
                        updated_at=now,
                    ),
                    StrategyVersionModel(
                        id=version_id,
                        strategy_id=strategy_id,
                        version_number=1,
                        code_snapshot={"source": "print('runtime')"},
                        parameter_template={"window": 12, "risk_mode": "standard"},
                        change_reason="Runtime baseline",
                        created_by=researcher_id,
                        created_at=now,
                    ),
                    BacktestJobModel(
                        id=live_job_id,
                        strategy_id=strategy_id,
                        strategy_version_id=version_id,
                        submitted_by=researcher_id,
                        name="Live readiness backtest",
                        status="SUCCEEDED",
                        start_date=now.date() - timedelta(days=10),
                        end_date=now.date() - timedelta(days=1),
                        symbols=["AAPL"],
                        benchmark_symbol="SPY",
                        parameters_snapshot={"window": 12},
                        queue_name="default",
                        execution_environment="test",
                        submitted_at=now - timedelta(hours=1),
                        started_at=now - timedelta(hours=1),
                        finished_at=now - timedelta(minutes=50),
                        updated_at=now - timedelta(minutes=50),
                    ),
                    BacktestResultModel(
                        id=live_result_id,
                        backtest_job_id=live_job_id,
                        summary_metrics={"total_return": 0.18},
                        equity_curve=[{"date": "2026-04-01", "equity": 100000}],
                        trade_summary=[{"symbol": "AAPL", "side": "BUY"}],
                        report_format="json",
                        report_body={"headline": "runtime ready"},
                        created_at=now - timedelta(minutes=50),
                        updated_at=now - timedelta(minutes=50),
                    ),
                    RiskRuleModel(
                        id=risk_rule_id,
                        created_by=researcher_id,
                        name="Live guardrail",
                        description="Seeded live rule",
                        scope="ACCOUNT",
                        scope_accounts=[str(live_account_id)],
                        scope_symbols=[],
                        rule_type="MAX_SINGLE_ORDER_NOTIONAL",
                        config={"max_notional": 5000.0},
                        enabled=True,
                        version=1,
                        created_at=now,
                        updated_at=now,
                    ),
                ]
            )

    return {
        "researcher_id": str(researcher_id),
        "admin_id": str(admin_id),
        "paper_account_id": str(paper_account_id),
        "live_account_id": str(live_account_id),
        "strategy_id": str(strategy_id),
        "version_id": str(version_id),
        "risk_rule_id": str(risk_rule_id),
        "now": now,
    }


def _override_runtime_service(session_factory) -> None:
    runtime_service = RuntimeService(RuntimeRepository(session_factory))
    app.dependency_overrides[get_runtime_service] = lambda: runtime_service


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_paper_runtime_lifecycle_supports_create_start_stop_restart() -> None:
    session_factory = _build_session_factory()
    seeded = _seed_runtime_baseline(session_factory)
    _override_runtime_service(session_factory)

    try:
        client = TestClient(app)
        create_response = client.post(
            "/api/v1/runtime/instances",
            headers={"X-User-Id": seeded["researcher_id"]},
            json={
                "strategy_version_id": seeded["version_id"],
                "broker_account_id": seeded["paper_account_id"],
                "environment": "PAPER",
                "config_snapshot": {"window": 20},
                "deployment_notes": "paper run",
            },
        )
        assert create_response.status_code == 200
        instance = create_response.json()["data"]
        assert instance["status"] == "CREATED"
        assert instance["approval_status"] == "NOT_REQUIRED"

        instance_id = instance["id"]
        start_response = client.post(f"/api/v1/runtime/instances/{instance_id}/start", headers={"X-User-Id": seeded["researcher_id"]})
        assert start_response.status_code == 200
        assert start_response.json()["data"]["status"] == "RUNNING"
        assert start_response.json()["data"]["last_heartbeat_at"] is not None

        stop_response = client.post(f"/api/v1/runtime/instances/{instance_id}/stop", headers={"X-User-Id": seeded["researcher_id"]})
        assert stop_response.status_code == 200
        assert stop_response.json()["data"]["status"] == "STOPPED"

        restart_response = client.post(
            f"/api/v1/runtime/instances/{instance_id}/restart",
            headers={"X-User-Id": seeded["researcher_id"]},
        )
        assert restart_response.status_code == 200
        restarted = restart_response.json()["data"]
        assert restarted["status"] == "RUNNING"
        assert restarted["restart_count"] == 1

        list_response = client.get("/api/v1/runtime/instances", headers={"X-User-Id": seeded["researcher_id"]})
        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] == 1
        detail_response = client.get(f"/api/v1/runtime/instances/{instance_id}", headers={"X-User-Id": seeded["researcher_id"]})
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["parameters_snapshot"]["window"] == 20
    finally:
        _clear_overrides()


def test_live_runtime_requires_approval_before_start() -> None:
    session_factory = _build_session_factory()
    seeded = _seed_runtime_baseline(session_factory)
    _override_runtime_service(session_factory)

    try:
        client = TestClient(app)
        rejected_live_create = client.post(
            "/api/v1/runtime/instances",
            headers={"X-User-Id": seeded["researcher_id"]},
            json={
                "strategy_version_id": seeded["version_id"],
                "broker_account_id": seeded["live_account_id"],
                "environment": "LIVE",
                "config_snapshot": {"window": 12},
                "deployment_notes": "researcher should be blocked",
            },
        )
        assert rejected_live_create.status_code == 403

        create_response = client.post(
            "/api/v1/runtime/instances",
            headers={"X-User-Id": seeded["admin_id"]},
            json={
                "strategy_version_id": seeded["version_id"],
                "broker_account_id": seeded["live_account_id"],
                "environment": "LIVE",
                "config_snapshot": {"window": 12},
                "deployment_notes": "need approval",
            },
        )
        assert create_response.status_code == 200
        instance_id = create_response.json()["data"]["id"]
        assert create_response.json()["data"]["approval_status"] == "PENDING"

        start_before_approval = client.post(
            f"/api/v1/runtime/instances/{instance_id}/start",
            headers={"X-User-Id": seeded["admin_id"]},
        )
        assert start_before_approval.status_code == 409
        assert start_before_approval.json()["error"]["code"] == "LIVE_APPROVAL_REQUIRED"

        approve_response = client.post(
            f"/api/v1/runtime/deployments/{instance_id}/approve",
            headers={"X-User-Id": seeded["admin_id"]},
            json={"comment": "approved for live"},
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["data"]["approval_status"] == "APPROVED"

        start_by_non_admin = client.post(
            f"/api/v1/runtime/instances/{instance_id}/start",
            headers={"X-User-Id": seeded["researcher_id"]},
        )
        assert start_by_non_admin.status_code == 403

        start_after_approval = client.post(
            f"/api/v1/runtime/instances/{instance_id}/start",
            headers={"X-User-Id": seeded["admin_id"]},
        )
        assert start_after_approval.status_code == 200
        assert start_after_approval.json()["data"]["status"] == "RUNNING"
    finally:
        _clear_overrides()


def test_heartbeat_timeout_moves_runtime_into_degraded_state() -> None:
    session_factory = _build_session_factory()
    seeded = _seed_runtime_baseline(session_factory)
    _override_runtime_service(session_factory)

    try:
        client = TestClient(app)
        create_response = client.post(
            "/api/v1/runtime/instances",
            headers={"X-User-Id": seeded["researcher_id"]},
            json={
                "strategy_version_id": seeded["version_id"],
                "broker_account_id": seeded["paper_account_id"],
                "environment": "PAPER",
            },
        )
        instance_id = create_response.json()["data"]["id"]
        client.post(f"/api/v1/runtime/instances/{instance_id}/start", headers={"X-User-Id": seeded["researcher_id"]})

        with session_factory() as session:
            with session.begin():
                runtime = session.get(RuntimeInstanceModel, instance_id)
                assert runtime is not None
                runtime.last_heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)

        detail_response = client.get(f"/api/v1/runtime/instances/{instance_id}", headers={"X-User-Id": seeded["researcher_id"]})
        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]
        assert detail["status"] == "DEGRADED"
        assert detail["recent_alerts"][0]["alert_type"] == "HEARTBEAT_TIMEOUT"
    finally:
        _clear_overrides()


def test_runtime_sweep_marks_stale_instances_without_detail_polling() -> None:
    session_factory = _build_session_factory()
    seeded = _seed_runtime_baseline(session_factory)
    runtime_service = RuntimeService(RuntimeRepository(session_factory))

    instance = runtime_service.create_instance(
        payload=RuntimeInstanceCreateRequest(
            strategy_version_id=seeded["version_id"],
            broker_account_id=seeded["paper_account_id"],
            environment="PAPER",
        ),
        requested_by=seeded["researcher_id"],
    )
    runtime_service.start_instance(instance.id, user_id=seeded["researcher_id"])

    with session_factory() as session:
        with session.begin():
            runtime = session.get(RuntimeInstanceModel, instance.id)
            assert runtime is not None
            runtime.last_heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)

    updated = runtime_service.sweep_stale_instances()
    detail = runtime_service.get_instance_detail(instance.id, user_id=seeded["researcher_id"])

    assert updated == 1
    assert detail.status == "DEGRADED"
    assert detail.recent_alerts[0].alert_type == "HEARTBEAT_TIMEOUT"


def test_runtime_detail_exposes_related_orders_and_risk_events() -> None:
    session_factory = _build_session_factory()
    seeded = _seed_runtime_baseline(session_factory)
    _override_runtime_service(session_factory)

    try:
        client = TestClient(app)
        create_response = client.post(
            "/api/v1/runtime/instances",
            headers={"X-User-Id": seeded["researcher_id"]},
            json={
                "strategy_version_id": seeded["version_id"],
                "broker_account_id": seeded["paper_account_id"],
                "environment": "PAPER",
            },
        )
        instance_id = create_response.json()["data"]["id"]

        with session_factory() as session:
            with session.begin():
                session.add(
                    OrderModel(
                        id=UUID("00000000-0000-0000-0000-000000004501"),
                        broker_account_id=UUID(seeded["paper_account_id"]),
                        runtime_instance_id=UUID(instance_id),
                        client_order_id="ord-runtime-5001",
                        broker_order_id="brk-runtime-5001",
                        symbol="AAPL",
                        side="BUY",
                        order_type="LIMIT",
                        quantity=Decimal("5"),
                        limit_price=Decimal("180.00"),
                        status="OPEN",
                        time_in_force="day",
                        idempotency_key="idem-runtime-5001",
                        submitted_at=seeded["now"],
                        updated_at=seeded["now"],
                    )
                )
                session.add(
                    RiskEventModel(
                        id=UUID("00000000-0000-0000-0000-000000004601"),
                        risk_rule_id=UUID(seeded["risk_rule_id"]),
                        broker_account_id=UUID(seeded["paper_account_id"]),
                        runtime_instance_id=UUID(instance_id),
                        order_id=None,
                        client_order_id="ord-runtime-5001",
                        severity="HIGH",
                        event_type="risk.rule_triggered",
                        reason="Order notional exceeded limit.",
                        status="OPEN",
                        payload={"symbol": "AAPL"},
                        dedupe_key="runtime-risk-5001",
                        occurred_at=seeded["now"],
                    )
                )

        detail_response = client.get(f"/api/v1/runtime/instances/{instance_id}", headers={"X-User-Id": seeded["researcher_id"]})
        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]
        assert detail["recent_orders"][0]["client_order_id"] == "ord-runtime-5001"
        assert detail["recent_risk_events"][0]["client_order_id"] == "ord-runtime-5001"

        logs_response = client.get(f"/api/v1/runtime/instances/{instance_id}/logs", headers={"X-User-Id": seeded["researcher_id"]})
        assert logs_response.status_code == 200
        assert logs_response.json()["data"]["total"] >= 1
    finally:
        _clear_overrides()
