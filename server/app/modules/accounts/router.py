from fastapi import APIRouter

router = APIRouter()


@router.get("/overview")
def get_account_overview() -> dict[str, object]:
    return {
        "data": {
            "account": {
                "id": "acc_paper_001",
                "broker": "ALPACA",
                "environment": "paper",
                "equity": 124592.4,
                "cash": 41240.0,
                "buying_power": 201840.0,
                "day_pnl": 1240.5,
                "day_pnl_percent": 1.01,
            },
            "positions": [
                {
                    "symbol": "TSLA",
                    "quantity": 100,
                    "avg_price": 240.5,
                    "market_price": 245.5,
                    "unrealized_pnl": 500.0,
                },
                {
                    "symbol": "NVDA",
                    "quantity": 50,
                    "avg_price": 480.0,
                    "market_price": 476.2,
                    "unrealized_pnl": -190.0,
                },
            ],
        },
        "meta": {"request_id": None},
        "error": None,
    }
