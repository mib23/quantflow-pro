from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.core.api import api_response
from app.modules.backtests.schemas import BacktestJobCreateRequest
from app.modules.backtests.service import BacktestService, get_backtest_service
from app.modules.orders.dependencies import resolve_current_user_id

router = APIRouter()


@router.get("")
def list_backtests(
    request: Request,
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> dict[str, object]:
    return api_response(service.list_jobs(user_id=user_id).model_dump(mode="json"), request)


@router.post("")
def create_backtest(
    request: Request,
    payload: BacktestJobCreateRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> dict[str, object]:
    return api_response(
        service.create_job(payload, user_id=user_id, trace_id=getattr(request.state, "request_id", None)).model_dump(mode="json"),
        request,
    )


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
    return api_response(
        service.cancel_job(job_id, user_id=user_id, trace_id=getattr(request.state, "request_id", None)).model_dump(mode="json"),
        request,
    )


@router.post("/{job_id}/retry")
def retry_backtest(
    request: Request,
    job_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> dict[str, object]:
    return api_response(
        service.retry_job(job_id, user_id=user_id, trace_id=getattr(request.state, "request_id", None)).model_dump(mode="json"),
        request,
    )


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
    job_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: BacktestService = Depends(get_backtest_service),
) -> Response:
    report = service.get_report(job_id, user_id=user_id)
    return Response(
        content=json.dumps(report, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="backtest-{job_id}.json"'},
    )
