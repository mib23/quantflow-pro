from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.api import api_response
from app.modules.orders.dependencies import resolve_current_user_id
from app.modules.strategies.schemas import (
    StrategyCreateRequest,
    StrategyVersionCloneRequest,
    StrategyVersionCreateRequest,
)
from app.modules.strategies.service import StrategyService, get_strategy_service

router = APIRouter()


@router.get("")
def list_strategies(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    user_id: str = Depends(resolve_current_user_id),
    service: StrategyService = Depends(get_strategy_service),
) -> dict[str, object]:
    return api_response(service.list_strategies(user_id=user_id, page=page, page_size=page_size).model_dump(mode="json"), request)


@router.post("")
def create_strategy(
    request: Request,
    payload: StrategyCreateRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: StrategyService = Depends(get_strategy_service),
) -> dict[str, object]:
    return api_response(service.create_strategy(payload, created_by=user_id).model_dump(mode="json"), request)


@router.get("/{strategy_id}")
def get_strategy(
    request: Request,
    strategy_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: StrategyService = Depends(get_strategy_service),
) -> dict[str, object]:
    return api_response(service.get_strategy(strategy_id, user_id=user_id).model_dump(mode="json"), request)


@router.post("/{strategy_id}/versions")
def create_strategy_version(
    request: Request,
    strategy_id: str,
    payload: StrategyVersionCreateRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: StrategyService = Depends(get_strategy_service),
) -> dict[str, object]:
    return api_response(service.create_version(strategy_id, payload, created_by=user_id).model_dump(mode="json"), request)


@router.post("/{strategy_id}/versions/{version_id}/clone")
def clone_strategy_version(
    request: Request,
    strategy_id: str,
    version_id: str,
    payload: StrategyVersionCloneRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: StrategyService = Depends(get_strategy_service),
) -> dict[str, object]:
    return api_response(service.clone_version(strategy_id, version_id, payload, created_by=user_id).model_dump(mode="json"), request)

