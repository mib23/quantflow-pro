from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.orders.broker import BrokerOrderUpdate
from app.modules.orders.repository import OrderRepository
from app.modules.orders.service import OrderService, get_order_service
from app.modules.orders.status import normalize_order_status
from app.modules.orders.tables import broker_accounts, metadata, users


class RecordingBrokerGateway:
    def __init__(self) -> None:
        self.submissions: list[dict[str, object]] = []
        self.cancellations: list[str] = []
        self.next_submission: BrokerOrderUpdate | None = BrokerOrderUpdate(
            broker_order_id="brk_0001",
            status="submitted",
            raw={"source": "fake-gateway"},
        )

    def submit_order(self, order):
        self.submissions.append(dict(order))
        return self.next_submission

    def cancel_order(self, broker_order_id: str):
        self.cancellations.append(broker_order_id)
        return BrokerOrderUpdate(broker_order_id=broker_order_id, status="canceled", raw={"source": "fake-gateway"})

    def get_order(self, broker_order_id: str):
        return BrokerOrderUpdate(broker_order_id=broker_order_id, status="open")


def _make_service(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'orders.db'}", future=True)
    metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

    with session_factory() as session:
        with session.begin():
            session.execute(
                insert(users).values(
                    {
                        "id": "usr_001",
                        "email": "trader@example.com",
                        "full_name": "Trader One",
                        "password_hash": "hash",
                        "role": "TRADER",
                        "status": "ACTIVE",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
            )
            session.execute(
                insert(broker_accounts).values(
                    {
                        "id": "acc_001",
                        "user_id": "usr_001",
                        "broker_name": "ALPACA",
                        "broker_account_no": "PA-001",
                        "external_account_id": "ext_001",
                        "environment": "paper",
                        "status": "ACTIVE",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
            )

    gateway = RecordingBrokerGateway()
    service = OrderService(OrderRepository(session_factory), gateway)
    return service, gateway


def _override_service(service: OrderService) -> None:
    app.dependency_overrides[get_order_service] = lambda: service


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_normalize_order_status() -> None:
    assert normalize_order_status("cancelled") == "CANCELED"
    assert normalize_order_status("partial filled") == "PARTIALLY_FILLED"
    assert normalize_order_status("new") == "SUBMITTED"
    assert normalize_order_status("mystery") == "FAILED"


def test_orders_lifecycle_and_executions(tmp_path) -> None:
    service, gateway = _make_service(tmp_path)
    _override_service(service)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/orders", headers={"X-User-Id": "usr_001"})
        assert response.status_code == 200
        assert response.json()["data"] == {"items": [], "page": 1, "page_size": 20, "total": 0}

        payload = {
            "broker_account_id": "acc_001",
            "symbol": "amd",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "limit_price": 195.25,
            "time_in_force": "day",
            "idempotency_key": "idem-001",
        }
        create_response = client.post("/api/v1/orders", json=payload, headers={"X-User-Id": "usr_001"})
        assert create_response.status_code == 200
        created = create_response.json()["data"]
        assert created["symbol"] == "AMD"
        assert created["status"] == "SUBMITTED"
        assert created["broker_order_id"] == "brk_0001"
        assert created["client_order_id"].startswith("ord_")
        assert gateway.submissions and gateway.submissions[0]["client_order_id"] == created["client_order_id"]

        duplicate_response = client.post("/api/v1/orders", json=payload, headers={"X-User-Id": "usr_001"})
        assert duplicate_response.status_code == 200
        assert duplicate_response.json()["data"]["client_order_id"] == created["client_order_id"]

        cancel_response = client.post(f"/api/v1/orders/{created['client_order_id']}/cancel", headers={"X-User-Id": "usr_001"})
        assert cancel_response.status_code == 200
        assert cancel_response.json()["data"]["status"] == "CANCELED"
        assert gateway.cancellations == ["brk_0001"]

        service.record_execution(
            client_order_id=created["client_order_id"],
            broker_execution_id="exe_001",
            filled_quantity=Decimal("10"),
            filled_price=Decimal("195.25"),
            fee_amount=Decimal("0.50"),
        )

        executions_response = client.get("/api/v1/orders/executions", headers={"X-User-Id": "usr_001"})
        assert executions_response.status_code == 200
        executions_payload = executions_response.json()["data"]
        assert executions_payload["total"] == 1
        assert executions_payload["items"][0]["broker_execution_id"] == "exe_001"
        assert executions_payload["items"][0]["client_order_id"] == created["client_order_id"]

        orders_response = client.get("/api/v1/orders", headers={"X-User-Id": "usr_001"})
        assert orders_response.status_code == 200
        orders_payload = orders_response.json()["data"]
        assert orders_payload["total"] == 1
        assert orders_payload["items"][0]["status"] == "FILLED"
    finally:
        _clear_overrides()


def test_idempotency_conflict_rejects_different_payload(tmp_path) -> None:
    service, _ = _make_service(tmp_path)
    _override_service(service)

    try:
        client = TestClient(app)
        payload = {
            "broker_account_id": "acc_001",
            "symbol": "TSLA",
            "side": "SELL",
            "order_type": "MARKET",
            "quantity": 5,
            "time_in_force": "day",
            "idempotency_key": "idem-dup",
        }
        first = client.post("/api/v1/orders", json=payload, headers={"X-User-Id": "usr_001"})
        assert first.status_code == 200

        changed_payload = dict(payload)
        changed_payload["quantity"] = 6
        second = client.post("/api/v1/orders", json=changed_payload, headers={"X-User-Id": "usr_001"})
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "ORDER_IDEMPOTENCY_CONFLICT"
    finally:
        _clear_overrides()
