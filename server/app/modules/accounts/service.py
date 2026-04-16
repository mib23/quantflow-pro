from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.accounts.repository import AccountsRepository
from app.modules.accounts.schemas import BrokerAccount, BrokerAccountsListResponse, OverviewResponse, Position, PositionsListResponse


def _as_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _calculate_day_pnl_percent(equity: object, day_pnl: object) -> float:
    equity_value = _as_float(equity)
    day_pnl_value = _as_float(day_pnl)
    reference_equity = equity_value - day_pnl_value
    if reference_equity <= 0:
        return 0.0
    return round(day_pnl_value / reference_equity * 100, 2)


@dataclass(slots=True)
class AccountsService:
    repository: AccountsRepository | None = None

    @property
    def resolved_repository(self) -> AccountsRepository:
        return self.repository or AccountsRepository()

    def get_broker_accounts(self, user_id: str) -> BrokerAccountsListResponse:
        rows = self.resolved_repository.list_broker_accounts(user_id)
        items = [self._to_broker_account(row) for row in rows]
        return BrokerAccountsListResponse(items=items, page=1, page_size=len(items), total=len(items))

    def get_positions(self, user_id: str) -> PositionsListResponse:
        rows = self.resolved_repository.list_positions(user_id)
        items = [self._to_position(row) for row in rows]
        return PositionsListResponse(items=items, page=1, page_size=len(items), total=len(items))

    def get_overview(self, user_id: str) -> OverviewResponse:
        accounts = self.get_broker_accounts(user_id).items
        if not accounts:
            raise ValueError("No broker accounts are bound to this user.")

        primary_account = accounts[0]
        positions = [position for position in self.get_positions(user_id).items if position.broker_account_id == primary_account.id]
        return OverviewResponse(account=primary_account, positions=positions)

    def _to_broker_account(self, row: dict[str, object]) -> BrokerAccount:
        return BrokerAccount(
            id=str(row["id"]),
            broker=str(row["broker_name"]),
            broker_account_no=str(row["broker_account_no"]),
            external_account_id=str(row["external_account_id"]),
            environment=str(row["environment"]),
            status=str(row["status"]),
            equity=_as_float(row.get("equity")),
            cash=_as_float(row.get("cash")),
            buying_power=_as_float(row.get("buying_power")),
            day_pnl=_as_float(row.get("day_pnl")),
            day_pnl_percent=_calculate_day_pnl_percent(row.get("equity"), row.get("day_pnl")),
            snapshot_at=row.get("snapshot_at"),
        )

    def _to_position(self, row: dict[str, object]) -> Position:
        return Position(
            broker_account_id=str(row["broker_account_id"]),
            symbol=str(row["symbol"]),
            quantity=_as_float(row.get("quantity")),
            avg_price=_as_float(row.get("avg_price")),
            market_price=_as_float(row.get("market_price")),
            market_value=_as_float(row.get("market_value")),
            unrealized_pnl=_as_float(row.get("unrealized_pnl")),
            snapshot_at=row.get("snapshot_at"),
        )
