from fastapi import APIRouter, Request

from app.core.api import api_response
from app.modules.market_data.service import get_latest_quote

router = APIRouter()


@router.get("/quote/{symbol}")
def get_quote(symbol: str, request: Request) -> dict[str, object]:
    quote = get_latest_quote(symbol)
    return api_response(
        {
            "symbol": quote.symbol,
            "bid": quote.bid,
            "ask": quote.ask,
            "last": quote.last,
            "timestamp": quote.timestamp,
        },
        request,
    )
