from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from app.core.exceptions import ApiException

from .repository import UserRepository
from .security import TokenError
from .service import AuthConfig, AuthService, AuthenticatedUser
from .session_store import RedisSessionStore


def get_auth_config() -> AuthConfig:
    return AuthConfig(
        jwt_secret=os.getenv("QF_JWT_SECRET", "quantflow-dev-auth-secret"),
        access_token_ttl_minutes=int(os.getenv("QF_ACCESS_TOKEN_TTL_MINUTES", "15")),
        refresh_token_ttl_days=int(os.getenv("QF_REFRESH_TOKEN_TTL_DAYS", "30")),
    )


@lru_cache(maxsize=1)
def get_auth_repository() -> UserRepository:
    database_url = os.getenv(
        "QF_DATABASE_URL",
        "postgresql+psycopg://quantflow:quantflow@localhost:5432/quantflow",
    )
    return UserRepository.from_database_url(database_url)


@lru_cache(maxsize=1)
def get_auth_session_store() -> RedisSessionStore:
    redis_url = os.getenv("QF_REDIS_URL", "redis://localhost:6379/0")
    return RedisSessionStore(redis_url)


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
