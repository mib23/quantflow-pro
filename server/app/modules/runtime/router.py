from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.api import api_response
from app.modules.orders.dependencies import resolve_current_user_id
from app.modules.runtime.schemas import (
    RuntimeApprovalActionRequest,
    RuntimeHeartbeatRequest,
    RuntimeInstanceCreateRequest,
)
from app.modules.runtime.service import RuntimeService, get_runtime_service

router = APIRouter()


@router.get("/instances")
def list_runtime_instances(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.list_instances(user_id=user_id, page=page, page_size=page_size).model_dump(mode="json"), request)


@router.post("/instances")
def create_runtime_instance(
    request: Request,
    payload: RuntimeInstanceCreateRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.create_instance(payload, requested_by=user_id).model_dump(mode="json"), request)


@router.get("/instances/{instance_id}")
def get_runtime_instance(
    request: Request,
    instance_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.get_instance_detail(instance_id, user_id=user_id).model_dump(mode="json"), request)


@router.post("/instances/{instance_id}/start")
def start_runtime_instance(
    request: Request,
    instance_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.start_instance(instance_id, user_id=user_id).model_dump(mode="json"), request)


@router.post("/instances/{instance_id}/stop")
def stop_runtime_instance(
    request: Request,
    instance_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.stop_instance(instance_id, user_id=user_id).model_dump(mode="json"), request)


@router.post("/instances/{instance_id}/restart")
def restart_runtime_instance(
    request: Request,
    instance_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.restart_instance(instance_id, user_id=user_id).model_dump(mode="json"), request)


@router.post("/instances/{instance_id}/heartbeat")
def heartbeat_runtime_instance(
    request: Request,
    instance_id: str,
    payload: RuntimeHeartbeatRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.record_heartbeat(instance_id, payload, user_id=user_id).model_dump(mode="json"), request)


@router.get("/instances/{instance_id}/logs")
def list_runtime_logs(
    request: Request,
    instance_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.list_logs(instance_id, user_id=user_id).model_dump(mode="json"), request)


@router.post("/deployments/{instance_id}/approve")
def approve_runtime_deployment(
    request: Request,
    instance_id: str,
    payload: RuntimeApprovalActionRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.approve_deployment(instance_id, payload, user_id=user_id).model_dump(mode="json"), request)


@router.post("/deployments/{instance_id}/reject")
def reject_runtime_deployment(
    request: Request,
    instance_id: str,
    payload: RuntimeApprovalActionRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: RuntimeService = Depends(get_runtime_service),
) -> dict[str, object]:
    return api_response(service.reject_deployment(instance_id, payload, user_id=user_id).model_dump(mode="json"), request)

