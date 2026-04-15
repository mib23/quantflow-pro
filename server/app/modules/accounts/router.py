from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.core.exceptions import ApiException
from app.modules.accounts.dependencies import resolve_current_user_id
from app.modules.accounts.service import AccountsService

router = APIRouter()


def get_accounts_service() -> AccountsService:
    return AccountsService()


def _envelope(data: object, request: Request | None = None) -> dict[str, object]:
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    return {"data": data, "meta": {"request_id": request_id}, "error": None}


@router.get("/broker-accounts")
def get_broker_accounts(
    request: Request,
    user_id: str = Depends(resolve_current_user_id),
    service: AccountsService = Depends(get_accounts_service),
) -> dict[str, object]:
    return _envelope(service.get_broker_accounts(user_id), request)


@router.get("/overview")
def get_account_overview(
    request: Request,
    user_id: str = Depends(resolve_current_user_id),
    service: AccountsService = Depends(get_accounts_service),
) -> dict[str, object]:
    try:
        return _envelope(service.get_overview(user_id), request)
    except ValueError as exc:
        raise ApiException("BROKER_ACCOUNT_NOT_FOUND", str(exc), status_code=status.HTTP_404_NOT_FOUND) from exc


@router.get("/positions")
def get_positions(
    request: Request,
    user_id: str = Depends(resolve_current_user_id),
    service: AccountsService = Depends(get_accounts_service),
) -> dict[str, object]:
    return _envelope(service.get_positions(user_id), request)
