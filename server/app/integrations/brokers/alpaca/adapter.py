from dataclasses import dataclass
from typing import Protocol


@dataclass
class BrokerOrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: int
    limit_price: float | None = None


@dataclass
class BrokerOrderSnapshot:
    broker_order_id: str
    symbol: str
    side: str
    status: str
    quantity: int
    filled_quantity: int


class BrokerAdapter(Protocol):
    def get_account_overview(self, account_id: str) -> dict: ...
    def list_positions(self, account_id: str) -> list[dict]: ...
    def place_order(self, account_id: str, order: BrokerOrderRequest) -> BrokerOrderSnapshot: ...
    def cancel_order(self, account_id: str, broker_order_id: str) -> BrokerOrderSnapshot: ...
    def get_order(self, account_id: str, broker_order_id: str) -> BrokerOrderSnapshot: ...


class AlpacaBrokerAdapter:
    def get_account_overview(self, account_id: str) -> dict:
        return {"account_id": account_id, "broker": "ALPACA", "environment": "paper"}

    def list_positions(self, account_id: str) -> list[dict]:
        return [{"account_id": account_id, "symbol": "TSLA", "quantity": 100}]

    def place_order(self, account_id: str, order: BrokerOrderRequest) -> BrokerOrderSnapshot:
        return BrokerOrderSnapshot(
            broker_order_id=f"alpaca_{account_id}_{order.symbol.lower()}",
            symbol=order.symbol,
            side=order.side,
            status="ACCEPTED",
            quantity=order.quantity,
            filled_quantity=0,
        )

    def cancel_order(self, account_id: str, broker_order_id: str) -> BrokerOrderSnapshot:
        return BrokerOrderSnapshot(
            broker_order_id=broker_order_id,
            symbol="UNKNOWN",
            side="BUY",
            status="CANCELLED",
            quantity=0,
            filled_quantity=0,
        )

    def get_order(self, account_id: str, broker_order_id: str) -> BrokerOrderSnapshot:
        return BrokerOrderSnapshot(
            broker_order_id=broker_order_id,
            symbol="AAPL",
            side="BUY",
            status="NEW",
            quantity=100,
            filled_quantity=0,
        )
