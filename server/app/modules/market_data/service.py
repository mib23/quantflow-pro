from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import dataclass


@dataclass(slots=True)
class QuoteSnapshot:
    symbol: str
    bid: float | None
    ask: float | None
    last: float | None
    timestamp: str


def get_latest_quote(symbol: str) -> QuoteSnapshot:
    normalized_symbol = symbol.strip().upper()
    return QuoteSnapshot(
        symbol=normalized_symbol,
        bid=245.2,
        ask=245.25,
        last=245.23,
        timestamp=datetime.now(UTC).isoformat(),
    )
