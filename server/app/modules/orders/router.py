from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class PlaceOrderRequest(BaseModel):
    broker_account_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP"]
    quantity: int = Field(gt=0)
    limit_price: float | None = Field(default=None, gt=0)
    time_in_force: str = "day"
    idempotency_key: str


@router.get("")
def list_orders() -> dict[str, object]:
    return {
        "data": {
            "items": [
                {
                    "client_order_id": "ord_20260414_001",
                    "symbol": "AMD",
                    "side": "BUY",
                    "quantity": 200,
                    "limit_price": 98.5,
                    "status": "OPEN",
                    "submitted_at": "2026-04-14T07:30:01Z",
                },
                {
                    "client_order_id": "ord_20260414_002",
                    "symbol": "SPY",
                    "side": "SELL",
                    "quantity": 50,
                    "limit_price": 401.0,
                    "status": "OPEN",
                    "submitted_at": "2026-04-14T07:31:15Z",
                },
            ],
            "page": 1,
            "page_size": 20,
            "total": 2,
        },
        "meta": {"request_id": None},
        "error": None,
    }


@router.post("")
def place_order(payload: PlaceOrderRequest) -> dict[str, object]:
    return {
        "data": {
            "client_order_id": f"ord_{payload.symbol.lower()}_{payload.idempotency_key[-4:]}",
            "broker_order_id": None,
            "status": "PENDING_SUBMIT",
            "risk_check": {"passed": True, "events": []},
        },
        "meta": {"request_id": None},
        "error": None,
    }


@router.post("/{client_order_id}/cancel")
def cancel_order(client_order_id: str) -> dict[str, object]:
    return {
        "data": {
            "client_order_id": client_order_id,
            "status": "CANCEL_REQUESTED",
        },
        "meta": {"request_id": None},
        "error": None,
    }
