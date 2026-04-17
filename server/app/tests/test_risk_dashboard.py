from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.models import (
    Base,
    AccountBalanceModel,
    BrokerAccountModel,
    OrderModel,
    PositionModel,
    RiskEventModel,
    RiskRuleModel,
    RiskRuleVersionModel,
    UserModel,
)
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.service import DashboardService, get_dashboard_service
from app.modules.risk.repository import RiskRepository
from app.modules.risk.seed import seed_default_risk_data
from app.modules.risk.service import RiskService, get_risk_service


def _build_session_factory():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def _seed_phase2_data(session_factory):
    user_id = UUID("00000000-0000-0000-0000-000000000011")
    account_id = UUID("00000000-0000-0000-0000-000000000022")
    rule_max_id = UUID("00000000-0000-0000-0000-000000000101")
    rule_restricted_id = UUID("00000000-0000-0000-0000-000000000102")
    now = datetime.now(UTC).replace(second=0, microsecond=0)

    with session_factory() as session:
        with session.begin():
            session.add(
                UserModel(
                    id=user_id,
                    email="alex@quantflow.local",
                    full_name="Alex Johnson",
                    password_hash="hash",
                    role="ADMIN",
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                BrokerAccountModel(
                    id=account_id,
                    user_id=user_id,
                    broker_name="ALPACA",
                    broker_account_no="PA-10001",
                    external_account_id="paper-demo-001",
                    environment="paper",
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
            )

            for snapshot_id, equity, cash, buying_power, day_pnl, hours_ago in [
                (UUID("00000000-0000-0000-0000-000000000201"), Decimal("124010.00"), Decimal("41850.00"), Decimal("199640.00"), Decimal("-210.00"), 4),
                (UUID("00000000-0000-0000-0000-000000000202"), Decimal("124220.00"), Decimal("41680.00"), Decimal("200120.00"), Decimal("120.00"), 3),
                (UUID("00000000-0000-0000-0000-000000000203"), Decimal("124592.40"), Decimal("41240.00"), Decimal("201840.00"), Decimal("1240.50"), 0),
            ]:
                session.add(
                    AccountBalanceModel(
                        id=snapshot_id,
                        broker_account_id=account_id,
                        equity=equity,
                        cash=cash,
                        buying_power=buying_power,
                        day_pnl=day_pnl,
                        snapshot_at=now - timedelta(hours=hours_ago),
                    )
                )

            session.add_all(
                [
                    PositionModel(
                        id=UUID("00000000-0000-0000-0000-000000000301"),
                        broker_account_id=account_id,
                        symbol="TSLA",
                        quantity=Decimal("100"),
                        avg_price=Decimal("240.50"),
                        market_price=Decimal("245.50"),
                        market_value=Decimal("24550.00"),
                        unrealized_pnl=Decimal("500.00"),
                        snapshot_at=now,
                    ),
                    PositionModel(
                        id=UUID("00000000-0000-0000-0000-000000000302"),
                        broker_account_id=account_id,
                        symbol="NVDA",
                        quantity=Decimal("50"),
                        avg_price=Decimal("480.00"),
                        market_price=Decimal("476.20"),
                        market_value=Decimal("23810.00"),
                        unrealized_pnl=Decimal("-190.00"),
                        snapshot_at=now,
                    ),
                ]
            )

            session.add(
                OrderModel(
                    id=UUID("00000000-0000-0000-0000-000000000401"),
                    broker_account_id=account_id,
                    client_order_id="ord_seed_open_001",
                    broker_order_id="brk_seed_open_001",
                    symbol="AMD",
                    side="BUY",
                    order_type="LIMIT",
                    quantity=Decimal("10"),
                    limit_price=Decimal("98.50"),
                    status="OPEN",
                    time_in_force="day",
                    idempotency_key="idem-seed-open-001",
                    submitted_at=now - timedelta(minutes=10),
                    updated_at=now - timedelta(minutes=9),
                )
            )

            for rule_id, name, description, rule_type, config, symbols in [
                (
                    rule_max_id,
                    "Single order notional limit",
                    "Block orders whose notional exceeds the account limit.",
                    "MAX_SINGLE_ORDER_NOTIONAL",
                    {"max_notional": 1000.0},
                    [],
                ),
                (
                    rule_restricted_id,
                    "Restricted symbols",
                    "Block trading in restricted symbols.",
                    "RESTRICTED_SYMBOLS",
                    {"symbols": ["GME", "AMC"]},
                    ["GME", "AMC"],
                ),
            ]:
                session.add(
                    RiskRuleModel(
                        id=rule_id,
                        created_by=user_id,
                        name=name,
                        description=description,
                        scope="ACCOUNT",
                        scope_accounts=[str(account_id)],
                        scope_symbols=symbols,
                        rule_type=rule_type,
                        config=config,
                        enabled=True,
                        version=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
                session.add(
                    RiskRuleVersionModel(
                        id=UUID(int=rule_id.int + 1000),
                        risk_rule_id=rule_id,
                        version=1,
                        snapshot={
                            "name": name,
                            "description": description,
                            "rule_type": rule_type,
                            "config": config,
                            "scope": {"account_ids": [str(account_id)], "symbols": symbols},
                            "enabled": True,
                        },
                        change_reason="Seeded test rule.",
                        changed_by=user_id,
                        changed_at=now,
                    )
                )

            session.add(
                RiskEventModel(
                    id=UUID("00000000-0000-0000-0000-000000000501"),
                    risk_rule_id=rule_max_id,
                    broker_account_id=account_id,
                    order_id=None,
                    client_order_id="ord_seed_risk_001",
                    severity="MEDIUM",
                    event_type="risk.rule_triggered",
                    reason="Seed event: order notional reached 72% of configured threshold.",
                    status="OPEN",
                    payload={"symbol": "TSLA", "notional": 720.0, "max_notional": 1000.0},
                    dedupe_key="seed-risk-event",
                    occurred_at=now - timedelta(minutes=5),
                )
            )

    return str(user_id), str(account_id), str(rule_max_id)


def _override_phase2_services(session_factory):
    risk_service = RiskService(RiskRepository(session_factory))
    dashboard_service = DashboardService(DashboardRepository(session_factory), risk_service)
    app.dependency_overrides[get_risk_service] = lambda: risk_service
    app.dependency_overrides[get_dashboard_service] = lambda: dashboard_service


def _clear_overrides():
    app.dependency_overrides.clear()


def test_dashboard_and_risk_endpoints_expose_real_aggregates() -> None:
    session_factory = _build_session_factory()
    user_id, account_id, rule_id = _seed_phase2_data(session_factory)
    _override_phase2_services(session_factory)

    try:
        client = TestClient(app)

        overview_response = client.get("/api/v1/dashboard/overview", headers={"X-User-Id": user_id})
        assert overview_response.status_code == 200
        overview = overview_response.json()["data"]
        assert overview["account"]["id"] == account_id
        assert overview["metrics"]["total_positions"] == 2
        assert overview["metrics"]["open_orders"] == 1
        assert overview["risk_summary"]["active_rules"] == 2
        assert len(overview["recent_alerts"]) == 1
        assert overview["pnl"]["unrealized"] == 310.0

        curve_response = client.get("/api/v1/dashboard/equity-curve", headers={"X-User-Id": user_id})
        assert curve_response.status_code == 200
        assert len(curve_response.json()["data"]["points"]) == 3

        summary_response = client.get("/api/v1/risk/summary", headers={"X-User-Id": user_id})
        assert summary_response.status_code == 200
        summary = summary_response.json()["data"]
        assert summary["active_rules"] == 2
        assert summary["triggered_today"] == 1
        assert summary["blocked_orders_today"] == 0
        assert summary["unresolved_events"] == 1
        assert summary["restrictions"]["restricted_symbols"] == ["GME", "AMC"]

        rules_response = client.get("/api/v1/risk/rules", headers={"X-User-Id": user_id})
        assert rules_response.status_code == 200
        rules = rules_response.json()["data"]["items"]
        assert len(rules) == 2
        assert rules[0]["history"]

        deactivate_response = client.post(f"/api/v1/risk/rules/{rule_id}/deactivate", headers={"X-User-Id": user_id})
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["data"]["enabled"] is False

        events_response = client.get("/api/v1/risk/events", headers={"X-User-Id": user_id})
        assert events_response.status_code == 200
        assert events_response.json()["data"]["total"] == 1
    finally:
        _clear_overrides()


def test_pre_trade_check_returns_order_risk_rejected_on_block() -> None:
    session_factory = _build_session_factory()
    user_id, account_id, _ = _seed_phase2_data(session_factory)
    _override_phase2_services(session_factory)

    try:
        client = TestClient(app)
        payload = {
            "broker_account_id": account_id,
            "symbol": "TSLA",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "limit_price": 150,
            "time_in_force": "day",
            "idempotency_key": "idem-risk-check-001",
        }

        response = client.post("/api/v1/risk/checks/pre-trade", json=payload, headers={"X-User-Id": user_id})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "ORDER_RISK_REJECTED"
        assert "max_notional" in response.json()["error"]["message"]
    finally:
        _clear_overrides()


def test_seed_default_risk_data_backfills_missing_rules_idempotently() -> None:
    session_factory = _build_session_factory()
    now = datetime(2026, 4, 15, 8, 30, tzinfo=UTC)

    with session_factory() as session:
        with session.begin():
            user = UserModel(
                id=UUID("00000000-0000-0000-0000-000000000901"),
                email="alex@quantflow.local",
                full_name="Alex Johnson",
                password_hash="hash",
                role="ADMIN",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
            account = BrokerAccountModel(
                id=UUID("00000000-0000-0000-0000-000000000902"),
                user_id=user.id,
                broker_name="ALPACA",
                broker_account_no="PA-10099",
                external_account_id="paper-demo-099",
                environment="paper",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
            session.add(user)
            session.add(account)

        owner = session.get(UserModel, user.id)
        broker_account = session.get(BrokerAccountModel, account.id)
        assert owner is not None
        assert broker_account is not None

        with session.begin():
            first_run = seed_default_risk_data(session, owner=owner, account=broker_account, now=now)
        with session.begin():
            second_run = seed_default_risk_data(session, owner=owner, account=broker_account, now=now)

        rule_count = session.query(RiskRuleModel).filter(RiskRuleModel.created_by == user.id).count()
        version_count = session.query(RiskRuleVersionModel).count()
        event_count = session.query(RiskEventModel).filter(RiskEventModel.broker_account_id == account.id).count()

    assert first_run == {"rules_created": 4, "events_created": 3}
    assert second_run == {"rules_created": 0, "events_created": 0}
    assert rule_count == 4
    assert version_count == 4
    assert event_count == 3
