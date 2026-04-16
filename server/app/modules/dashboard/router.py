from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.api import api_response
from app.modules.dashboard.service import DashboardService, get_dashboard_service
from app.modules.orders.dependencies import resolve_current_user_id

router = APIRouter()


@router.get("/overview")
def get_dashboard_overview(
    request: Request,
    user_id: str = Depends(resolve_current_user_id),
    broker_account_id: str | None = Query(default=None),
    service: DashboardService = Depends(get_dashboard_service),
) -> dict[str, object]:
    data = service.get_overview(user_id=user_id, broker_account_id=broker_account_id)
    return api_response(data.model_dump(mode="json"), request)


@router.get("/equity-curve")
def get_dashboard_equity_curve(
    request: Request,
    user_id: str = Depends(resolve_current_user_id),
    broker_account_id: str | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=200, ge=1, le=1000),
    service: DashboardService = Depends(get_dashboard_service),
) -> dict[str, object]:
    data = service.get_equity_curve(user_id=user_id, broker_account_id=broker_account_id, days=days, limit=limit)
    return api_response(data.model_dump(mode="json"), request)
