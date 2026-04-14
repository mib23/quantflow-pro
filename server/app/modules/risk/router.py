from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
def get_risk_summary() -> dict[str, object]:
    return {
        "data": {
            "hard_limits": {
                "max_daily_loss": 5000,
                "max_single_order_value": 50000,
                "max_position_size_percent": 20,
            },
            "restrictions": {
                "restricted_symbols": ["GME", "AMC", "DOGE"],
                "market_hours_only": True,
            },
            "recent_events": [
                {
                    "id": "risk_evt_001",
                    "severity": "MEDIUM",
                    "message": "Daily exposure reached 72% of configured threshold.",
                    "occurred_at": "2026-04-14T07:20:00Z",
                }
            ],
        },
        "meta": {"request_id": None},
        "error": None,
    }
