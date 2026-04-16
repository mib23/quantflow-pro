from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from app.core.exceptions import ApiException
from app.core.settings import get_settings

from .repository import UserRepository
from .security import TokenError
from .service import AuthConfig, AuthService, AuthenticatedUser
from .session_store import RedisSessionStore


def get_auth_config() -> AuthConfig:
    settings = get_settings()
    return AuthConfig(
        jwt_secret=settings.jwt_secret,
        access_token_ttl_minutes=settings.access_token_ttl_minutes,
        refresh_token_ttl_days=settings.refresh_token_ttl_days,
    )


@lru_cache(maxsize=1)
def get_auth_repository() -> UserRepository:
    return UserRepository.from_database_url(get_settings().database_url)


@lru_cache(maxsize=1)
def get_auth_session_store() -> RedisSessionStore:
    return RedisSessionStore(get_settings().redis_url)


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    return AuthService(get_auth_repository(), get_auth_session_store(), get_auth_config())


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise ApiException("AUTH_UNAUTHORIZED", "Authorization header is required.", status_code=401)

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiException("AUTH_UNAUTHORIZED", "Bearer token is required.", status_code=401)

    return token


def get_current_user(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUser:
    access_token = _extract_bearer_token(request)
    try:
        return auth_service.get_current_user(access_token)
    except ApiException:
        raise
    except TokenError as exc:
        raise ApiException("AUTH_UNAUTHORIZED", str(exc), status_code=401) from exc
