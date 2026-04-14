from fastapi import APIRouter

router = APIRouter()


@router.get("/quote/{symbol}")
def get_quote(symbol: str) -> dict[str, object]:
    return {
        "data": {
            "symbol": symbol.upper(),
            "bid": 245.2,
            "ask": 245.25,
            "last": 245.23,
            "timestamp": "2026-04-14T07:32:00Z",
        },
        "meta": {"request_id": None},
        "error": None,
    }
