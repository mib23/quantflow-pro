from __future__ import annotations

CANONICAL_ORDER_STATUSES: tuple[str, ...] = (
    "PENDING_SUBMIT",
    "SUBMITTED",
    "OPEN",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCEL_REQUESTED",
    "CANCELED",
    "REJECTED",
    "FAILED",
)

FINAL_ORDER_STATUSES = frozenset({"FILLED", "CANCELED", "REJECTED", "FAILED"})

_ORDER_STATUS_ALIASES: dict[str, str] = {
    "NEW": "SUBMITTED",
    "ACCEPTED": "SUBMITTED",
    "ACTIVE": "OPEN",
    "QUEUED": "PENDING_SUBMIT",
    "PENDING": "PENDING_SUBMIT",
    "PENDING_NEW": "PENDING_SUBMIT",
    "SUBMITTING": "PENDING_SUBMIT",
    "PARTIAL_FILL": "PARTIALLY_FILLED",
    "PARTIAL_FILLED": "PARTIALLY_FILLED",
    "PARTIALLYFILLED": "PARTIALLY_FILLED",
    "CANCELING": "CANCEL_REQUESTED",
    "CANCELLING": "CANCEL_REQUESTED",
    "CANCELLED": "CANCELED",
    "DONE_FOR_DAY": "CANCELED",
    "EXPIRED": "FAILED",
    "REPLACED": "SUBMITTED",
}


def normalize_order_status(value: str | None) -> str:
    if value is None:
        return "FAILED"

    cleaned = value.strip().upper().replace("-", "_").replace(" ", "_")
    normalized = _ORDER_STATUS_ALIASES.get(cleaned, cleaned)
    if normalized in CANONICAL_ORDER_STATUSES:
        return normalized
    return "FAILED"


def is_final_order_status(value: str | None) -> bool:
    return normalize_order_status(value) in FINAL_ORDER_STATUSES
