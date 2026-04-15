from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.api import api_response
from app.core.exceptions import ApiException
from app.modules.orders.dependencies import resolve_current_user_id
from app.modules.risk.schemas import (
    PreTradeCheckRequest,
    RiskRuleCreateRequest,
    RiskRuleUpdateRequest,
)
from app.modules.risk.service import RiskService, get_risk_service

router = APIRouter()


@router.get("/summary")
def get_risk_summary(
    request: Request,
    user_id: str = Depends(resolve_current_user_id),
    broker_account_id: str | None = Query(default=None),
    service: RiskService = Depends(get_risk_service),
) -> dict[str, object]:
    return api_response(service.get_summary(user_id=user_id, broker_account_id=broker_account_id).model_dump(mode="json"), request)


@router.get("/rules")
def list_risk_rules(
    request: Request,
    user_id: str = Depends(resolve_current_user_id),
    broker_account_id: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    rule_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    service: RiskService = Depends(get_risk_service),
) -> dict[str, object]:
    data = service.list_rules(
        user_id=user_id,
        broker_account_id=broker_account_id,
        enabled=enabled,
        rule_type=rule_type,
        page=page,
        page_size=page_size,
    )
    return api_response(data.model_dump(mode="json"), request)


@router.post("/rules")
def create_risk_rule(
    request: Request,
    payload: RiskRuleCreateRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: RiskService = Depends(get_risk_service),
) -> dict[str, object]:
    data = service.create_rule(payload, created_by=user_id, trace_id=getattr(getattr(request, "state", None), "request_id", None))
    return api_response(data.model_dump(mode="json"), request)


@router.put("/rules/{rule_id}")
def update_risk_rule(
    request: Request,
    rule_id: str,
    payload: RiskRuleUpdateRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: RiskService = Depends(get_risk_service),
) -> dict[str, object]:
    data = service.update_rule(rule_id, payload, changed_by=user_id, trace_id=getattr(getattr(request, "state", None), "request_id", None))
    return api_response(data.model_dump(mode="json"), request)


@router.post("/rules/{rule_id}/activate")
def activate_risk_rule(
    request: Request,
    rule_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: RiskService = Depends(get_risk_service),
) -> dict[str, object]:
    data = service.activate_rule(rule_id, changed_by=user_id, trace_id=getattr(getattr(request, "state", None), "request_id", None))
    return api_response(data.model_dump(mode="json"), request)


@router.post("/rules/{rule_id}/deactivate")
def deactivate_risk_rule(
    request: Request,
    rule_id: str,
    user_id: str = Depends(resolve_current_user_id),
    service: RiskService = Depends(get_risk_service),
) -> dict[str, object]:
    data = service.deactivate_rule(rule_id, changed_by=user_id, trace_id=getattr(getattr(request, "state", None), "request_id", None))
    return api_response(data.model_dump(mode="json"), request)


@router.get("/events")
def list_risk_events(
    request: Request,
    user_id: str = Depends(resolve_current_user_id),
    broker_account_id: str | None = Query(default=None),
    rule_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    service: RiskService = Depends(get_risk_service),
) -> dict[str, object]:
    data = service.list_events(
        user_id=user_id,
        broker_account_id=broker_account_id,
        rule_id=rule_id,
        severity=severity,
        status_value=status_value,
        page=page,
        page_size=page_size,
    )
    return api_response(data.model_dump(mode="json"), request)


@router.post("/checks/pre-trade")
def pre_trade_check(
    request: Request,
    payload: PreTradeCheckRequest,
    user_id: str = Depends(resolve_current_user_id),
    service: RiskService = Depends(get_risk_service),
) -> dict[str, object]:
    data = service.check_pre_trade(
        payload,
        user_id=user_id,
        persist=True,
        trace_id=getattr(getattr(request, "state", None), "request_id", None),
    )
    if not data.passed:
        raise service.build_rejection_exception(data)
    return api_response(data.model_dump(mode="json"), request)
