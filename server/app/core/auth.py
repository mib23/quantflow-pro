from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.exceptions import ApiException
from app.core.models import UserModel
from app.core.security import TokenPayload, TokenService
from app.core.sessions import get_session_store
from app.core.settings import get_settings


@dataclass(slots=True)
class CurrentUser:
    id: UUID
    email: str
    full_name: str
    role: str
    status: str
    session_id: str


def get_token_service() -> TokenService:
    return TokenService(get_settings())


def get_bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiException("AUTH_UNAUTHORIZED", "Missing bearer token.", status.HTTP_401_UNAUTHORIZED)
    return token


def resolve_current_user(
    request: Request,
    db: Session = Depends(get_db_session),
    token_service: TokenService = Depends(get_token_service),
) -> CurrentUser:
    token = get_bearer_token(request)
    payload: TokenPayload = token_service.decode_token(token, token_type="access")
    session = get_session_store().get_session(payload.session_id)
    if session is None or session["user_id"] != payload.subject:
        raise ApiException("AUTH_UNAUTHORIZED", "Session is no longer active.", status.HTTP_401_UNAUTHORIZED)

    user = db.get(UserModel, UUID(payload.subject))
    if user is None or user.status != "ACTIVE":
        raise ApiException("AUTH_UNAUTHORIZED", "User is not available.", status.HTTP_401_UNAUTHORIZED)

    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        session_id=payload.session_id,
    )
