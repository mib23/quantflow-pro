from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.api import api_response
from .dependencies import get_auth_service, get_current_user
from .schemas import LoginRequest, LogoutRequest, RefreshRequest
from .service import AuthService

router = APIRouter()


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, object]:
    token_pair = auth_service.login(payload.email, payload.password)
    return api_response(
        {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "token_type": token_pair.token_type,
            "user": token_pair.user.to_public_dict(),
        },
        request,
    )


@router.post("/refresh")
def refresh(
    payload: RefreshRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, object]:
    token_pair = auth_service.refresh(payload.refresh_token)
    return api_response(
        {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "token_type": token_pair.token_type,
            "user": token_pair.user.to_public_dict(),
        },
        request,
    )


@router.post("/logout")
def logout(
    request: Request,
    payload: LogoutRequest | None = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, object]:
    authorization = request.headers.get("Authorization")
    access_token = None
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            access_token = token

    refresh_token = payload.refresh_token if payload is not None else None
    result = auth_service.logout(refresh_token=refresh_token, access_token=access_token)
    return api_response(
        {
            "revoked": result.revoked,
            "session_id": result.session_id,
        },
        request,
    )


@router.get("/me")
def me(request: Request, current_user=Depends(get_current_user)) -> dict[str, object]:
    return api_response(current_user.to_public_dict(), request)
