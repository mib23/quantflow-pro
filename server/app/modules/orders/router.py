from fastapi import APIRouter, Depends, Query, Request

from app.modules.orders.dependencies import resolve_current_user_id
from app.modules.orders.schemas import PlaceOrderRequest
from app.modules.orders.service import OrderService, get_order_service

router = APIRouter()


def _envelope(data: object, request: Request | None = None) -> dict[str, object]:
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    return {"data": data, "meta": {"request_id": request_id}, "error": None}


@router.get("")
def list_orders(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    user_id: str = Depends(resolve_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> dict[str, object]:
    return _envelope(service.list_orders(page=page, page_size=page_size, user_id=user_id).model_dump(mode="json"), request)


@router.get("/executions")
def list_executions(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    user_id: str = Depends(resolve_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> dict[str, object]:
    return _envelope(service.list_executions(page=page, page_size=page_size, user_id=user_id).model_dump(mode="json"), request)


@router.post("")
def place_order(
    request: Request,
    payload: PlaceOrderRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> dict[str, object]:
    return _envelope(service.place_order(payload, user_id=user_id).model_dump(mode="json"), request)


@router.post("/{client_order_id}/cancel")
def cancel_order(
    request: Request,
    client_order_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> dict[str, object]:
    return _envelope(service.cancel_order(client_order_id, user_id=user_id).model_dump(mode="json"), request)
