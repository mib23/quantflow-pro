from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.api import api_response
from app.modules.orders.dependencies import resolve_current_user_id
from app.modules.strategies.schemas import BacktestJobCreateRequest
from app.modules.backtests.service import BacktestService, get_backtest_service

router = APIRouter()


@router.get("")
def list_backtests(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> dict[str, object]:
    return api_response(service.list_jobs(user_id=user_id, page=page, page_size=page_size).model_dump(mode="json"), request)


@router.post("")
def create_backtest(
    request: Request,
    payload: BacktestJobCreateRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> dict[str, object]:
    return api_response(service.create_job(payload, submitted_by=user_id).model_dump(mode="json"), request)


@router.get("/{job_id}")
def get_backtest(
    request: Request,
    job_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> dict[str, object]:
    return api_response(service.get_job(job_id, user_id=user_id).model_dump(mode="json"), request)


@router.post("/{job_id}/cancel")
def cancel_backtest(
    request: Request,
    job_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> dict[str, object]:
    return api_response(service.cancel_job(job_id, user_id=user_id).model_dump(mode="json"), request)


@router.get("/{job_id}/result")
def get_backtest_result(
    request: Request,
    job_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> dict[str, object]:
    return api_response(service.get_result(job_id, user_id=user_id).model_dump(mode="json"), request)


@router.get("/{job_id}/report")
def get_backtest_report(
    request: Request,
    job_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> dict[str, object]:
    return api_response(service.get_report(job_id, user_id=user_id).model_dump(mode="json"), request)

