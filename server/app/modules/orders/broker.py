from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(slots=True)
class BrokerOrderUpdate:
    broker_order_id: str | None = None
    status: str | None = None
    raw: dict[str, Any] | None = None


class BrokerGateway(Protocol):
    def submit_order(self, order: Mapping[str, Any]) -> BrokerOrderUpdate | None: ...

    def cancel_order(self, broker_order_id: str) -> BrokerOrderUpdate | None: ...

    def get_order(self, broker_order_id: str) -> BrokerOrderUpdate | None: ...


class NullBrokerGateway:
    def submit_order(self, order: Mapping[str, Any]) -> BrokerOrderUpdate | None:
        broker_order_id = f"brk_{order['symbol']}_{str(order['client_order_id'])[-6:]}"
        return BrokerOrderUpdate(broker_order_id=broker_order_id, status="submitted", raw={"mode": "simulated"})

    def cancel_order(self, broker_order_id: str) -> BrokerOrderUpdate | None:
        return BrokerOrderUpdate(broker_order_id=broker_order_id, status="canceled", raw={"mode": "simulated"})

    def get_order(self, broker_order_id: str) -> BrokerOrderUpdate | None:
        return BrokerOrderUpdate(broker_order_id=broker_order_id, status="open", raw={"mode": "simulated"})
