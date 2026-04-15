from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import Connection

from app.core.settings import get_settings


@lru_cache
def get_accounts_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@dataclass(slots=True)
class AccountsRepository:
    engine: Engine | None = None

    @property
    def resolved_engine(self) -> Engine:
        return self.engine or get_accounts_engine()

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        with self.resolved_engine.connect() as connection:
            yield connection

    def list_broker_accounts(self, user_id: str) -> list[dict[str, object]]:
        query = text(
            """
            WITH latest_balances AS (
                SELECT
                    account_balances.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY account_balances.broker_account_id
                        ORDER BY account_balances.snapshot_at DESC, account_balances.id DESC
                    ) AS row_number
                FROM account_balances
            )
            SELECT
                broker_accounts.id,
                broker_accounts.broker_name,
                broker_accounts.broker_account_no,
                broker_accounts.external_account_id,
                broker_accounts.environment,
                broker_accounts.status,
                latest_balances.equity,
                latest_balances.cash,
                latest_balances.buying_power,
                latest_balances.day_pnl,
                latest_balances.snapshot_at
            FROM broker_accounts
            LEFT JOIN latest_balances
                ON latest_balances.broker_account_id = broker_accounts.id
               AND latest_balances.row_number = 1
            WHERE broker_accounts.user_id = :user_id
            ORDER BY
                CASE WHEN broker_accounts.status = 'ACTIVE' THEN 0 ELSE 1 END,
                broker_accounts.created_at DESC,
                broker_accounts.id ASC
            """
        )

        with self.connect() as connection:
            rows = connection.execute(query, {"user_id": user_id}).mappings().all()
        return [dict(row) for row in rows]

    def list_positions(self, user_id: str) -> list[dict[str, object]]:
        query = text(
            """
            WITH latest_positions AS (
                SELECT
                    positions.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY positions.broker_account_id, positions.symbol
                        ORDER BY positions.snapshot_at DESC, positions.id DESC
                    ) AS row_number
                FROM positions
            )
            SELECT
                latest_positions.broker_account_id,
                latest_positions.symbol,
                latest_positions.quantity,
                latest_positions.avg_price,
                latest_positions.market_price,
                latest_positions.market_value,
                latest_positions.unrealized_pnl,
                latest_positions.snapshot_at
            FROM latest_positions
            JOIN broker_accounts ON broker_accounts.id = latest_positions.broker_account_id
            WHERE broker_accounts.user_id = :user_id
              AND latest_positions.row_number = 1
            ORDER BY latest_positions.broker_account_id ASC, latest_positions.symbol ASC
            """
        )

        with self.connect() as connection:
            rows = connection.execute(query, {"user_id": user_id}).mappings().all()
        return [dict(row) for row in rows]
