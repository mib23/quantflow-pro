from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.core.api import api_response

router = APIRouter()


@router.get("/quote/{symbol}")
def get_quote(symbol: str, request: Request) -> dict[str, object]:
    return api_response(
        {
            "symbol": symbol.upper(),
            "bid": 245.2,
            "ask": 245.25,
            "last": 245.23,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        request,
    )
