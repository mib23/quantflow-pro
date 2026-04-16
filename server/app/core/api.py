from typing import Any

from fastapi import Request


def api_response(data: Any, request: Request | None = None) -> dict[str, Any]:
    request_id = getattr(request.state, "request_id", None) if request is not None else None
    return {
        "data": data,
        "meta": {"request_id": request_id},
        "error": None,
    }
