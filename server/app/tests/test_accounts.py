from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.main import app
from app.modules.accounts import repository as accounts_repository


def _build_test_engine():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE broker_accounts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                broker_name TEXT NOT NULL,
                broker_account_no TEXT NOT NULL,
                external_account_id TEXT NOT NULL,
                environment TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE account_balances (
                id TEXT PRIMARY KEY,
                broker_account_id TEXT NOT NULL,
                equity NUMERIC NOT NULL,
                cash NUMERIC NOT NULL,
                buying_power NUMERIC NOT NULL,
                day_pnl NUMERIC NOT NULL,
                snapshot_at TEXT NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE positions (
                id TEXT PRIMARY KEY,
                broker_account_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity NUMERIC NOT NULL,
                avg_price NUMERIC NOT NULL,
                market_price NUMERIC NOT NULL,
                market_value NUMERIC NOT NULL,
                unrealized_pnl NUMERIC NOT NULL,
                snapshot_at TEXT NOT NULL
            )
            """
        )

    return engine


def _seed_accounts_data(engine) -> None:
    now = datetime(2026, 4, 14, 7, 30, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (id, email, full_name, password_hash, role, status, created_at, updated_at)
                VALUES (:id, :email, :full_name, :password_hash, :role, :status, :created_at, :updated_at)
                """
            ),
            [
                {
                    "id": "user-1",
                    "email": "trader@example.com",
                    "full_name": "Trader One",
                    "password_hash": "hash",
                    "role": "TRADER",
                    "status": "ACTIVE",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            ],
        )
        connection.execute(
            text(
                """
                INSERT INTO broker_accounts (
                    id, user_id, broker_name, broker_account_no, external_account_id,
                    environment, status, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :broker_name, :broker_account_no, :external_account_id,
                    :environment, :status, :created_at, :updated_at
                )
                """
            ),
            [
                {
                    "id": "acc-primary",
                    "user_id": "user-1",
                    "broker_name": "ALPACA",
                    "broker_account_no": "A-100",
                    "external_account_id": "ext-100",
                    "environment": "paper",
                    "status": "ACTIVE",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                {
                    "id": "acc-secondary",
                    "user_id": "user-1",
                    "broker_name": "ALPACA",
                    "broker_account_no": "A-200",
                    "external_account_id": "ext-200",
                    "environment": "paper",
                    "status": "INACTIVE",
                    "created_at": (now - timedelta(days=1)).isoformat(),
                    "updated_at": (now - timedelta(days=1)).isoformat(),
                },
            ],
        )
        connection.execute(
            text(
                """
                INSERT INTO account_balances (
                    id, broker_account_id, equity, cash, buying_power, day_pnl, snapshot_at
                ) VALUES (
                    :id, :broker_account_id, :equity, :cash, :buying_power, :day_pnl, :snapshot_at
                )
                """
            ),
            [
                {
                    "id": "bal-old",
                    "broker_account_id": "acc-primary",
                    "equity": 100500.0,
                    "cash": 50000.0,
                    "buying_power": 150000.0,
                    "day_pnl": 500.0,
                    "snapshot_at": (now - timedelta(minutes=30)).isoformat(),
                },
                {
                    "id": "bal-new",
                    "broker_account_id": "acc-primary",
                    "equity": 101000.0,
                    "cash": 51000.0,
                    "buying_power": 150500.0,
                    "day_pnl": 1000.0,
                    "snapshot_at": now.isoformat(),
                },
                {
                    "id": "bal-secondary",
                    "broker_account_id": "acc-secondary",
                    "equity": 25000.0,
                    "cash": 10000.0,
                    "buying_power": 40000.0,
                    "day_pnl": -250.0,
                    "snapshot_at": now.isoformat(),
                },
            ],
        )
        connection.execute(
            text(
                """
                INSERT INTO positions (
                    id, broker_account_id, symbol, quantity, avg_price, market_price,
                    market_value, unrealized_pnl, snapshot_at
                ) VALUES (
                    :id, :broker_account_id, :symbol, :quantity, :avg_price, :market_price,
                    :market_value, :unrealized_pnl, :snapshot_at
                )
                """
            ),
            [
                {
                    "id": "pos-old",
                    "broker_account_id": "acc-primary",
                    "symbol": "TSLA",
                    "quantity": 5,
                    "avg_price": 200.0,
                    "market_price": 205.0,
                    "market_value": 1025.0,
                    "unrealized_pnl": 25.0,
                    "snapshot_at": (now - timedelta(minutes=20)).isoformat(),
                },
                {
                    "id": "pos-new",
                    "broker_account_id": "acc-primary",
                    "symbol": "TSLA",
                    "quantity": 10,
                    "avg_price": 200.0,
                    "market_price": 210.0,
                    "market_value": 2100.0,
                    "unrealized_pnl": 100.0,
                    "snapshot_at": now.isoformat(),
                },
                {
                    "id": "pos-nvda",
                    "broker_account_id": "acc-primary",
                    "symbol": "NVDA",
                    "quantity": 2,
                    "avg_price": 500.0,
                    "market_price": 505.0,
                    "market_value": 1010.0,
                    "unrealized_pnl": 10.0,
                    "snapshot_at": now.isoformat(),
                },
                {
                    "id": "pos-secondary",
                    "broker_account_id": "acc-secondary",
                    "symbol": "AAPL",
                    "quantity": 3,
                    "avg_price": 100.0,
                    "market_price": 101.0,
                    "market_value": 303.0,
                    "unrealized_pnl": 3.0,
                    "snapshot_at": now.isoformat(),
                },
            ],
        )


def test_accounts_overview_reads_db_and_chooses_primary_account(monkeypatch) -> None:
    engine = _build_test_engine()
    _seed_accounts_data(engine)
    monkeypatch.setattr(accounts_repository, "get_accounts_engine", lambda: engine)

    client = TestClient(app)
    response = client.get("/api/v1/accounts/overview", headers={"X-User-Id": "user-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"] is None
    assert payload["data"]["account"]["id"] == "acc-primary"
    assert payload["data"]["account"]["broker"] == "ALPACA"
    assert payload["data"]["account"]["day_pnl_percent"] == 1.0
    assert [position["symbol"] for position in payload["data"]["positions"]] == ["NVDA", "TSLA"]
    assert payload["data"]["positions"][1]["quantity"] == 10.0


def test_accounts_broker_accounts_and_positions_endpoints_read_latest_snapshots(monkeypatch) -> None:
    engine = _build_test_engine()
    _seed_accounts_data(engine)
    monkeypatch.setattr(accounts_repository, "get_accounts_engine", lambda: engine)

    client = TestClient(app)

    broker_accounts_response = client.get("/api/v1/accounts/broker-accounts", headers={"X-User-Id": "user-1"})
    positions_response = client.get("/api/v1/accounts/positions", headers={"X-User-Id": "user-1"})

    assert broker_accounts_response.status_code == 200
    broker_accounts_payload = broker_accounts_response.json()
    assert broker_accounts_payload["data"]["total"] == 2
    assert broker_accounts_payload["data"]["items"][0]["id"] == "acc-primary"
    assert broker_accounts_payload["data"]["items"][0]["equity"] == 101000.0
    assert broker_accounts_payload["data"]["items"][0]["day_pnl_percent"] == 1.0

    assert positions_response.status_code == 200
    positions_payload = positions_response.json()
    assert positions_payload["data"]["total"] == 3
    assert [item["symbol"] for item in positions_payload["data"]["items"]] == ["NVDA", "TSLA", "AAPL"]
    assert positions_payload["data"]["items"][1]["quantity"] == 10.0


def test_accounts_require_current_user_context(monkeypatch) -> None:
    engine = _build_test_engine()
    _seed_accounts_data(engine)
    monkeypatch.setattr(accounts_repository, "get_accounts_engine", lambda: engine)

    client = TestClient(app)
    response = client.get("/api/v1/accounts/overview")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_UNAUTHORIZED"
